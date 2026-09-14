"""Streaming Model 1 provider adapters.

The module deliberately imports no optional provider SDK at import time.  The
Qwen adapter uses a small dependency-free HTTP transport by default, while
both adapters accept injected fakes so their streaming behavior can be tested
without network access or provider credentials.
"""

from __future__ import annotations

import asyncio
import inspect
import importlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Iterable, Iterator, Mapping, Protocol

from .config import Model1Config, utc_now_iso
from .personas import PersonaProfile
from .prompts import build_layered_system_prompt


class QwenStreamingError(RuntimeError):
    """A sanitized Qwen streaming failure.

    Provider response bodies and exception text are intentionally discarded:
    SDKs and gateways occasionally echo request payloads, including keys.
    """

    def __init__(self, message: str = "Qwen streaming request failed") -> None:
        super().__init__(message)


class CosyVoiceStreamingError(RuntimeError):
    """A sanitized CosyVoice streaming failure."""

    def __init__(self, message: str = "CosyVoice streaming request failed") -> None:
        super().__init__(message)


class StreamingHTTPTransport(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: float | None = None,
    ) -> Any:
        ...


class _UrllibStreamingTransport:
    """Open a response without eagerly reading it.

    ``urllib`` response objects expose ``__iter__`` and ``readline`` and are
    therefore sufficient for SSE without adding an HTTP dependency.
    """

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: float | None = None,
    ) -> Any:
        body = json_encode(json)
        request = urllib.request.Request(
            url,
            data=body,
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            # The caller only reads the status.  Never retain or expose the
            # body because it can contain credentials or the submitted prompt.
            return _HTTPErrorResponse(exc.code)


@dataclass(frozen=True)
class _HTTPErrorResponse:
    status_code: int


def json_encode(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _status_code(response: Any) -> int:
    value = getattr(response, "status_code", None)
    if value is None:
        value = getattr(response, "status", None)
    if value is None:
        getcode = getattr(response, "getcode", None)
        if callable(getcode):
            try:
                value = getcode()
            except Exception:
                value = None
    try:
        return int(value) if value is not None else 200
    except (TypeError, ValueError):
        return 200


def _as_text_chunk(chunk: Any) -> str:
    if isinstance(chunk, bytes):
        return chunk.decode("utf-8", errors="replace")
    if isinstance(chunk, str):
        return chunk
    return ""


def _response_chunks(response: Any) -> Iterable[Any]:
    """Return a line/chunk iterator from common HTTP response shapes."""

    if isinstance(response, (bytes, str)):
        return (response,)
    iter_lines = getattr(response, "iter_lines", None)
    if callable(iter_lines):
        return iter_lines()
    iter_bytes = getattr(response, "iter_bytes", None)
    if callable(iter_bytes):
        return iter_bytes()
    if isinstance(response, Iterable):
        return response
    read = getattr(response, "read", None)
    if callable(read):
        return (read(),)
    return ()


def _iter_sse_events(chunks: Iterable[Any]) -> Iterator[str]:
    """Yield complete SSE ``data:`` payloads from arbitrarily split chunks."""

    buffer = ""
    data_lines: list[str] = []

    def consume_line(line: str) -> Iterator[str]:
        nonlocal data_lines
        if line.startswith("data:"):
            value = line[5:]
            if value.startswith(" "):
                value = value[1:]
            data_lines.append(value)
        elif not line.strip():
            if data_lines:
                yield "\n".join(data_lines)
                data_lines = []
        # SSE comments and event/id fields do not carry model content.

    for raw_chunk in chunks:
        text = _as_text_chunk(raw_chunk)
        if not text:
            continue
        # HTTP streams conventionally use LF or CRLF.  Supporting lone CR is
        # useful for simple test iterators and costs no additional buffering.
        buffer += text.replace("\r\n", "\n").replace("\r", "\n")
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            yield from consume_line(line)

    if buffer:
        yield from consume_line(buffer)
    if data_lines:
        yield "\n".join(data_lines)


def _content_from_event(event: Any) -> str:
    if not isinstance(event, Mapping):
        return ""
    choices = event.get("choices")
    if not isinstance(choices, list) or not choices:
        # Some OpenAI-compatible gateways wrap the usual response in output.
        output = event.get("output")
        if isinstance(output, Mapping):
            return _content_from_event(output)
        return ""
    first = choices[0]
    if not isinstance(first, Mapping):
        return ""
    delta = first.get("delta")
    if not isinstance(delta, Mapping):
        delta = first.get("message")
    if not isinstance(delta, Mapping):
        return ""
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, Mapping) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "".join(parts)
    return ""


class DeepgramStreamingError(RuntimeError):
    """A sanitized Deepgram streaming failure."""

    def __init__(self, message: str = "Deepgram streaming request failed") -> None:
        super().__init__(message)


class DeepgramStreamingClient:
    """Small, dependency-optional Deepgram live transcription adapter.

    The websocket connection is opened lazily by :meth:`start`.  A factory can
    be injected by tests (or by an application that already owns a websocket
    implementation); the default imports ``websocket-client`` only when a
    session actually starts.
    """

    endpoint = "wss://api.deepgram.com/v1/listen"
    query_params: Mapping[str, str] = {
        "encoding": "linear16",
        "sample_rate": "16000",
        "channels": "1",
        "model": "nova-3",
        "punctuate": "true",
        "interim_results": "true",
        "smart_format": "true",
        "endpointing": "300",
    }

    def __init__(
        self,
        config: Model1Config,
        *,
        websocket_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config
        self.websocket_factory = websocket_factory
        self._socket: Any = None
        self._stopped = False

    @property
    def url(self) -> str:
        return f"{self.endpoint}?{urllib.parse.urlencode(self.query_params)}"

    @property
    def websocket_url(self) -> str:
        return self.url

    def __repr__(self) -> str:
        return f"{type(self).__name__}(endpoint={self.endpoint!r})"

    def _default_factory(self) -> Callable[..., Any]:
        try:
            websocket = importlib.import_module("websocket")
            factory = websocket.create_connection
        except Exception as exc:
            raise DeepgramStreamingError(
                "websocket-client is required for Deepgram streaming"
            ) from exc
        return factory

    def _connect(self) -> Any:
        factory = self.websocket_factory or self._default_factory()
        token = f"Token {self.config.deepgram_api_key}"
        headers = {"Authorization": token}
        header_lines = [f"Authorization: {token}"]
        if self.websocket_factory is None:
            try:
                return factory(
                    self.url,
                    header=header_lines,
                    timeout=getattr(self.config, "request_timeout_seconds", 60.0),
                )
            except Exception as exc:
                raise DeepgramStreamingError() from exc
        try:
            signature = inspect.signature(factory)
        except (TypeError, ValueError):
            signature = None
        try:
            if signature is not None:
                names = signature.parameters
                if "headers" in names:
                    return factory(self.url, headers=headers)
                if "header" in names:
                    return factory(self.url, header=header_lines)
                if any(
                    parameter.kind is inspect.Parameter.VAR_KEYWORD
                    for parameter in names.values()
                ):
                    return factory(self.url, headers=headers)
            return factory(self.url, headers)
        except Exception as exc:
            raise DeepgramStreamingError() from exc

    def start(self) -> None:
        if self._socket is not None:
            return
        self._socket = self._connect()
        self._stopped = False

    connect = start
    open = start

    def send_audio(self, audio: bytes | bytearray | memoryview) -> None:
        if not isinstance(audio, (bytes, bytearray, memoryview)):
            raise TypeError("audio must be bytes-like")
        payload = bytes(audio)
        if not payload:
            return
        if self._socket is None or self._stopped:
            raise DeepgramStreamingError("Deepgram stream is not active")
        sender = getattr(self._socket, "send", None)
        if not callable(sender):
            raise DeepgramStreamingError("Deepgram websocket is unavailable")
        try:
            binary_sender = getattr(self._socket, "send_binary", None)
            if callable(binary_sender):
                binary_sender(payload)
                return
            try:
                signature = inspect.signature(sender)
            except (TypeError, ValueError):
                signature = None
            if signature is not None and (
                "opcode" in signature.parameters
                or any(
                    parameter.kind is inspect.Parameter.VAR_KEYWORD
                    for parameter in signature.parameters.values()
                )
            ):
                # websocket-client's binary opcode is 2.  Other websocket
                # implementations simply accept the bytes-only fallback.
                sender(payload, opcode=2)
            else:
                sender(payload)
        except Exception as exc:
            raise DeepgramStreamingError() from exc

    push_audio = send_audio

    @classmethod
    def parse_message(cls, raw: Any) -> list[dict[str, str]]:
        """Extract only transcript text from one provider message."""

        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8")
            except UnicodeDecodeError:
                return []
        if isinstance(raw, str):
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                return []
        elif isinstance(raw, Mapping):
            payload = raw
        else:
            return []
        if not isinstance(payload, Mapping):
            return []
        if str(payload.get("type", "")).lower() in {"error", "err"}:
            return []
        channel = payload.get("channel")
        if not isinstance(channel, Mapping):
            return []
        alternatives = channel.get("alternatives")
        if not isinstance(alternatives, list) or not alternatives:
            return []
        first = alternatives[0]
        if not isinstance(first, Mapping):
            return []
        transcript = first.get("transcript")
        if not isinstance(transcript, str):
            return []
        transcript = transcript.strip()
        if not transcript:
            return []
        event_type = (
            "transcript_final"
            if payload.get("is_final") is True or payload.get("speech_final") is True
            else "transcript_delta"
        )
        # Transcript text is the only provider field allowed through.  A
        # bounded event prevents an unexpectedly large provider value from
        # becoming a browser payload.
        return [{"type": event_type, "text": transcript[:4000]}]

    def _receive_events(self) -> list[dict[str, str]]:
        if self._socket is None:
            return []
        receiver = getattr(self._socket, "recv", None)
        if not callable(receiver):
            receiver = getattr(self._socket, "receive", None)
        if not callable(receiver):
            return []
        set_timeout = getattr(self._socket, "settimeout", None)
        get_timeout = getattr(self._socket, "gettimeout", None)
        previous_timeout: Any = None
        if callable(get_timeout):
            try:
                previous_timeout = get_timeout()
            except Exception:
                previous_timeout = None
        if callable(set_timeout):
            try:
                set_timeout(0.25)
            except Exception:
                pass
        events: list[dict[str, str]] = []
        try:
            for _ in range(256):
                try:
                    raw = receiver()
                except (StopIteration, TimeoutError):
                    break
                except Exception:
                    # Provider exception text is deliberately not retained.
                    break
                if raw in (None, "", b""):
                    break
                events.extend(self.parse_message(raw))
        finally:
            if callable(set_timeout) and previous_timeout is not None:
                try:
                    set_timeout(previous_timeout)
                except Exception:
                    pass
        return events

    def stop(self) -> list[dict[str, str]]:
        if self._socket is None or self._stopped:
            return []
        sender = getattr(self._socket, "send", None)
        events: list[dict[str, str]] = []
        try:
            if not callable(sender):
                raise DeepgramStreamingError("Deepgram websocket is unavailable")
            sender(json.dumps({"type": "Finalize"}, separators=(",", ":")))
            events = self._receive_events()
        except DeepgramStreamingError:
            raise
        except Exception as exc:
            raise DeepgramStreamingError() from exc
        finally:
            try:
                if callable(sender):
                    sender(json.dumps({"type": "CloseStream"}, separators=(",", ":")))
            except Exception:
                pass
            close = getattr(self._socket, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            self._stopped = True
        return events

    close = stop


class QwenStreamingClient:
    """OpenAI-compatible Qwen chat-completions SSE client."""

    MAX_MAX_TOKENS = 4096

    def __init__(
        self,
        config: Model1Config,
        *,
        transport: StreamingHTTPTransport | None = None,
        stream_iterator: Callable[[Any], Iterable[Any]] | Iterable[Any] | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.config = config
        self.transport = transport or _UrllibStreamingTransport()
        self.stream_iterator = stream_iterator
        configured = max_tokens if max_tokens is not None else getattr(config, "qwen_max_tokens", 96)
        try:
            configured_int = int(configured)
        except (TypeError, ValueError):
            configured_int = 256
        self.max_tokens = max(1, min(configured_int, self.MAX_MAX_TOKENS))

    @property
    def endpoint(self) -> str:
        base = str(self.config.qwen_base_url).rstrip("/")
        return base if base.endswith("/chat/completions") else f"{base}/chat/completions"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(endpoint={self.endpoint!r}, max_tokens={self.max_tokens})"

    @staticmethod
    def _messages(value: Any) -> list[Mapping[str, Any]]:
        if isinstance(value, str):
            return [{"role": "user", "content": value}]
        if isinstance(value, Mapping):
            return [value]
        try:
            result = list(value)
        except TypeError as exc:
            raise TypeError("messages must be a string or iterable of mappings") from exc
        if not all(isinstance(item, Mapping) for item in result):
            raise TypeError("messages must contain mappings")
        return result

    def _iterator(self, response: Any) -> Iterable[Any]:
        injected = self.stream_iterator
        if injected is None:
            return _response_chunks(response)
        if callable(injected):
            try:
                return injected(response)
            except TypeError:
                # A zero-argument iterator factory is convenient in tests.
                return injected()  # type: ignore[call-arg]
        return injected

    def stream(
        self,
        messages: str | Iterable[Mapping[str, Any]],
        *,
        model: str | None = None,
    ) -> Iterator[str]:
        """Yield non-empty text deltas as soon as SSE events arrive."""

        payload: dict[str, Any] = {
            "model": model or self.config.qwen_model,
            "messages": self._messages(messages),
            "stream": True,
            "enable_thinking": False,
            "max_tokens": self.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.config.dashscope_api_key}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        }
        try:
            response = self.transport.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=getattr(self.config, "request_timeout_seconds", 60.0),
            )
        except Exception as exc:
            raise QwenStreamingError() from exc

        status = _status_code(response)
        if not 200 <= status < 300:
            self._close(response)
            raise QwenStreamingError(f"Qwen streaming request failed (HTTP {status})")

        try:
            for raw_event in _iter_sse_events(self._iterator(response)):
                if raw_event.strip() == "[DONE]":
                    break
                if not raw_event.strip():
                    continue
                try:
                    event = json.loads(raw_event)
                except (TypeError, ValueError) as exc:
                    raise QwenStreamingError("Qwen stream returned invalid data") from exc
                delta = _content_from_event(event)
                if delta:
                    yield delta
        except QwenStreamingError:
            raise
        except Exception as exc:
            raise QwenStreamingError() from exc
        finally:
            self._close(response)

    stream_chat = stream
    stream_response = stream

    def stream_text(
        self,
        transcript: str,
        *,
        system_prompt: str | None = None,
    ) -> Iterator[str]:
        messages: list[Mapping[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": transcript})
        return self.stream(messages)

    @staticmethod
    def _close(response: Any) -> None:
        close = getattr(response, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


class SentenceChunker:
    """Incrementally split text at punctuation or a bounded character size."""

    SENTENCE_PUNCTUATION = frozenset(".!?。！？;；\n")

    def __init__(self, max_chars: int = 120) -> None:
        if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
            raise ValueError("max_chars must be a positive integer")
        self.max_chars = max_chars
        self._buffer: list[str] = []

    def push(self, delta: str) -> list[str]:
        if not isinstance(delta, str):
            raise TypeError("text delta must be a string")
        chunks: list[str] = []
        for character in delta:
            self._buffer.append(character)
            if character in self.SENTENCE_PUNCTUATION or len(self._buffer) >= self.max_chars:
                chunk = self._take()
                if chunk:
                    chunks.append(chunk)
        return chunks

    def flush(self) -> list[str]:
        chunk = self._take()
        return [chunk] if chunk else []

    def _take(self) -> str:
        text = "".join(self._buffer).strip()
        self._buffer.clear()
        return text


def sentence_chunker(
    deltas: Iterable[str] | str,
    *,
    max_chars: int = 120,
) -> Iterator[str]:
    """Yield sentence-sized chunks from an iterable of Qwen deltas."""

    chunker = SentenceChunker(max_chars=max_chars)
    source: Iterable[str] = (deltas,) if isinstance(deltas, str) else deltas
    for delta in source:
        yield from chunker.push(delta)
    yield from chunker.flush()


@dataclass(frozen=True)
class StreamingTiming:
    """Monotonic timing for one TTS stream."""

    started_ts: str
    first_audio_ts: str | None
    ended_ts: str | None
    time_to_first_audio_seconds: float | None
    total_duration_seconds: float | None


class _StreamingResultCallback:
    """Duck-typed callback; optionally subclassed from DashScope's callback."""

    def __init__(self, owner: "CosyVoiceStreamingSynthesizer") -> None:
        self.owner = owner

    def on_open(self, *args: Any, **kwargs: Any) -> None:
        return None

    def on_data(self, data: Any, *args: Any, **kwargs: Any) -> None:
        self.owner._on_audio(data)

    def on_complete(self, *args: Any, **kwargs: Any) -> None:
        self.owner._on_complete()

    def on_error(self, *args: Any, **kwargs: Any) -> None:
        self.owner._on_error()


class CosyVoiceStreamingSynthesizer:
    """DashScope CosyVoice v3-plus streaming adapter."""

    def __init__(
        self,
        config: Model1Config,
        voice_id: str,
        *,
        synthesizer_factory: Callable[..., Any] | None = None,
    ) -> None:
        if not voice_id:
            raise ValueError("voice_id must not be empty")
        self.config = config
        self.voice_id = voice_id
        self._synthesizer_factory = synthesizer_factory
        self._synthesizer: Any = None
        self._callback: Any = None
        self._state = "new"
        self._error: CosyVoiceStreamingError | None = None
        self._audio_chunks: list[bytes] = []
        self._started_mono: float | None = None
        self._started_ts: str | None = None
        self._first_audio_mono: float | None = None
        self._first_audio_ts: str | None = None
        self._ended_mono: float | None = None
        self._ended_ts: str | None = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(voice_id={self.voice_id!r}, state={self._state!r})"

    @property
    def audio_chunks(self) -> list[bytes]:
        return list(self._audio_chunks)

    @property
    def audio(self) -> bytes:
        return b"".join(self._audio_chunks)

    @property
    def time_to_first_audio_seconds(self) -> float | None:
        if self._started_mono is None or self._first_audio_mono is None:
            return None
        return max(0.0, self._first_audio_mono - self._started_mono)

    @property
    def first_audio_seconds(self) -> float | None:
        return self.time_to_first_audio_seconds

    @property
    def first_audio_latency_seconds(self) -> float | None:
        return self.time_to_first_audio_seconds

    @property
    def total_duration_seconds(self) -> float | None:
        if self._started_mono is None:
            return None
        end = self._ended_mono if self._ended_mono is not None else time.monotonic()
        return max(0.0, end - self._started_mono)

    @property
    def total_latency_seconds(self) -> float | None:
        return self.total_duration_seconds

    @property
    def timing(self) -> StreamingTiming | None:
        if self._started_ts is None:
            return None
        return StreamingTiming(
            started_ts=self._started_ts,
            first_audio_ts=self._first_audio_ts,
            ended_ts=self._ended_ts,
            time_to_first_audio_seconds=self.time_to_first_audio_seconds,
            total_duration_seconds=self.total_duration_seconds,
        )

    def _resolve_factory(self) -> tuple[Callable[..., Any], type[Any] | None]:
        if self._synthesizer_factory is not None:
            return self._synthesizer_factory, None
        try:
            dashscope = importlib.import_module("dashscope")
            tts_v2 = importlib.import_module("dashscope.audio.tts_v2")
            synthesizer_type = tts_v2.SpeechSynthesizer
            callback_type = getattr(tts_v2, "ResultCallback", None)
        except Exception as exc:
            raise CosyVoiceStreamingError("DashScope SDK is required for CosyVoice streaming") from exc
        dashscope.base_websocket_api_url = self.config.cosyvoice_ws_url
        dashscope.api_key = self.config.dashscope_api_key_cosyvoice
        return synthesizer_type, callback_type

    def _ensure_started(self) -> Any:
        if self._state == "cancelled":
            raise CosyVoiceStreamingError("CosyVoice stream was cancelled")
        if self._state == "complete":
            raise CosyVoiceStreamingError("CosyVoice stream is already complete")
        if self._synthesizer is not None:
            return self._synthesizer
        self._started_mono = time.monotonic()
        self._started_ts = utc_now_iso()
        factory, callback_type = self._resolve_factory()
        callback_class: type[Any] = _StreamingResultCallback
        if isinstance(callback_type, type):
            callback_class = type(
                "CosyVoiceResultCallback",
                (_StreamingResultCallback, callback_type),
                {"__init__": _StreamingResultCallback.__init__},
            )
        self._callback = callback_class(self)
        try:
            self._synthesizer = factory(
                model=self.config.cosyvoice_model,
                voice=self.voice_id,
                callback=self._callback,
            )
        except Exception as exc:
            self._finish()
            raise CosyVoiceStreamingError() from exc
        self._state = "active"
        return self._synthesizer

    def streaming_call(self, text: str) -> Any:
        if not isinstance(text, str):
            raise TypeError("TTS text must be a string")
        if not text:
            return None
        synthesizer = self._ensure_started()
        method = getattr(synthesizer, "streaming_call", None)
        if not callable(method):
            raise CosyVoiceStreamingError("CosyVoice synthesizer does not support streaming")
        try:
            result = method(text)
        except Exception as exc:
            self._finish()
            raise CosyVoiceStreamingError() from exc
        self._raise_callback_error()
        return result

    def complete(self) -> bytes:
        if self._state == "new":
            self._ensure_started()
        if self._state == "complete":
            return self.audio
        if self._state == "cancelled":
            return self.audio
        method = getattr(self._synthesizer, "streaming_complete", None)
        if not callable(method):
            method = getattr(self._synthesizer, "complete", None)
        try:
            if callable(method):
                method()
        except Exception as exc:
            self._finish()
            raise CosyVoiceStreamingError() from exc
        self._raise_callback_error()
        self._state = "complete"
        self._finish()
        return self.audio

    def cancel(self) -> None:
        if self._state in {"cancelled", "complete"}:
            return
        if self._state == "new":
            self._state = "cancelled"
            return
        method = getattr(self._synthesizer, "streaming_cancel", None)
        if not callable(method):
            method = getattr(self._synthesizer, "cancel", None)
        try:
            if callable(method):
                method()
        except Exception as exc:
            self._finish()
            raise CosyVoiceStreamingError() from exc
        self._state = "cancelled"
        self._finish()

    def _on_audio(self, data: Any) -> None:
        getter = getattr(data, "get_audio_data", None)
        if not isinstance(data, (bytes, bytearray, memoryview)) and callable(getter):
            try:
                data = getter()
            except Exception:
                data = None
        if isinstance(data, (bytearray, memoryview)):
            data = bytes(data)
        if not isinstance(data, bytes) or not data:
            return
        if self._started_mono is None:
            self._started_mono = time.monotonic()
            self._started_ts = utc_now_iso()
        if self._first_audio_mono is None:
            self._first_audio_mono = time.monotonic()
            self._first_audio_ts = utc_now_iso()
        self._audio_chunks.append(data)

    def _on_complete(self) -> None:
        self._finish()

    def _on_error(self) -> None:
        self._error = CosyVoiceStreamingError()
        self._finish()

    def _raise_callback_error(self) -> None:
        if self._error is not None:
            raise self._error

    def _finish(self) -> None:
        if self._started_mono is not None and self._ended_mono is None:
            self._ended_mono = time.monotonic()
            self._ended_ts = utc_now_iso()


class LiveModel1Session:
    """One browser microphone turn through Deepgram, Qwen, and CosyVoice.

    Provider adapters remain synchronous because both the websocket and SDK
    implementations may block.  Public methods move that work to a worker
    thread, keeping the WebSocket event loop responsive.  Final Deepgram
    transcripts are intentionally consumed at ``stop``; this MVP does not
    attempt full-duplex barge-in.
    """

    supports_audio_input = True

    def __init__(
        self,
        profile: PersonaProfile,
        config: Model1Config,
        task_context: Any = None,
        *,
        deepgram_factory: Callable[..., Any] | Any | None = None,
        qwen_factory: Callable[..., Any] | Any | None = None,
        tts_factory: Callable[..., Any] | Any | None = None,
    ) -> None:
        self.profile = profile
        self.config = config
        self.task_context = task_context
        self.deepgram_factory = deepgram_factory
        self.qwen_factory = qwen_factory
        self.tts_factory = tts_factory
        self._deepgram: Any = None
        self._tts: Any = None
        self._timing: StreamingTiming | None = None
        self._state = "new"
        self._events: list[dict[str, Any]] = []

    @property
    def timing(self) -> StreamingTiming | None:
        return self._timing

    @staticmethod
    def _factory_value(factory: Any, default: Callable[..., Any], *args: Any) -> Any:
        if factory is None:
            return default(*args)
        if not callable(factory):
            return factory
        try:
            signature = inspect.signature(factory)
        except (TypeError, ValueError):
            return factory(*args)
        candidates = [
            (args, {}),
            ((), {"config": args[0]}) if args else ((), {}),
            ((), {}),
        ]
        if len(args) > 1:
            candidates.insert(1, ((), {"config": args[0], "voice_id": args[1]}))
        for call_args, kwargs in candidates:
            try:
                signature.bind(*call_args, **kwargs)
            except TypeError:
                continue
            return factory(*call_args, **kwargs)
        raise TypeError("provider factory has an unsupported signature")

    def _new_deepgram(self) -> Any:
        return self._factory_value(
            self.deepgram_factory,
            DeepgramStreamingClient,
            self.config,
        )

    def _new_qwen(self) -> Any:
        return self._factory_value(self.qwen_factory, QwenStreamingClient, self.config)

    def _new_tts(self) -> Any:
        return self._factory_value(
            self.tts_factory,
            CosyVoiceStreamingSynthesizer,
            self.config,
            getattr(self.profile, "voice_id", ""),
        )

    @staticmethod
    def _first_method(target: Any, names: tuple[str, ...]) -> Callable[..., Any] | None:
        for name in names:
            method = getattr(target, name, None)
            if callable(method):
                return method
        return None

    @staticmethod
    def _safe_error() -> dict[str, str]:
        return {"type": "error", "message": "Session error"}

    async def start(self) -> Any:
        if self._state == "started":
            return None
        try:
            self._deepgram = await asyncio.to_thread(self._new_deepgram)
            if inspect.isawaitable(self._deepgram):
                self._deepgram = await self._deepgram
            method = self._first_method(self._deepgram, ("start", "connect", "open"))
            if method is None:
                raise DeepgramStreamingError("Deepgram websocket is unavailable")
            result = await asyncio.to_thread(method)
            if inspect.isawaitable(result):
                await result
            self._state = "started"
            return None
        except Exception:
            self._state = "failed"
            return self._safe_error()

    async def send_audio(self, audio: bytes | bytearray | memoryview) -> Any:
        if not isinstance(audio, (bytes, bytearray, memoryview)):
            return self._safe_error()
        if self._state != "started" or self._deepgram is None:
            return self._safe_error()
        method = self._first_method(self._deepgram, ("send_audio", "push_audio", "send"))
        if method is None:
            return self._safe_error()
        try:
            result = await asyncio.to_thread(method, bytes(audio))
            if inspect.isawaitable(result):
                result = await result
            # Interim transcripts are intentionally not forwarded to the
            # browser in this first version; final text is handled at stop.
            return None
        except Exception:
            return self._safe_error()

    @staticmethod
    def _transcript(events: Any) -> str:
        if isinstance(events, Mapping):
            events = [events]
        if isinstance(events, str):
            parsed = DeepgramStreamingClient.parse_message(events)
            if parsed:
                events = parsed
            else:
                return events.strip()[:4000]
        if not isinstance(events, Iterable):
            return ""
        parts: list[str] = []
        for event in events:
            if isinstance(event, (str, bytes)):
                event = DeepgramStreamingClient.parse_message(event)
                if isinstance(event, list):
                    for parsed in event:
                        if parsed.get("type") == "transcript_final":
                            text = parsed.get("text")
                            if isinstance(text, str) and text.strip():
                                parts.append(text.strip())
                continue
            if not isinstance(event, Mapping) or event.get("type") != "transcript_final":
                continue
            text = event.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        return " ".join(parts)[:4000]

    def _system_prompt(self) -> str | None:
        profile_context = getattr(self.profile, "prompt_context", None)
        if not isinstance(profile_context, Mapping):
            profile_context = {
                "persona_id": getattr(self.profile, "persona_id", ""),
                "display_label": getattr(self.profile, "display_label", ""),
            }
        context = self.task_context if self.task_context is not None else {}
        prompt = build_layered_system_prompt(profile_context, context)
        return (
            f"{prompt}\n\n"
            "REALTIME TURN CONSTRAINT: Reply in at most two short sentences "
            "and no more than 32 words. Answer the learner directly. Do not "
            "introduce yourself, discuss feelings, emotions, weather, system "
            "capabilities, or artificial intelligence unless the learner "
            "explicitly asks about that topic. Do not give an encyclopedia "
            "explanation. Ask at most one short follow-up question."
        )

    @staticmethod
    def _qwen_stream(qwen: Any, transcript: str, system_prompt: str | None) -> Iterable[Any]:
        method = getattr(qwen, "stream_text", None)
        if callable(method):
            try:
                signature = inspect.signature(method)
            except (TypeError, ValueError):
                signature = None
            if signature is not None and "system_prompt" in signature.parameters:
                return method(transcript, system_prompt=system_prompt)
            return method(transcript)
        method = getattr(qwen, "stream", None)
        if callable(method):
            messages: list[Mapping[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": transcript})
            return method(messages)
        raise QwenStreamingError("Qwen streaming client is unavailable")

    @staticmethod
    def _new_audio_events(synthesizer: Any, before: int) -> tuple[list[dict[str, Any]], int]:
        chunks = getattr(synthesizer, "audio_chunks", None)
        if not isinstance(chunks, (list, tuple)):
            return [], before
        events: list[dict[str, Any]] = []
        current = len(chunks)
        for chunk in chunks[before:]:
            if isinstance(chunk, (bytes, bytearray, memoryview)) and chunk:
                events.append({"type": "audio_chunk", "data": bytes(chunk)})
        return events, current

    def _tts_chunk(
        self,
        synthesizer: Any,
        text: str,
        audio_index: int,
        *,
        emit: Callable[[dict[str, Any]], None] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        method = self._first_method(synthesizer, ("streaming_call", "stream"))
        if method is None:
            raise CosyVoiceStreamingError("CosyVoice synthesizer is unavailable")

        events: list[dict[str, Any]] = []

        def append(event: dict[str, Any]) -> None:
            events.append(event)
            if emit is not None:
                emit(event)

        result = method(text)
        new_events, audio_index = self._new_audio_events(synthesizer, audio_index)
        for event in new_events:
            append(event)
        if isinstance(result, (bytes, bytearray, memoryview)) and result and not events:
            append({"type": "audio_chunk", "data": bytes(result)})
        elif isinstance(result, Mapping) and not events:
            chunk = result.get("data")
            if isinstance(chunk, (bytes, bytearray, memoryview)) and chunk:
                append({"type": "audio_chunk", "data": bytes(chunk)})
        elif isinstance(result, Iterable) and not isinstance(result, (str, bytes, bytearray, memoryview)):
            if not events:
                for chunk in result:
                    if isinstance(chunk, (bytes, bytearray, memoryview)) and chunk:
                        append({"type": "audio_chunk", "data": bytes(chunk)})
        return events, audio_index

    def _finish_sync(
        self,
        *,
        emit: Callable[[dict[str, Any]], None] | None = None,
        aggregate_audio: bool = True,
        include_timing: bool = True,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        def append(event: dict[str, Any]) -> None:
            events.append(event)
            if emit is not None:
                emit(event)

        deepgram = self._deepgram
        transcript_events: Any = []
        if deepgram is not None:
            method = self._first_method(deepgram, ("stop", "close"))
            if method is not None:
                transcript_events = method()
        transcript = self._transcript(transcript_events)
        if not transcript:
            return events

        try:
            qwen = self._new_qwen()
            stream = self._qwen_stream(qwen, transcript, self._system_prompt())
            if isinstance(stream, str):
                stream = (stream,)
            chunker = SentenceChunker()
            synthesizer = self._new_tts()
            self._tts = synthesizer
            audio_index = 0
            for delta in stream:
                if not isinstance(delta, str) or not delta:
                    continue
                # Preserve Qwen's deltas as text events while feeding the
                # same deltas through the shared sentence chunker.
                append({"type": "text_delta", "text": delta[:4000]})
                for chunk in chunker.push(delta):
                    _, audio_index = self._tts_chunk(
                        synthesizer,
                        chunk,
                        audio_index,
                        emit=append,
                    )
            for chunk in chunker.flush():
                _, audio_index = self._tts_chunk(
                    synthesizer,
                    chunk,
                    audio_index,
                    emit=append,
                )
            complete = self._first_method(synthesizer, ("complete", "streaming_complete"))
            if complete is not None:
                complete()
            tts_events, _ = self._new_audio_events(synthesizer, audio_index)
            for event in tts_events:
                append(event)
            timing = getattr(synthesizer, "timing", None)
            if include_timing and timing is not None:
                self._timing = timing
                append({"type": "timing", **self._timing_payload(timing)})
            elif timing is not None:
                self._timing = timing
        except Exception:
            append(self._safe_error())
        if aggregate_audio:
            audio_parts = [
                event["data"]
                for event in events
                if event.get("type") == "audio_chunk"
                and isinstance(event.get("data"), (bytes, bytearray, memoryview))
            ]
            if audio_parts:
                combined_audio = b"".join(bytes(part) for part in audio_parts)
                events = [event for event in events if event.get("type") != "audio_chunk"]
                insert_at = len(events)
                for index, event in enumerate(events):
                    if event.get("type") == "timing":
                        insert_at = index
                        break
                events.insert(insert_at, {"type": "audio_chunk", "data": combined_audio})
        return events

    @staticmethod
    def _timing_payload(value: Any) -> dict[str, Any]:
        if isinstance(value, StreamingTiming):
            source: Mapping[str, Any] = {
                "started_ts": value.started_ts,
                "first_audio_ts": value.first_audio_ts,
                "ended_ts": value.ended_ts,
                "time_to_first_audio_seconds": value.time_to_first_audio_seconds,
                "total_duration_seconds": value.total_duration_seconds,
            }
        elif isinstance(value, Mapping):
            source = value
        else:
            source = {
                key: getattr(value, key, None)
                for key in (
                    "started_ts",
                    "first_audio_ts",
                    "ended_ts",
                    "time_to_first_audio_seconds",
                    "total_duration_seconds",
                )
            }
        result: dict[str, Any] = {}
        for key in (
            "started_ts",
            "first_audio_ts",
            "ended_ts",
            "time_to_first_audio_seconds",
            "total_duration_seconds",
        ):
            item = source.get(key)
            if key.endswith("_ts") and isinstance(item, str) and len(item) <= 80:
                result[key] = item
            elif not key.endswith("_ts") and isinstance(item, (int, float)) and not isinstance(item, bool):
                result[key] = item
        return result

    async def stop(self) -> list[dict[str, Any]]:
        if self._state == "stopped":
            return list(self._events)
        if self._state not in {"started", "failed"}:
            self._state = "stopped"
            self._events = []
            return []
        try:
            events = await asyncio.to_thread(self._finish_sync)
        except Exception:
            events = [self._safe_error()]
        self._state = "stopped"
        self._events = list(events)
        return events

    @staticmethod
    def _event_iterator(events: Iterable[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
        async def iterate() -> AsyncIterator[dict[str, Any]]:
            for event in events:
                yield event

        return iterate()

    async def stream_stop(self) -> AsyncIterator[dict[str, Any]]:
        """Finalize the turn while yielding safe text/audio events promptly.

        Provider calls remain in a worker thread.  The worker uses
        ``call_soon_threadsafe`` to bridge each already-sanitized event into
        this loop, so the first Qwen delta and each available TTS chunk can be
        sent without waiting for the full response.
        """

        if self._state == "stopped":
            return self._event_iterator(self._events)
        if self._state not in {"started", "failed"}:
            self._state = "stopped"
            self._events = []
            return self._event_iterator(())

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Any] = asyncio.Queue()
        sentinel = object()

        def publish(event: dict[str, Any]) -> None:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except RuntimeError:
                # The consumer loop may have been closed after disconnect.
                pass

        def finish_worker() -> None:
            try:
                events = self._finish_sync(
                    emit=publish,
                    aggregate_audio=False,
                    include_timing=False,
                )
            except Exception:
                events = [self._safe_error()]
                publish(events[0])
            self._state = "stopped"
            self._events = list(events)
            try:
                loop.call_soon_threadsafe(queue.put_nowait, sentinel)
            except RuntimeError:
                pass

        asyncio.create_task(asyncio.to_thread(finish_worker))

        async def iterate() -> AsyncIterator[dict[str, Any]]:
            while True:
                event = await queue.get()
                if event is sentinel:
                    break
                if isinstance(event, Mapping):
                    yield dict(event)

        return iterate()


# Short aliases are useful to code that calls the adapter a client/provider.
DeepgramStreamingProviderError = DeepgramStreamingError
QwenStreamingProviderError = QwenStreamingError
CosyVoiceStreamingProviderError = CosyVoiceStreamingError


__all__ = [
    "CosyVoiceStreamingError",
    "CosyVoiceStreamingProviderError",
    "CosyVoiceStreamingSynthesizer",
    "DeepgramStreamingClient",
    "DeepgramStreamingError",
    "DeepgramStreamingProviderError",
    "LiveModel1Session",
    "QwenStreamingClient",
    "QwenStreamingError",
    "QwenStreamingProviderError",
    "SentenceChunker",
    "StreamingTiming",
    "sentence_chunker",
]
