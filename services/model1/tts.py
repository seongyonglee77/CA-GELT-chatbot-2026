"""CosyVoice 2 text-to-speech adapter.

DashScope is imported only when a synthesis call is made.  Tests and callers
can inject ``synthesizer_factory`` and therefore do not need the optional SDK.
"""

from __future__ import annotations

import importlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .config import Model1Config, RequestTiming, utc_now_iso


class TTSProviderError(RuntimeError):
    """A sanitized CosyVoice provider failure."""

    def __init__(self, message: str = "CosyVoice TTS request failed") -> None:
        # Do not include SDK exception text: some SDKs echo credentials or
        # request payloads in their exception messages.
        super().__init__(message)


@dataclass(frozen=True)
class TTSResult:
    """Synthesized audio and its request timing."""

    audio_bytes: bytes = field(repr=False)
    timing: RequestTiming

    @property
    def audio(self) -> bytes:
        return self.audio_bytes

    @property
    def duration_seconds(self) -> float:
        return self.timing.duration_seconds


class CosyVoiceTTS:
    """Explicit CosyVoice adapter for one response utterance."""

    def __init__(
        self,
        config: Model1Config,
        *,
        synthesizer_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config
        self._synthesizer_factory = synthesizer_factory

    def _factory(self) -> Callable[..., Any]:
        if self._synthesizer_factory is not None:
            return self._synthesizer_factory

        try:
            dashscope = importlib.import_module("dashscope")
            tts_v2 = importlib.import_module("dashscope.audio.tts_v2")
            synthesizer_type = tts_v2.SpeechSynthesizer
        except Exception as exc:
            raise TTSProviderError("DashScope SDK is required for CosyVoice TTS") from exc

        # DashScope's Python SDK reads these module-level values when opening
        # its websocket.  Set them immediately before constructing the client.
        dashscope.base_websocket_api_url = self.config.cosyvoice_ws_url
        dashscope.api_key = self.config.dashscope_api_key_cosyvoice
        return synthesizer_type

    def synthesize(self, text: str, *, voice_id: str) -> TTSResult:
        if not isinstance(text, str):
            raise TypeError("TTS text must be a string")
        if not voice_id:
            raise ValueError("voice_id must not be empty")

        started_ts = utc_now_iso()
        started_mono = time.monotonic()
        try:
            synthesizer = self._factory()(
                model=self.config.cosyvoice_model,
                voice=voice_id,
            )
            raw_audio = synthesizer.call(text)
            audio = self._audio_bytes(raw_audio)
        except TTSProviderError:
            raise
        except Exception as exc:
            raise TTSProviderError() from exc

        ended_ts = utc_now_iso()
        timing = RequestTiming(
            started_ts=started_ts,
            ended_ts=ended_ts,
            duration_seconds=max(0.0, time.monotonic() - started_mono),
        )
        return TTSResult(audio_bytes=audio, timing=timing)

    @staticmethod
    def _audio_bytes(raw_audio: Any) -> bytes:
        if isinstance(raw_audio, bytes):
            return raw_audio
        if isinstance(raw_audio, (bytearray, memoryview)):
            return bytes(raw_audio)
        # Some SDK versions expose the response bytes through this method.
        getter = getattr(raw_audio, "get_audio_data", None)
        if callable(getter):
            data = getter()
            if isinstance(data, (bytes, bytearray, memoryview)):
                return bytes(data)
        raise TTSProviderError("CosyVoice returned no audio bytes")


# A descriptive alias helps applications migrate from "adapter" terminology
# without creating a second implementation or import path.
CosyVoiceTTSAdapter = CosyVoiceTTS

CosyVoiceAdapter = CosyVoiceTTS

__all__ = [
    "CosyVoiceAdapter",
    "CosyVoiceTTS",
    "CosyVoiceTTSAdapter",
    "TTSProviderError",
    "TTSResult",
]
