"""Fake-only checks for the configured live Model 1 session."""

from __future__ import annotations

import asyncio
import json
import threading
from urllib.parse import parse_qs, urlsplit

from apps.model1_web import server
from services.model1.config import Model1Config
from services.model1.personas import PersonaProfile
from services.model1.realtime import (
    DeepgramStreamingClient,
    LiveModel1Session,
    StreamingTiming,
)


def config() -> Model1Config:
    return Model1Config(
        deepgram_api_key="deepgram-secret",
        dashscope_api_key="qwen-secret",
        qwen_base_url="https://qwen.example/v1",
        qwen_model="qwen3.6-27b",
        dashscope_api_key_cosyvoice="cosy-secret",
        cosyvoice_ws_url="wss://cosy.example",
        cosyvoice_model="cosyvoice-v3-plus",
    )


def profile() -> PersonaProfile:
    return PersonaProfile(
        persona_id="demo",
        voice_id="demo-voice",
        display_label="Demo",
        source_grounded={},
        fictionalized={},
        behavior={},
    )


class FakeSocket:
    def __init__(self, incoming):
        self.incoming = list(incoming)
        self.sent = []
        self.closed = False

    def send(self, value):
        self.sent.append(value)

    def recv(self):
        if self.incoming:
            return self.incoming.pop(0)
        raise TimeoutError()

    def close(self):
        self.closed = True


def run(coro):
    return asyncio.run(coro)


def test_deepgram_url_header_binary_audio_and_finalize():
    sockets = []

    def factory(url, headers):
        socket = FakeSocket(
            [
                json.dumps(
                    {
                        "type": "Results",
                        "is_final": True,
                        "channel": {"alternatives": [{"transcript": "hello there"}]},
                    }
                )
            ]
        )
        sockets.append((url, headers, socket))
        return socket

    client = DeepgramStreamingClient(config(), websocket_factory=factory)
    client.start()
    client.send_audio(b"\x01\x02")
    events = client.stop()

    url, headers, socket = sockets[0]
    query = parse_qs(urlsplit(url).query)
    assert urlsplit(url).scheme == "wss"
    assert urlsplit(url).netloc == "api.deepgram.com"
    assert query == {
        "encoding": ["linear16"],
        "sample_rate": ["16000"],
        "channels": ["1"],
        "model": ["nova-3"],
        "punctuate": ["true"],
        "interim_results": ["true"],
        "smart_format": ["true"],
        "endpointing": ["300"],
    }
    assert headers == {"Authorization": "Token deepgram-secret"}
    assert socket.sent[0] == b"\x01\x02"
    assert json.loads(socket.sent[1]) == {"type": "Finalize"}
    assert json.loads(socket.sent[2]) == {"type": "CloseStream"}
    assert events == [{"type": "transcript_final", "text": "hello there"}]
    assert socket.closed


class FakeDeepgram:
    def __init__(self, *_args):
        self.audio = []
        self.started = False

    def start(self):
        self.started = True

    def send_audio(self, chunk):
        self.audio.append(chunk)

    def stop(self):
        return [{"type": "transcript_final", "text": "hello."}]


class FakeQwen:
    def __init__(self, *_args):
        self.transcripts = []

    def stream_text(self, transcript, *, system_prompt=None):
        self.transcripts.append((transcript, system_prompt))
        yield "Hello "
        yield "world."


class FakeTTS:
    def __init__(self, *_args):
        self.audio_chunks = []
        self.timing = StreamingTiming("start", "first", "end", 0.01, 0.02)

    def streaming_call(self, text):
        self.audio_chunks.append(text.encode("utf-8"))

    def complete(self):
        return None


def test_live_session_streams_safe_text_audio_after_stop():
    session = LiveModel1Session(
        profile(),
        config(),
        task_context={"topic": "greetings"},
        deepgram_factory=FakeDeepgram,
        qwen_factory=FakeQwen,
        tts_factory=FakeTTS,
    )

    run(session.start())
    run(session.send_audio(b"pcm"))
    events = run(session.stop())

    assert session.supports_audio_input is True
    assert {event["type"] for event in events} >= {"text_delta", "audio_chunk", "timing"}
    assert [event["text"] for event in events if event["type"] == "text_delta"] == [
        "Hello ",
        "world.",
    ]
    assert [event["data"] for event in events if event["type"] == "audio_chunk"] == [
        b"Hello world."
    ]


