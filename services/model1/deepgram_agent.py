"""Integrated Deepgram Voice Agent transport for classroom personas.

The provider client in this module is intentionally synchronous.  WebSocket
I/O runs in a reader thread and callers from the async web adapter move the
small blocking operations to ``asyncio.to_thread``.  No Deepgram SDK is
required at import time; only ``websocket-client`` is imported when a session
is started.
"""

from __future__ import annotations

import copy
import importlib
import inspect
import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from .config import read_env_file, utc_now_iso
from .personas import PersonaProfile
from .prompts import build_layered_system_prompt


DEEPGRAM_AGENT_ENDPOINT = "wss://agent.deepgram.com/v1/agent/converse"
_SETTINGS_ROOT = Path(__file__).resolve().parents[2] / "prompts"
_PERSONA_SETTINGS = {
    "deepgram_kit": "raw_materials/deepgram_kit_code.json",
    "deepgram_kai": "raw_materials/deepgram_kai_code.json",
    "deepgram_hannah": "raw_materials/deepgram_Hannah_code.json",
    "deepgram_naveen": "raw_materials/deepgram_Naveen_code.json",
}
_VOICE_MODELS = {
    "deepgram_kit": "flux-kit-en",
    "deepgram_kai": "flux-kai-en",
    "deepgram_hannah": "flux-hannah-en",
    "deepgram_naveen": "flux-naveen-en",
}
_LISTEN_MODEL = "flux-general-en"
_THINK_MODEL = "gemini-3.1-flash-lite"
_MAX_TRANSCRIPT_CHARS = 4000


class DeepgramAgentError(RuntimeError):
    """A provider failure whose text is safe to expose to application code."""

    def __init__(self, message: str = "Deepgram voice agent failed") -> None:
        super().__init__(message)


class DeepgramAgentConfigurationError(DeepgramAgentError):
    """Raised when the optional Deepgram Agent configuration is incomplete."""


class DeepgramAgentConfig:
    """Minimal optional configuration used by the Agent path.

    Unlike :class:`Model1Config`, this loader intentionally requires only the
    Deepgram key.  The legacy cascade keeps its existing full configuration
    requirements when this path is disabled.
    """

    def __init__(self, deepgram_api_key: str, *, request_timeout_seconds: float = 60.0) -> None:
        key = str(deepgram_api_key).strip()
        if not key:
            raise DeepgramAgentConfigurationError("Deepgram Agent configuration is unavailable")
        try:
            timeout = float(request_timeout_seconds)
        except (TypeError, ValueError) as exc:
            raise DeepgramAgentConfigurationError("Deepgram Agent configuration is unavailable") from exc
        if timeout <= 0:
            raise DeepgramAgentConfigurationError("Deepgram Agent configuration is unavailable")
        self.deepgram_api_key = key
        self.request_timeout_seconds = timeout

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "DeepgramAgentConfig":
        source = os.environ if env is None else env
        key = source.get("DEEPGRAM_API_KEY", "")
        timeout = source.get("DEEPGRAM_AGENT_TIMEOUT_SECONDS", "60")
        return cls(key, request_timeout_seconds=timeout)

    @classmethod
    def from_env_file(
        cls,
        path: str | os.PathLike[str] = ".env.local",
        *,
        env: Mapping[str, str] | None = None,
    ) -> "DeepgramAgentConfig":
        values = read_env_file(path)
        values.update(dict(os.environ if env is None else env))
        return cls.from_env(values)


