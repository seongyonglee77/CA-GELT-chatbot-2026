"""Provider-isolated Model 1 STT -> Qwen -> CosyVoice orchestration."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

from .config import Model1Config, RequestTiming, utc_now_iso
from .personas import PersonaProfile, PersonaRegistry
from .prompts import LAYER2_ELF_POLICY, build_layered_system_prompt
from .tts import CosyVoiceTTS


class ProviderError(RuntimeError):
    """A sanitized provider or transport error.

    Error text deliberately contains only provider and status information.
    Response bodies and exception details are not retained in ``str(error)``.
    """

    def __init__(
        self,
        provider: str,
        *,
        status_code: int | None = None,
        message: str | None = None,
    ) -> None:
        self.provider = provider
        self.status_code = status_code
        suffix = f" (HTTP {status_code})" if status_code is not None else ""
        super().__init__(message or f"{provider} request failed{suffix}")


@dataclass(frozen=True)
class HttpResponse:
    """Small response shape shared by the default transport and test fakes."""

    status_code: int
    body: bytes = field(repr=False)

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class HttpTransport(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, str] | None = None,
        data: bytes | None = None,
        json: Any = None,
        timeout: float | None = None,
    ) -> Any:
        ...


class UrllibTransport:
    """Dependency-free HTTP POST transport used outside tests."""

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, str] | None = None,
        data: bytes | None = None,
        json: Any = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        if json is not None:
            request_data = json_encode(json)
            request_headers = {**headers, "Content-Type": "application/json"}
        else:
            request_data = data
            request_headers = dict(headers)
        request = urllib.request.Request(url, data=request_data, headers=request_headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return HttpResponse(response.status, response.read())
        except urllib.error.HTTPError as exc:
            # Returning a response lets adapters consistently sanitize errors
            # while preserving the useful HTTP status for callers.
            return HttpResponse(exc.code, exc.read())


def json_encode(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class STTResult:
    transcript: str
    timing: RequestTiming

    @property
    def duration_seconds(self) -> float:
        return self.timing.duration_seconds


@dataclass(frozen=True)
class QwenResult:
    text: str
    timing: RequestTiming

    @property
    def response_text(self) -> str:
        return self.text

    @property
    def duration_seconds(self) -> float:
        return self.timing.duration_seconds


def _status_code(response: Any) -> int:
    if isinstance(response, Mapping):
        status = response.get("status_code", response.get("status", 200))
    else:
        status = getattr(response, "status_code", getattr(response, "status", 200))
    try:
        return int(status)
    except (TypeError, ValueError):
        return 200


def _response_json(response: Any) -> Any:
    if isinstance(response, Mapping):
        body = response.get("json", response.get("body", response))
        if callable(body):
            body = body()
        if isinstance(body, bytes):
            return json.loads(body.decode("utf-8"))
        if isinstance(body, str):
            return json.loads(body)
        return body
    parser = getattr(response, "json", None)
    if callable(parser):
        return parser()
    body = getattr(response, "body", getattr(response, "content", getattr(response, "text", None)))
    if isinstance(body, bytes):
        return json.loads(body.decode("utf-8"))
    if isinstance(body, str):
        return json.loads(body)
    if body is not None:
        return body
    raise ValueError("Provider response did not contain JSON")


def _timing(started_ts: str, started_mono: float) -> RequestTiming:
    return RequestTiming(
        started_ts=started_ts,
        ended_ts=utc_now_iso(),
        duration_seconds=max(0.0, time.monotonic() - started_mono),
    )


class DeepgramSTTClient:
    """Deepgram prerecorded transcription adapter."""

    endpoint = "https://api.deepgram.com/v1/listen"

    def __init__(
        self,
        config: Model1Config,
        *,
        transport: HttpTransport | None = None,
        audio_content_type: str = "audio/wav",
    ) -> None:
        self.config = config
        self.transport = transport or UrllibTransport()
        self.audio_content_type = audio_content_type

    def transcribe(self, audio_bytes: bytes) -> STTResult:
        if not isinstance(audio_bytes, (bytes, bytearray, memoryview)):
            raise TypeError("audio_bytes must be bytes-like")
        started_ts = utc_now_iso()
        started_mono = time.monotonic()
        headers = {
            "Authorization": f"Token {self.config.deepgram_api_key}",
            "Content-Type": self.audio_content_type,
        }
        params = {
            "model": "nova-3",
            "smart_format": "true",
            "punctuate": "true",
            "utterances": "true",
        }
        try:
            response = self.transport.post(
                self.endpoint,
                headers=headers,
                params=params,
                data=bytes(audio_bytes),
                timeout=self.config.request_timeout_seconds,
            )
        except Exception as exc:
            raise ProviderError("Deepgram") from exc
        status = _status_code(response)
        if not 200 <= status < 300:
            raise ProviderError("Deepgram", status_code=status)
        try:
            payload = _response_json(response)
            results = payload["results"]
            try:
                transcript = results["channels"][0]["alternatives"][0]["transcript"]
            except (KeyError, IndexError, TypeError):
                transcript = results["utterances"][0]["transcript"]
            if not isinstance(transcript, str):
                raise ValueError("transcript is not text")
        except Exception as exc:
            raise ProviderError("Deepgram", message="Deepgram returned an invalid response") from exc
        return STTResult(transcript=transcript, timing=_timing(started_ts, started_mono))

    # ``run`` is a natural adapter-level spelling and keeps orchestration code
    # readable without adding a second path.
    run = transcribe


# Kept as the historical public name; the policy now has one shared source in
# the human-readable Layer 2 asset.
MODEL1_SYSTEM_POLICY = LAYER2_ELF_POLICY


def serialize_context(value: str | Mapping[str, Any]) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    except (TypeError, ValueError) as exc:
        raise TypeError("style_card and task_context mappings must be JSON serializable") from exc


def build_system_prompt(
    style_card: str | Mapping[str, Any],
    task_context: str | Mapping[str, Any],
    persona: Mapping[str, Any] | None = None,
) -> str:
    """Combine the approved Model 1 policy with turn-specific context."""

    # Validate through the legacy serializer first so its public error text
    # remains stable, while the shared builder owns all policy layers.
    serialize_context(style_card)
    serialize_context(task_context)
    # Layer 1 → Layer 2 → Layer 3 is assembled by the shared builder.  Keep
    # the legacy style-card label and serialization so existing callers and
    # provider payloads retain their public behavior.
    prompt = build_layered_system_prompt(persona, task_context)
    return (
        f"{prompt}\n\n"
        "Style Card (serialized):\n"
        f"{serialize_context(style_card)}"
    )


class QwenChatClient:
    """OpenAI-compatible Qwen chat-completion adapter."""

    def __init__(
        self,
        config: Model1Config,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        self.config = config
        self.transport = transport or UrllibTransport()

    @property
    def endpoint(self) -> str:
        base = self.config.qwen_base_url.rstrip("/")
        return base if base.endswith("/chat/completions") else f"{base}/chat/completions"

    def complete(
        self,
        transcript: str,
        *,
        style_card: str | Mapping[str, Any],
        task_context: str | Mapping[str, Any],
        persona: Mapping[str, Any] | None = None,
    ) -> QwenResult:
        if not isinstance(transcript, str):
            raise TypeError("transcript must be a string")
        started_ts = utc_now_iso()
        started_mono = time.monotonic()
        payload = {
            "model": self.config.qwen_model,
            "enable_thinking": self.config.qwen_enable_thinking,
            "max_tokens": self.config.qwen_max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": build_system_prompt(style_card, task_context, persona),
                },
                {"role": "user", "content": transcript},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.config.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self.transport.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.config.request_timeout_seconds,
            )
        except Exception as exc:
            raise ProviderError("Qwen") from exc
        status = _status_code(response)
        if not 200 <= status < 300:
            raise ProviderError("Qwen", status_code=status)
        try:
            body = _response_json(response)
            content = body["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, Mapping) else str(part)
                    for part in content
                )
            if not isinstance(content, str):
                raise ValueError("content is not text")
        except Exception as exc:
            raise ProviderError("Qwen", message="Qwen returned an invalid response") from exc
        return QwenResult(text=content, timing=_timing(started_ts, started_mono))

    run = complete


@dataclass(frozen=True)
class PersonaVoice:
    """The selected persona label and explicit CosyVoice voice ID."""

    persona_id: str
    voice_id: str


@dataclass(frozen=True)
class CascadeRequest:
    """One turn's caller-supplied input.

    ``audio_bytes`` is excluded from repr to avoid leaking raw audio through
    debugging or test failure output.
    """

    persona_id: str
    voice_id: str
    style_card: str | Mapping[str, Any]
    task_context: str | Mapping[str, Any]
    audio_bytes: bytes = field(repr=False)

    @property
    def persona(self) -> PersonaVoice:
        return PersonaVoice(self.persona_id, self.voice_id)


@dataclass(frozen=True)
class CascadeResult:
    """Outputs and timing fields for one completed Model 1 turn."""

    persona: PersonaVoice
    transcript: str
    response_text: str
    audio_bytes: bytes = field(repr=False)
    user_turn_end_ts: str = ""
    first_model_event_ts: str = ""
    first_audio_out_ts: str = ""
    response_end_ts: str = ""
    stt_latency_seconds: float = 0.0
    model_latency_seconds: float = 0.0
    tts_latency_seconds: float = 0.0
    time_to_first_model_event_seconds: float = 0.0
    time_to_first_audio_out_seconds: float = 0.0
    total_latency_seconds: float = 0.0
    generation_latency_seconds: float = 0.0
    response_onset_latency_seconds: float = 0.0
    playback_duration_seconds: float = 0.0
    latencies: Mapping[str, float] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.response_text

    @property
    def audio(self) -> bytes:
        return self.audio_bytes


class Model1Cascade:
    """Run one user turn through Deepgram, Qwen, and CosyVoice in order."""

    def __init__(
        self,
        stt_client: DeepgramSTTClient,
        qwen_client: QwenChatClient,
        tts_adapter: CosyVoiceTTS,
        persona_registry: PersonaRegistry | None = None,
    ) -> None:
        self.stt_client = stt_client
        self.qwen_client = qwen_client
        self.tts_adapter = tts_adapter
        self.persona_registry = persona_registry

    @classmethod
    def from_config(
        cls,
        config: Model1Config,
        *,
        http_transport: HttpTransport | None = None,
        synthesizer_factory: Callable[..., Any] | None = None,
        persona_registry: PersonaRegistry | None = None,
    ) -> "Model1Cascade":
        return cls(
            DeepgramSTTClient(config, transport=http_transport),
            QwenChatClient(config, transport=http_transport),
            CosyVoiceTTS(config, synthesizer_factory=synthesizer_factory),
            persona_registry=persona_registry,
        )

    def run(
        self,
        *,
        persona_id: str,
        voice_id: str,
        style_card: str | Mapping[str, Any],
        task_context: str | Mapping[str, Any],
        audio_bytes: bytes,
    ) -> CascadeResult:
        return self._run(
            persona_id=persona_id,
            voice_id=voice_id,
            style_card=style_card,
            task_context=task_context,
            audio_bytes=audio_bytes,
        )

    def run_persona(
        self,
        persona_id: str,
        task_context: str | Mapping[str, Any],
        audio_bytes: bytes,
    ) -> CascadeResult:
        """Run a turn using the voice and prompt context from the registry."""

        if self.persona_registry is None:
            raise ValueError("Model1Cascade requires a PersonaRegistry for run_persona")
        profile = self.persona_registry.resolve(persona_id)
        return self._run(
            persona_id=profile.persona_id,
            voice_id=profile.voice_id,
            style_card={},
            task_context=task_context,
            audio_bytes=audio_bytes,
            persona=profile.prompt_context,
        )

    def _run(
        self,
        *,
        persona_id: str,
        voice_id: str,
        style_card: str | Mapping[str, Any],
        task_context: str | Mapping[str, Any],
        audio_bytes: bytes,
        persona: Mapping[str, Any] | None = None,
    ) -> CascadeResult:
        request = CascadeRequest(
            persona_id=persona_id,
            voice_id=voice_id,
            style_card=style_card,
            task_context=task_context,
            audio_bytes=audio_bytes,
        )
        turn_started_mono = time.monotonic()
        user_turn_end_ts = utc_now_iso()

        stt_result = self.stt_client.transcribe(request.audio_bytes)
        if persona is None:
            qwen_result = self.qwen_client.complete(
                stt_result.transcript,
                style_card=request.style_card,
                task_context=request.task_context,
            )
        else:
            qwen_result = self.qwen_client.complete(
                stt_result.transcript,
                style_card=request.style_card,
                task_context=request.task_context,
                persona=persona,
            )
        first_model_event_ts = utc_now_iso()
        first_model_event_mono = time.monotonic()
        tts_result = self.tts_adapter.synthesize(qwen_result.text, voice_id=request.voice_id)
        first_audio_out_ts = utc_now_iso()
        first_audio_out_mono = time.monotonic()
        response_end_ts = first_audio_out_ts

        total = max(0.0, first_audio_out_mono - turn_started_mono)
        first_model_latency = max(0.0, first_model_event_mono - turn_started_mono)
        first_audio_latency = max(0.0, first_audio_out_mono - turn_started_mono)
        latencies = {
            "stt_seconds": stt_result.timing.duration_seconds,
            "model_seconds": qwen_result.timing.duration_seconds,
            "tts_seconds": tts_result.timing.duration_seconds,
            "first_model_event_seconds": first_model_latency,
            "first_audio_out_seconds": first_audio_latency,
            "total_seconds": total,
            # Canonical project-log names; values are monotonic seconds.
            "generation_latency": first_model_latency,
            "response_onset_latency": first_audio_latency,
            "playback_duration": 0.0,
        }
        return CascadeResult(
            persona=request.persona,
            transcript=stt_result.transcript,
            response_text=qwen_result.text,
            audio_bytes=tts_result.audio_bytes,
            user_turn_end_ts=user_turn_end_ts,
            first_model_event_ts=first_model_event_ts,
            first_audio_out_ts=first_audio_out_ts,
            response_end_ts=response_end_ts,
            stt_latency_seconds=stt_result.timing.duration_seconds,
            model_latency_seconds=qwen_result.timing.duration_seconds,
            tts_latency_seconds=tts_result.timing.duration_seconds,
            time_to_first_model_event_seconds=first_model_latency,
            time_to_first_audio_out_seconds=first_audio_latency,
            total_latency_seconds=total,
            generation_latency_seconds=first_model_latency,
            response_onset_latency_seconds=first_audio_latency,
            playback_duration_seconds=0.0,
            latencies=latencies,
        )


__all__ = [
    "CascadeRequest",
    "CascadeResult",
    "DeepgramClient",
    "DeepgramSTTClient",
    "HttpResponse",
    "HttpTransport",
    "MODEL1_SYSTEM_POLICY",
    "Model1Cascade",
    "PersonaProfile",
    "PersonaRegistry",
    "PersonaVoice",
    "ProviderError",
    "QwenClient",
    "QwenChatClient",
    "QwenResult",
    "STTResult",
    "UrllibTransport",
    "build_system_prompt",
    "serialize_context",
]


# Provider-neutral spellings retained as aliases, not compatibility
# implementations, so callers can choose concise names without coupling
# orchestration to SDK classes.
DeepgramClient = DeepgramSTTClient
QwenClient = QwenChatClient