def test_live_session_redacts_provider_errors():
    class BrokenQwen:
        def stream_text(self, *_args, **_kwargs):
            raise RuntimeError("provider body qwen-secret")

    session = LiveModel1Session(
        profile(),
        config(),
        deepgram_factory=FakeDeepgram,
        qwen_factory=BrokenQwen,
        tts_factory=FakeTTS,
    )
    run(session.start())
    events = run(session.stop())
    serialized = json.dumps(events)
    assert {"type": "error", "message": "Session error"} in events
    assert "qwen-secret" not in serialized
    assert "provider body" not in serialized


def test_live_session_stream_stop_yields_before_provider_finishes():
    release = threading.Event()
    finished = threading.Event()

    class SlowQwen:
        def stream_text(self, transcript, *, system_prompt=None):
            del transcript, system_prompt
            yield "Hello."
            release.wait(timeout=2)
            finished.set()
            yield " Goodbye."

    async def collect():
        session = LiveModel1Session(
            profile(),
            config(),
            deepgram_factory=FakeDeepgram,
            qwen_factory=SlowQwen,
            tts_factory=FakeTTS,
        )
        await session.start()
        stream = await session.stream_stop()
        iterator = stream.__aiter__()
        first = await asyncio.wait_for(iterator.__anext__(), timeout=1)
        second = await asyncio.wait_for(iterator.__anext__(), timeout=1)
        assert first["type"] == "text_delta"
        assert second["type"] == "audio_chunk"
        assert not finished.is_set()
        release.set()
        remaining = [event async for event in iterator]
        return [first, second, *remaining]

    events = run(collect())
    assert finished.is_set()
    assert [event["text"] for event in events if event["type"] == "text_delta"] == [
        "Hello.",
        " Goodbye.",
    ]
    assert [event["data"] for event in events if event["type"] == "audio_chunk"] == [
        b"Hello.",
        b"Goodbye.",
    ]


def test_live_session_stream_stop_redacts_provider_errors():
    class BrokenQwen:
        def stream_text(self, *_args, **_kwargs):
            raise RuntimeError("provider body qwen-secret")

    async def collect():
        session = LiveModel1Session(
            profile(),
            config(),
            deepgram_factory=FakeDeepgram,
            qwen_factory=BrokenQwen,
            tts_factory=FakeTTS,
        )
        await session.start()
        stream = await session.stream_stop()
        return [event async for event in stream]

    events = run(collect())
    serialized = json.dumps(events)
    assert {"type": "error", "message": "Session error"} in events
    assert "qwen-secret" not in serialized
    assert "provider body" not in serialized


def test_protocol_prefers_stream_stop_async_iterable():
    class StreamingSession:
        timing = StreamingTiming("start", "first", "end", 0.01, 0.02)

        async def stream_stop(self):
            async def events():
                yield {"type": "text_delta", "text": "Hello"}
                yield {"type": "audio_chunk", "data": b"mp3"}

            return events()

    class FakeWebSocket:
        def __init__(self):
            self.sent = []

        async def send(self, value):
            self.sent.append(json.loads(value))

    async def stop():
        websocket = FakeWebSocket()
        await server.Model1Protocol()._stop(websocket, StreamingSession())
        return websocket.sent

    sent = run(stop())
    assert [event["type"] for event in sent] == ["text_delta", "audio_chunk", "timing", "stopped"]
    assert sent[1]["data"] == "bXAz"


def test_server_default_uses_live_session_only_with_config():
    configured = server._default_session_factory(profile(), None, config())
    unconfigured = server._default_session_factory(profile(), None, None)
    assert isinstance(configured, LiveModel1Session)
    assert configured.supports_audio_input is True
    assert unconfigured.supports_audio_input is False