def deepgram_agent_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether the explicitly opt-in Agent path is enabled."""

    source = os.environ if env is None else env
    return source.get("DEEPGRAM_AGENT_ENABLED", "").strip().lower() == "true"


def _persona_id(profile: Any) -> str:
    if isinstance(profile, str):
        return profile
    value = getattr(profile, "persona_id", None)
    if isinstance(value, str):
        return value
    if isinstance(profile, Mapping) and isinstance(profile.get("persona_id"), str):
        return profile["persona_id"]
    return ""


def _config_key(config: Any) -> str:
    if isinstance(config, str):
        return config
    value = getattr(config, "deepgram_api_key", None)
    if isinstance(value, str):
        return value
    if isinstance(config, Mapping):
        for key in ("deepgram_api_key", "DEEPGRAM_API_KEY", "api_key"):
            value = config.get(key)
            if isinstance(value, str):
                return value
    return ""


class DeepgramVoiceAgentSession:
    """One synchronous Deepgram Voice Agent conversation.

    ``start`` opens the socket, waits for the provider Welcome event, and
    sends the immutable Settings payload once.  It does not return until the
    provider confirms SettingsApplied.  A background reader consumes provider
    messages so audio and status events are available through the return values
    of ``send_audio``/``stop`` and through :meth:`drain_events`.
    ConversationText is reduced to a bounded, provider-neutral transcript
    event before entering the event queue.
    """

    supports_audio_input = True
    endpoint = DEEPGRAM_AGENT_ENDPOINT

    def __init__(
        self,
        profile: PersonaProfile | Mapping[str, Any] | str,
        config: Any | None = None,
        *,
        api_key: str | None = None,
        deepgram_api_key: str | None = None,
        task_context: Any = None,
        websocket_factory: Callable[..., Any] | None = None,
        settings_root: str | os.PathLike[str] | None = None,
    ) -> None:
        self.profile = profile
        self.persona_id = _persona_id(profile)
        if self.persona_id not in _PERSONA_SETTINGS:
            raise ValueError("unsupported Deepgram persona")
        self.config = config
        self.api_key = (api_key or deepgram_api_key or _config_key(config)).strip()
        if not self.api_key:
            raise DeepgramAgentConfigurationError("Deepgram Agent configuration is unavailable")
        self.task_context = task_context
        self.websocket_factory = websocket_factory
        self.settings_root = Path(settings_root) if settings_root is not None else _SETTINGS_ROOT
        self.settings = self._load_settings()
        self.audio_format = self._audio_format(self.settings)
        self._socket: Any = None
        self._reader: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._events: queue.Queue[dict[str, Any]] = queue.Queue()
        self._state = "new"
        self._settings_sent = False
        self._welcome_event = threading.Event()
        self._settings_applied_event = threading.Event()
        self._lock = threading.Lock()
        self._started_mono: float | None = None
        self._first_audio_mono: float | None = None
        self._started_ts: str | None = None
        self._first_audio_ts: str | None = None
        self._ended_ts: str | None = None
        self._timing: dict[str, Any] | None = None

    @staticmethod
    def _audio_format(settings: Mapping[str, Any]) -> dict[str, Any]:
        audio = settings.get("audio")
        input_audio = audio.get("input") if isinstance(audio, Mapping) else None
        output_audio = audio.get("output") if isinstance(audio, Mapping) else None
        if not isinstance(input_audio, Mapping) or not isinstance(output_audio, Mapping):
            raise DeepgramAgentConfigurationError("Deepgram Agent settings are unavailable")
        if input_audio.get("encoding") != "linear16" or input_audio.get("sample_rate") != 48000:
            raise DeepgramAgentConfigurationError("Deepgram Agent settings are unavailable")
        if (
            output_audio.get("encoding") != "linear16"
            or output_audio.get("sample_rate") != 24000
            or output_audio.get("container") not in {None, "none"}
        ):
            raise DeepgramAgentConfigurationError("Deepgram Agent settings are unavailable")
        return {
            "encoding": "linear16",
            "sample_rate": 24000,
            "container": "none",
        }

    def _load_settings(self) -> dict[str, Any]:
        path = self.settings_root / _PERSONA_SETTINGS[self.persona_id]
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DeepgramAgentConfigurationError("Deepgram Agent settings are unavailable") from exc
        if not isinstance(settings, dict) or settings.get("type") != "Settings":
            raise DeepgramAgentConfigurationError("Deepgram Agent settings are unavailable")
        settings = copy.deepcopy(settings)
        try:
            agent = settings["agent"]
            speak_provider = agent["speak"]["provider"]
            listen_provider = agent["listen"]["provider"]
            think = agent["think"]
        except (KeyError, TypeError) as exc:
            raise DeepgramAgentConfigurationError("Deepgram Agent settings are unavailable") from exc
        if not all(isinstance(value, dict) for value in (agent, speak_provider, listen_provider, think)):
            raise DeepgramAgentConfigurationError("Deepgram Agent settings are unavailable")
        # These values are part of the selected persona contract, not caller
        # configuration.  The prompt is always rebuilt from the current profile.
        speak_provider.update({"type": "deepgram", "version": "v2", "model": _VOICE_MODELS[self.persona_id]})
        listen_provider.update({"type": "deepgram", "version": "v2", "model": _LISTEN_MODEL})
        think["provider"] = {"type": "google", "model": _THINK_MODEL}
        think["prompt"] = build_layered_system_prompt(
            self.profile,
            self.task_context,
        )
        return settings

    @property
    def timing(self) -> Mapping[str, Any] | None:
        return dict(self._timing) if self._timing is not None else None

    @property
    def state(self) -> str:
        return self._state

    def _default_factory(self) -> Callable[..., Any]:
        try:
            websocket = importlib.import_module("websocket")
            return websocket.create_connection
        except Exception as exc:
            raise DeepgramAgentError("websocket-client is required for Deepgram Agent") from exc

    def _connect(self) -> Any:
        factory = self.websocket_factory or self._default_factory()
        token = f"Token {self.api_key}"
        header = [f"Authorization: {token}"]
        try:
            signature = inspect.signature(factory)
        except (TypeError, ValueError):
            signature = None
        try:
            if signature is None:
                return factory(self.endpoint, header=header)
            parameters = signature.parameters
            kwargs: dict[str, Any] = {}
            if "header" in parameters:
                kwargs["header"] = header
            elif "headers" in parameters:
                kwargs["headers"] = {"Authorization": token}
            elif any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
                kwargs["header"] = header
            if "timeout" in parameters:
                timeout = getattr(self.config, "request_timeout_seconds", 60.0)
                kwargs["timeout"] = timeout
            if kwargs:
                return factory(self.endpoint, **kwargs)
            return factory(self.endpoint)
        except Exception as exc:
            raise DeepgramAgentError() from exc

    @staticmethod
    def _send_binary(socket: Any, payload: bytes) -> None:
        binary_sender = getattr(socket, "send_binary", None)
        if callable(binary_sender):
            binary_sender(payload)
            return
        sender = getattr(socket, "send", None)
        if not callable(sender):
            raise DeepgramAgentError()
        try:
            signature = inspect.signature(sender)
        except (TypeError, ValueError):
            signature = None
        if signature is not None and (
            "opcode" in signature.parameters
            or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values())
        ):
            sender(payload, opcode=2)
        else:
            sender(payload)

    @staticmethod
    def _send_json(socket: Any, payload: Mapping[str, Any]) -> None:
        sender = getattr(socket, "send", None)
        if not callable(sender):
            raise DeepgramAgentError()
        sender(json.dumps(dict(payload), ensure_ascii=False, separators=(",", ":")))

    def _request_timeout(self) -> float:
        configured = getattr(self.config, "request_timeout_seconds", 60.0)
        if isinstance(self.config, Mapping):
            configured = self.config.get("request_timeout_seconds", configured)
        try:
            timeout = float(configured)
        except (TypeError, ValueError):
            return 60.0
        return timeout if timeout > 0 else 60.0

    @staticmethod
    def _close_socket(socket: Any) -> None:
        close = getattr(socket, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    def _abort_start(self) -> None:
        self._stop_event.set()
        socket = self._socket
        if socket is not None:
            self._close_socket(socket)
        reader = self._reader
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=2.0)
        self._socket = None
        self._reader = None
        self._state = "failed"

    def start(self) -> list[dict[str, Any]]:
        """Open the provider and complete the Welcome/Settings handshake."""

        with self._lock:
            if self._state == "started":
                return self.drain_events()
            if self._state == "stopped":
                return []
            socket = self._connect()
            self._socket = socket
            self._stop_event.clear()
            self._welcome_event.clear()
            self._settings_applied_event.clear()
            self._settings_sent = False
            self._state = "starting"
            self._reader = threading.Thread(
                target=self._reader_loop,
                name="deepgram-agent-reader",
                daemon=True,
            )
            self._reader.start()

        timeout = self._request_timeout()
        if not self._welcome_event.wait(timeout):
            self._abort_start()
            raise DeepgramAgentConfigurationError(
                "Deepgram Agent configuration is unavailable"
            )
        self._settings_sent = True
        try:
            self._send_json(socket, self.settings)
        except Exception as exc:
            self._settings_sent = False
            self._abort_start()
            raise DeepgramAgentError() from exc
        if not self._settings_applied_event.wait(timeout):
            self._abort_start()
            raise DeepgramAgentConfigurationError(
                "Deepgram Agent configuration is unavailable"
            )
        with self._lock:
            if self._state != "starting":
                return []
            self._state = "started"
            self._started_mono = time.monotonic()
            self._started_ts = utc_now_iso()
        return [{"type": "ready", "audio_format": dict(self.audio_format)}] + self.drain_events()

    connect = start
    open = start

    def _provider_event(self, raw: Any) -> None:
        if isinstance(raw, (bytearray, memoryview)):
            raw = bytes(raw)
        if isinstance(raw, bytes):
            if not raw:
                return
            if raw[:1] in {b"{", b"["}:
                try:
                    decoded = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError):
                    decoded = None
                if isinstance(decoded, Mapping):
                    self._provider_event(decoded)
                    return
            if self._first_audio_mono is None:
                self._first_audio_mono = time.monotonic()
                self._first_audio_ts = utc_now_iso()
            self._events.put(
                {
                    "type": "audio_chunk",
                    "data": raw,
                    "audio_format": dict(self.audio_format),
                }
            )
            return
        if isinstance(raw, Mapping):
            message = raw
        elif isinstance(raw, str):
            try:
                message = json.loads(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                self._events.put({"type": "status", "status": "provider_message"})
                return
        else:
            return
        if not isinstance(message, Mapping):
            return
        event_type = message.get("type")
        if event_type == "ConversationText":
            provider_role = message.get("role")
            role = (
                "user"
                if provider_role == "user"
                else "assistant"
                if provider_role in {"assistant", "agent"}
                else None
            )
            text = message.get("content")
            if not isinstance(text, str):
                text = message.get("text")
            if role is None or not isinstance(text, str):
                return
            text = text.strip()
            if not text:
                return
            # Emit a deliberately small allow-listed shape. Never forward the
            # provider object, which may contain metadata or credentials.
            self._events.put(
                {
                    "type": "transcript",
                    "role": role,
                    "text": text[:_MAX_TRANSCRIPT_CHARS],
                }
            )
            return
        if event_type in {"SettingsApplied", "SettingsAppliedSuccessfully"}:
            if self._settings_sent:
                self._settings_applied_event.set()
            else:
                return
            self._events.put(
                {"type": "settings_applied", "audio_format": dict(self.audio_format)}
            )
        elif event_type in {"Welcome", "Ready"}:
            self._welcome_event.set()
            self._events.put(
                {"type": "ready", "audio_format": dict(self.audio_format)}
            )
        elif event_type in {"UserStartedSpeaking", "AgentStartedSpeaking"}:
            self._events.put(
                {
                    "type": "speaking",
                    "speaking": True,
                    "role": "user" if event_type.startswith("User") else "agent",
                }
            )
        elif event_type in {"UserStoppedSpeaking", "AgentStoppedSpeaking"}:
            self._events.put(
                {
                    "type": "speaking",
                    "speaking": False,
                    "role": "user" if event_type.startswith("User") else "agent",
                }
            )
        elif event_type in {"AgentAudioDone", "AudioDone"}:
            self._events.put({"type": "audio_done"})
        elif event_type in {"Error", "AgentError"}:
            self._events.put({"type": "error", "message": "Deepgram Agent error"})
        elif isinstance(event_type, str) and event_type:
            self._events.put({"type": "status", "status": event_type[:80]})

    def _reader_loop(self) -> None:
        socket = self._socket
        if socket is None:
            return
        while not self._stop_event.is_set():
            try:
                raw = socket.recv()
            except queue.Empty:
                continue
            except (StopIteration, EOFError):
                break
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                if "timeout" in type(exc).__name__.casefold():
                    continue
                self._events.put({"type": "error", "message": "Deepgram Agent error"})
                break
            if raw is None:
                break
            self._provider_event(raw)

    def drain_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                return events

    def send_audio(self, audio: bytes | bytearray | memoryview) -> list[dict[str, Any]]:
        if not isinstance(audio, (bytes, bytearray, memoryview)):
            raise TypeError("audio must be bytes-like")
        payload = bytes(audio)
        if not payload:
            return self.drain_events()
        if self._state != "started" or self._socket is None:
            raise DeepgramAgentError("Deepgram Agent session is not active")
        try:
            self._send_binary(self._socket, payload)
        except Exception as exc:
            raise DeepgramAgentError() from exc
        return self.drain_events()

    push_audio = send_audio

    def _make_timing(self) -> dict[str, Any] | None:
        if self._started_mono is None:
            return None
        ended_mono = time.monotonic()
        self._ended_ts = self._ended_ts or utc_now_iso()
        return {
            "started_ts": self._started_ts,
            "first_audio_ts": self._first_audio_ts,
            "ended_ts": self._ended_ts,
            "time_to_first_audio_seconds": (
                self._first_audio_mono - self._started_mono
                if self._first_audio_mono is not None
                else None
            ),
            "total_duration_seconds": ended_mono - self._started_mono,
        }

    def stop(self) -> list[dict[str, Any]]:
        if self._state == "stopped":
            return self.drain_events()
        if self._state == "new":
            self._state = "stopped"
            return []
        self._stop_event.set()
        socket = self._socket
        if socket is not None:
            self._close_socket(socket)
        reader = self._reader
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=2.0)
        self._ended_ts = utc_now_iso()
        self._timing = self._make_timing()
        self._state = "stopped"
        events = self.drain_events()
        if self._timing is not None:
            events.append({"type": "timing", **self._timing})
        return events

    close = stop
    cancel = stop


__all__ = [
    "DEEPGRAM_AGENT_ENDPOINT",
    "DeepgramAgentConfig",
    "DeepgramAgentConfigurationError",
    "DeepgramAgentError",
    "DeepgramVoiceAgentSession",
    "deepgram_agent_enabled",
]
