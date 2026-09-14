"""Fake-only checks for the Model 1 browser adapter."""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from types import SimpleNamespace

from apps.model1_web import server


class FakeWebSocket:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.messages:
            raise StopAsyncIteration
        return self.messages.pop(0)

    async def send(self, value):
        self.sent.append(json.loads(value))


class FakeRegistry:
    def resolve(self, persona_id):
        return SimpleNamespace(persona_id=persona_id)


class FakeSession:
    supports_audio_input = True

    def __init__(self):
        self.started = False
        self.stopped = False
        self.audio = []

    async def start(self):
        self.started = True
        return {"type": "timing", "total_duration_seconds": 0.0}

    async def send_audio(self, chunk):
        self.audio.append(chunk)
        return {"type": "text_delta", "text": "ok"}

    async def stop(self):
        self.stopped = True


class UnsupportedSession:
    supports_audio_input = False

    async def stop(self):
        return None


def run(coro):
    return asyncio.run(coro)


def events(ws, event_type):
    return [event for event in ws.sent if event.get("type") == event_type]


def test_start_and_stop_success():
    session = FakeSession()
    ws = FakeWebSocket([
        json.dumps({"type": "start", "persona_id": "demo", "task_context": {"topic": "greetings"}}),
        json.dumps({"type": "stop"}),
    ])
    app = server.create_app(lambda profile, task_context: session, registry=FakeRegistry())

    run(app.handle_client(ws))

    assert events(ws, "ready") == [{"type": "ready", "persona_id": "demo", "audio_input_supported": True}]
    assert events(ws, "stopped") == [{"type": "stopped"}]
    assert session.started is True
    assert session.stopped is True


def test_unsupported_audio_is_explicit():
    ws = FakeWebSocket([
        json.dumps({"type": "start", "persona_id": "demo"}),
        json.dumps({"type": "audio", "data": base64.b64encode(b"pcm").decode("ascii")}),
        json.dumps({"type": "stop"}),
    ])
    app = server.create_app(lambda profile, task_context: UnsupportedSession(), registry=FakeRegistry())

    run(app.handle_client(ws))

    assert events(ws, "error") == [{
        "type": "error",
        "message": "Live audio ingestion is not available in this MVP",
    }]
    assert events(ws, "stopped")


def test_invalid_json_and_type_are_safe():
    ws = FakeWebSocket(["not-json", json.dumps({"type": 7}), json.dumps({"type": "unknown"})])

    run(server.handle_client(ws, registry=FakeRegistry(), session_factory=lambda *_: UnsupportedSession()))

    assert [item["message"] for item in events(ws, "error")] == [
        "Invalid JSON message",
        "Invalid message type",
        "Unsupported message type",
    ]


def test_hidden_transcript_event_is_forwarded_without_provider_metadata():
    class TranscriptSession:
        supports_audio_input = True

        async def start(self):
            return None

        async def send_audio(self, _chunk):
            return {
                "type": "transcript",
                "role": "user",
                "text": "hello from the learner",
                "provider_payload": "must not be forwarded",
            }

        async def stop(self):
            return None

    ws = FakeWebSocket([
        json.dumps({"type": "start", "persona_id": "demo"}),
        json.dumps({"type": "audio", "data": base64.b64encode(b"pcm").decode("ascii")}),
        json.dumps({"type": "stop"}),
    ])
    app = server.create_app(
        lambda profile, task_context: TranscriptSession(),
        registry=FakeRegistry(),
    )

    run(app.handle_client(ws))

    transcript_events = events(ws, "transcript")
    assert transcript_events == [{
        "type": "transcript",
        "role": "user",
        "text": "hello from the learner",
    }]
    assert "provider_payload" not in json.dumps(ws.sent)


def test_secret_and_raw_profile_content_are_not_echoed():
    secret = "not-for-browser"

    class FailingSession:
        async def start(self):
            raise RuntimeError(f"provider body {secret}")

    ws = FakeWebSocket([
        json.dumps({"type": "start", "persona_id": "demo", "task_context": {"secret": secret}}),
    ])
    app = server.create_app(lambda profile, task_context: FailingSession(), registry=FakeRegistry())

    run(app.handle_client(ws))

    serialized = json.dumps(ws.sent)
    assert secret not in serialized
    assert "raw_profile" not in serialized
    assert all("provider body" not in json.dumps(item) for item in ws.sent)


def test_static_files_exist_without_credentials_or_provider_endpoints():
    root = Path(__file__).parents[1] / "apps" / "model1_web" / "static"
    html = (root / "index.html").read_text(encoding="utf-8")
    javascript = (root / "app.js").read_text(encoding="utf-8")
    static_text = f"{html}\n{javascript}".lower()

    assert (root / "index.html").is_file()
    assert (root / "app.js").is_file()
    assert "api_key" not in static_text
    assert "api-key" not in static_text
    # The portal names fixed persona IDs so its links can open their
    # conversation pages. Provider credentials and endpoints remain absent.
    assert "deepgram_api_key" not in static_text
    assert "dashscope" not in static_text
    assert "qwen" not in static_text
    assert "cosyvoice" not in static_text
    assert "https://" not in static_text


def test_global_englishes_portal_links_active_audio_persona_pages():
    root = Path(__file__).parents[1] / "apps" / "model1_web" / "static"
    portal = (root / "index.html").read_text(encoding="utf-8")
    pages = {
        "deepgram-kit": "deepgram_kit",
        "deepgram-kai": "deepgram_kai",
    }

    assert "Meeting Conversation Partners across Contexts" in portal
    assert "More conversation partners will be added soon" in portal
    assert "icnale-chn-004" not in portal
    assert "icnale-idn-001" not in portal
    assert "icnale-jpn-002" not in portal
    for slug, persona_id in pages.items():
        page = root / "personas" / slug / "index.html"
        html = page.read_text(encoding="utf-8")
        assert page.is_file()
        assert f'data-persona-id="{persona_id}"' in html
        assert "/persona.js" in html
        assert "Transcripts are not displayed on screen." in html
        assert f"/personas/{slug}/" in portal
