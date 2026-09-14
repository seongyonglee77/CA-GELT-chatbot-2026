"""Fake websocket checks for the integrated Deepgram Voice Agent path."""

from __future__ import annotations

import json
import queue
import threading
import time

import pytest

from services.model1.deepgram_agent import (
    DeepgramAgentConfig,
    DeepgramAgentError,
    DeepgramVoiceAgentSession,
)
from services.model1.personas import PersonaRegistry


class FakeProviderSocket:
    def __init__(self, *, auto_settings_applied: bool = True) -> None:
        self.sent: list[tuple[object, int | None]] = []
        self.incoming: queue.Queue[object] = queue.Queue()
        self.closed = False
        self.auto_settings_applied = auto_settings_applied
        self.welcome_emitted = False
        self.settings_sent = threading.Event()
        self.settings_applied_emitted = threading.Event()

    def send(self, value, opcode=None):
        self.sent.append((value, opcode))
        if opcode is None and isinstance(value, str):
            payload = json.loads(value)
            if payload.get("type") == "Settings":
                assert self.welcome_emitted
                self.settings_sent.set()
                if self.auto_settings_applied:
                    self.emit_settings_applied()

    def recv(self):
        if not self.welcome_emitted:
            self.welcome_emitted = True
            return json.dumps({"type": "Welcome"})
        value = self.incoming.get(timeout=0.2)
        if value is None:
            raise EOFError()
        return value

    def close(self):
        self.closed = True
        self.incoming.put(None)

    def emit_settings_applied(self):
        self.settings_applied_emitted.set()
        self.incoming.put(json.dumps({"type": "SettingsApplied"}))


def profile(persona_id: str = "deepgram_kit"):
    return PersonaRegistry("voices/personas").resolve(persona_id)


def wait_events(session: DeepgramVoiceAgentSession, count: int = 1):
    for _ in range(100):
        events = session.drain_events()
        if len(events) >= count:
            return events
        time.sleep(0.005)
    return session.drain_events()


def test_settings_select_voice_and_layered_prompt():
    socket = FakeProviderSocket()
    session = DeepgramVoiceAgentSession(
        profile(),
        DeepgramAgentConfig("test-key"),
        websocket_factory=lambda url, header=None: socket,
    )

    events = session.start()
    settings = json.loads(socket.sent[0][0])
    assert settings["agent"]["speak"]["provider"]["model"] == "flux-kit-en"
    assert settings["agent"]["listen"]["provider"]["model"] == "flux-general-en"
    assert settings["agent"]["think"]["provider"]["model"] == "gemini-3.1-flash-lite"
    assert "# Layer 1" in settings["agent"]["think"]["prompt"]
    assert "# Layer 3" in settings["agent"]["think"]["prompt"]
    assert "Kit" in settings["agent"]["think"]["prompt"]
    assert events[0]["audio_format"] == {
        "encoding": "linear16",
        "sample_rate": 24000,
        "container": "none",
    }
    session.stop()


def test_binary_media_and_safe_provider_events():
    socket = FakeProviderSocket()
    session = DeepgramVoiceAgentSession(
        profile("deepgram_kai"),
        api_key="test-key",
        websocket_factory=lambda url, headers=None: socket,
    )
    session.start()
    socket.incoming.put(json.dumps({"type": "ConversationText", "content": "secret transcript"}))
    socket.incoming.put(json.dumps({"type": "UserStartedSpeaking"}))
    socket.incoming.put(json.dumps({"type": "AgentStartedSpeaking"}))
    socket.incoming.put(b"pcm-output")
    socket.incoming.put(json.dumps({"type": "AgentAudioDone"}))
    events = session.send_audio(b"pcm-input")

    assert any(item[0] == b"pcm-input" and item[1] == 2 for item in socket.sent)
    events.extend(wait_events(session))
    assert not any(
        event.get("content") == "secret transcript"
        or event.get("text") == "secret transcript"
        for event in events
        if isinstance(event, dict)
    )
    audio = next(event for event in events if event["type"] == "audio_chunk")
    assert audio["data"] == b"pcm-output"
    assert audio["audio_format"]["sample_rate"] == 24000
    assert any(event["type"] == "audio_done" for event in events)
    assert any(
        event["type"] == "speaking"
        and event["role"] == "user"
        and event["speaking"] is True
        for event in events
    )
    session.stop()


def test_unsupported_persona_rejected():
    with pytest.raises(ValueError):
        DeepgramVoiceAgentSession(profile("deepgram_kit").__class__(
            "icnale_chn_004_student", "voice", "label", {}, {}, {}
        ), api_key="test-key")


def test_audio_waits_for_settings_applied():
    socket = FakeProviderSocket(auto_settings_applied=False)
    session = DeepgramVoiceAgentSession(
        profile(),
        DeepgramAgentConfig("test-key", request_timeout_seconds=1),
        websocket_factory=lambda url, header=None: socket,
    )
    start_error: list[BaseException] = []

    def start_session():
        try:
            session.start()
        except BaseException as exc:  # pragma: no cover - failure detail below
            start_error.append(exc)

    starter = threading.Thread(target=start_session)
    starter.start()
    assert socket.settings_sent.wait(1)
    with pytest.raises(DeepgramAgentError):
        session.send_audio(b"before-settings-applied")
    assert not any(item[1] == 2 for item in socket.sent)
    socket.emit_settings_applied()
    starter.join(timeout=1)
    assert not start_error
    session.stop()


def test_stop_closes_without_close_command_and_keeps_timing():
    socket = FakeProviderSocket()
    session = DeepgramVoiceAgentSession(
        profile(),
        api_key="test-key",
        websocket_factory=lambda url, header=None: socket,
    )
    session.start()
    events = session.stop()
    assert socket.closed is True
    close_messages = [json.loads(item[0]) for item in socket.sent if isinstance(item[0], str)]
    assert not any(message.get("type") == "CloseStream" for message in close_messages)
    assert any(event["type"] == "timing" for event in events)
    assert not any(event["type"] == "error" for event in events)
