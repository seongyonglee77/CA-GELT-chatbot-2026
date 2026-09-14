"""CosyVoice voice enrollment adapter for Model 1.

The adapter keeps the enrollment provider boundary small and testable: callers
inject a ``post`` transport in tests, while the default path uses only the
standard library.  Provider responses and errors are intentionally reduced to
safe, non-sensitive fields.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from .config import Model1Config, RequestTiming, utc_now_iso


class VoiceEnrollmentProviderError(RuntimeError):
    """A sanitized CosyVoice voice-enrollment failure."""

    def __init__(self, message: str = "CosyVoice voice enrollment request failed") -> None:
        # Do not retain provider exception text or response bodies.  SDKs and
        # HTTP clients sometimes echo request URLs, keys, or payloads.
        super().__init__(message)


@dataclass(frozen=True)
class VoiceEnrollmentResult:
    """The safe result of one enrollment request."""

    voice_id: str
    timing: RequestTiming

    @property
    def duration_seconds(self) -> float:
        return self.timing.duration_seconds

    @property
    def request_timing(self) -> RequestTiming:
        return self.timing


@dataclass(frozen=True)
class _HttpResponse:
    status_code: int
    body: bytes = field(repr=False)

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class VoiceEnrollmentHttpTransport(Protocol):
    """Minimal HTTP interface used by :class:`CosyVoiceVoiceEnrollment`."""

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Any = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        ...


class UrllibVoiceEnrollmentTransport:
    """Dependency-free JSON POST implementation for real provider calls."""

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Any = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> _HttpResponse:
        request_headers = {**headers, "Content-Type": "application/json"}
        request_data = (
            json_dumps(json).encode("utf-8") if json is not None else None
        )
        request = urllib.request.Request(
            url,
            data=request_data,
            headers=request_headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return _HttpResponse(response.status, response.read())
        except urllib.error.HTTPError as exc:
            # Preserve status handling in the adapter without retaining the
            # provider's response body in an exception.
            try:
                body = exc.read()
            except Exception:
                body = b""
            return _HttpResponse(exc.code, body)


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _status_code(response: Any) -> int:
    if isinstance(response, Mapping):
        value = response.get("status_code", response.get("status", 200))
    else:
        value = getattr(response, "status_code", getattr(response, "status", 200))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 200


def _response_json(response: Any) -> Any:
    if isinstance(response, Mapping):
        value = response.get("json", response.get("body", response))
        if callable(value):
            value = value()
        if isinstance(value, bytes):
            return json.loads(value.decode("utf-8"))
        if isinstance(value, str):
            return json.loads(value)
        return value
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
    raise ValueError("response did not contain JSON")


def _voice_id(payload: Any) -> str:
    """Extract only a provider voice identifier from known response shapes."""

    candidates: list[Any] = []
    if isinstance(payload, Mapping):
        candidates.append(payload.get("voice_id"))
        output = payload.get("output")
        if isinstance(output, Mapping):
            candidates.append(output.get("voice_id"))
            candidates.append(output.get("voiceId"))
        result = payload.get("result")
        if isinstance(result, Mapping):
            candidates.append(result.get("voice_id"))
            candidates.append(result.get("voiceId"))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    raise ValueError("provider response did not include a voice ID")


class CosyVoiceVoiceEnrollment:
    """Create a Singapore CosyVoice voice from an HTTPS reference-audio URL."""

    def __init__(
        self,
        config: Model1Config,
        *,
        clone_url: str | None = None,
        transport: VoiceEnrollmentHttpTransport | None = None,
        http_transport: VoiceEnrollmentHttpTransport | None = None,
    ) -> None:
        self.config = config
        # ``Model1Config`` in older project snapshots has no clone-url field;
        # callers can pass the Singapore ``COSYVOICE_CLONE_URL`` explicitly.
        configured_url = clone_url
        if configured_url is None:
            configured_url = getattr(config, "cosyvoice_clone_url", None)
        if configured_url is None:
            configured_url = getattr(config, "clone_url", None)
        if not isinstance(configured_url, str) or not configured_url.strip():
            raise ValueError("COSYVOICE_CLONE_URL must be configured")
        self.clone_url = configured_url.strip()
        if not _is_https_url(self.clone_url):
            raise ValueError("COSYVOICE_CLONE_URL must be an HTTPS URL")
        if transport is not None and http_transport is not None and transport is not http_transport:
            raise ValueError("pass only one HTTP transport")
        self.transport = transport or http_transport or UrllibVoiceEnrollmentTransport()

    def __repr__(self) -> str:
        # Keep endpoint and credential-bearing config out of diagnostics.
        return "CosyVoiceVoiceEnrollment(<configured>)"

    def enroll(
        self,
        audio_url: str | None = None,
        prefix: str | None = None,
    ) -> VoiceEnrollmentResult:
        """Enroll one voice using a provider-hosted HTTPS reference audio URL."""

        # Accept either natural call spelling (audio URL first) or the payload
        # spelling (prefix first) without changing the provider request shape.
        if (
            isinstance(audio_url, str)
            and isinstance(prefix, str)
            and not _is_https_url(audio_url)
            and _is_https_url(prefix)
        ):
            audio_url, prefix = prefix, audio_url
        if not isinstance(prefix, str) or not prefix.strip():
            raise ValueError("prefix must be a non-empty string")
        if not isinstance(audio_url, str) or not _is_https_url(audio_url):
            raise ValueError("audio_url must be an HTTPS URL")

        payload = {
            "model": "voice-enrollment",
            "input": {
                "action": "create_voice",
                "target_model": self.config.cosyvoice_model,
                "prefix": prefix.strip(),
                "url": audio_url,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.config.dashscope_api_key_cosyvoice}",
            "Content-Type": "application/json",
        }
        started_ts = utc_now_iso()
        started_mono = time.monotonic()
        try:
            response = self.transport.post(
                self.clone_url,
                headers=headers,
                json=payload,
                timeout=self.config.request_timeout_seconds,
            )
        except Exception as exc:
            raise VoiceEnrollmentProviderError() from exc

        status = _status_code(response)
        if not 200 <= status < 300:
            raise VoiceEnrollmentProviderError(
                f"CosyVoice voice enrollment request failed (HTTP {status})"
            )
        try:
            voice_id = _voice_id(_response_json(response))
        except Exception as exc:
            raise VoiceEnrollmentProviderError(
                "CosyVoice voice enrollment returned an invalid response"
            ) from exc

        timing = RequestTiming(
            started_ts=started_ts,
            ended_ts=utc_now_iso(),
            duration_seconds=max(0.0, time.monotonic() - started_mono),
        )
        return VoiceEnrollmentResult(voice_id=voice_id, timing=timing)

    # A verb that mirrors the provider operation is useful to application
    # boundaries while keeping one implementation and one result contract.
    create_voice = enroll


def _is_https_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(value)
    except ValueError:
        return False
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


__all__ = [
    "CosyVoiceVoiceEnrollment",
    "UrllibVoiceEnrollmentTransport",
    "VoiceEnrollmentHttpTransport",
    "VoiceEnrollmentProviderError",
    "VoiceEnrollmentResult",
]
