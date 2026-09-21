"""Dependency-light WebSocket adapter for the Singapore Model 1 MVP.

The adapter owns only protocol validation and safe event shaping.  Deepgram
classroom personas use the integrated Voice Agent transport; legacy personas
may use :mod:`services.model1.realtime` when the full cascade is configured.
An unconfigured app keeps the explicit unsupported-audio boundary.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import inspect
import json
import mimetypes
import os
from collections.abc import AsyncIterable, Iterable, Mapping
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable

from services.model1 import realtime as model1_realtime
from services.model1.config import Model1Config, read_env_file
from services.model1.deepgram_agent import (
    DeepgramAgentConfig,
    DeepgramVoiceAgentSession,
    deepgram_agent_enabled,
)
from services.model1.personas import PersonaProfile, PersonaRegistry


MAX_AUDIO_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 4000


class UnsupportedAudioIngestion(RuntimeError):
    """Raised by the default session because live STT is not available yet."""


class _MVPUnsupportedSession:
    """Session placeholder that makes the unsupported MVP boundary explicit."""

    supports_audio_input = False

    def __init__(self, profile: PersonaProfile, config: Model1Config | None = None) -> None:
        self.profile = profile
        self.config = config

    async def send_audio(self, _audio: bytes) -> None:
        raise UnsupportedAudioIngestion()

    async def stop(self) -> None:
        return None


def _default_session_factory(
    profile: PersonaProfile,
    task_context: Any = None,
    config: Model1Config | None = None,
) -> Any:
    persona_id = getattr(profile, "persona_id", None)
    # Deepgram classroom personas are always routed through the integrated
    # listen/think/speak Agent when explicitly enabled.  They must never enter
    # the legacy Qwen/CosyVoice cascade.
    if persona_id in {
        "deepgram_kit",
        "deepgram_kai",
        "deepgram_hannah",
        "deepgram_naveen",
    }:
        if isinstance(config, DeepgramAgentConfig) or deepgram_agent_enabled():
            return DeepgramVoiceAgentSession(
                profile,
                config=config,
                task_context=task_context,
            )
        # Never route a Deepgram classroom persona through the legacy
        # Qwen/CosyVoice cascade when the integrated path is disabled.
        return _MVPUnsupportedSession(profile, config)
    if config is not None:
        # A minimal Agent config intentionally has no Qwen/CosyVoice fields.
        # Non-Deepgram personas remain on the established cascade only when
        # the full Model1Config is present.
        if isinstance(config, Model1Config) or all(
            hasattr(config, field)
            for field in (
                "deepgram_api_key",
                "qwen_base_url",
                "qwen_model",
                "cosyvoice_ws_url",
                "cosyvoice_model",
            )
        ):
            return model1_realtime.LiveModel1Session(profile, config, task_context=task_context)
        return _MVPUnsupportedSession(profile, config)
    # ``task_context`` is intentionally not retained: it must never be echoed
    # by this adapter and the default session does not have STT to consume it.
    del task_context
    return _MVPUnsupportedSession(profile, config)


def _is_awaitable(value: Any) -> bool:
    return inspect.isawaitable(value)


async def _maybe_await(value: Any) -> Any:
    return await value if _is_awaitable(value) else value


def _json_message(raw: Any) -> Mapping[str, Any] | None:
    if isinstance(raw, Mapping):
        return raw
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(raw, str):
        return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, Mapping) else None


def _valid_base64(value: Any) -> bytes | None:
    if not isinstance(value, str) or not value or len(value) > MAX_AUDIO_BYTES * 2:
        return None
    try:
        decoded = base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError, binascii.Error):
        return None
    if not decoded or len(decoded) > MAX_AUDIO_BYTES:
        return None
    return decoded


def _encoded_audio(value: Any) -> str | None:
    if isinstance(value, (bytearray, memoryview)):
        value = bytes(value)
    if isinstance(value, bytes):
        if not value or len(value) > MAX_AUDIO_BYTES:
            return None
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, str):
        decoded = _valid_base64(value)
        return base64.b64encode(decoded).decode("ascii") if decoded is not None else None
    return None


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def _timing_payload(value: Any) -> dict[str, Any]:
    """Keep only the timing fields exposed by the realtime service type."""

    if isinstance(value, model1_realtime.StreamingTiming):
        source: Mapping[str, Any] = asdict(value)
    elif is_dataclass(value):
        source = asdict(value)
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
    payload: dict[str, Any] = {"type": "timing"}
    for key in (
        "started_ts",
        "first_audio_ts",
        "ended_ts",
        "time_to_first_audio_seconds",
        "total_duration_seconds",
    ):
        item = source.get(key)
        if key.endswith("_ts"):
            if isinstance(item, str) and len(item) <= 80:
                payload[key] = item
        else:
            number = _number(item)
            if number is not None:
                payload[key] = number
    return payload


class Model1Protocol:
    """A framework-neutral protocol handler suitable for a WebSocket server."""

    def __init__(
        self,
        *,
        session_factory: Callable[..., Any] | None = None,
        registry: Any | None = None,
        config: Model1Config | None = None,
    ) -> None:
        self.session_factory = session_factory or _default_session_factory
        self.registry = registry if registry is not None else PersonaRegistry()
        self.config = config

    async def __call__(self, websocket: Any, path: str | None = None) -> None:
        await self.handle_client(websocket, path)

    async def _send(self, websocket: Any, event: Mapping[str, Any]) -> None:
        send = getattr(websocket, "send", None)
        if not callable(send):
            return
        payload = json.dumps(dict(event), ensure_ascii=False, separators=(",", ":"))
        await _maybe_await(send(payload))

    async def _error(self, websocket: Any, message: str) -> None:
        # Messages are selected from fixed, non-sensitive strings at callsites.
        await self._send(websocket, {"type": "error", "message": message})

    def _resolve_persona(self, persona_id: str) -> Any:
        resolver = getattr(self.registry, "resolve", None)
        if not callable(resolver):
            raise ValueError("persona registry is unavailable")
        return resolver(persona_id)

    def _factory_call(self, profile: Any, task_context: Any) -> Any:
        factory = self.session_factory
        profile_candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = [
            ((profile, task_context, self.config), {}),
            ((profile, task_context), {}),
            ((profile,), {}),
            ((), {"profile": profile, "task_context": task_context, "config": self.config}),
            ((), {"persona": profile, "task_context": task_context}),
        ]
        id_candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = [
            ((getattr(profile, "persona_id", None), task_context, self.config), {}),
            ((getattr(profile, "persona_id", None), task_context), {}),
            ((), {"persona_id": getattr(profile, "persona_id", None), "task_context": task_context}),
            ((getattr(profile, "persona_id", None), task_context), {}),
        ]
        try:
            signature = inspect.signature(factory)
        except (TypeError, ValueError):
            return factory(profile, task_context)

        # Prefer a persona id when a factory names its first argument that way;
        # otherwise the documented profile object is the least lossy contract.
        first_name = next(iter(signature.parameters), "")
        candidates = id_candidates + profile_candidates if first_name in {"persona_id", "id"} else profile_candidates + id_candidates
        candidates.append(((), {}))
        for args, kwargs in candidates:
            try:
                signature.bind(*args, **kwargs)
            except TypeError:
                continue
            return factory(*args, **kwargs)
        raise TypeError("session_factory has an unsupported signature")

    async def _new_session(self, profile: Any, task_context: Any) -> Any:
        session = self._factory_call(profile, task_context)
        return await _maybe_await(session)

    async def _call_session(self, session: Any, names: tuple[str, ...], *args: Any) -> Any:
        for name in names:
            method = getattr(session, name, None)
            if callable(method):
                # Provider adapters are synchronous by design.  Keep their
                # blocking websocket calls off the event loop while retaining
                # support for the legacy async test/session implementations.
                if inspect.iscoroutinefunction(method):
                    return await method(*args)
                result = await asyncio.to_thread(method, *args)
                return await _maybe_await(result)
        return None

    @staticmethod
    def _audio_format(value: Any) -> dict[str, Any] | None:
        if not isinstance(value, Mapping):
            return None
        encoding = value.get("encoding")
        sample_rate = value.get("sample_rate")
        container = value.get("container")
        if encoding != "linear16" or sample_rate != 24000 or container not in {None, "none"}:
            return None
        return {
            "encoding": "linear16",
            "sample_rate": 24000,
            "container": "none",
        }

    async def _emit_result(self, websocket: Any, result: Any) -> None:
        """Convert only known fake/session outputs into safe protocol events."""

        if result is None:
            return
        if isinstance(result, (bytes, bytearray, memoryview)):
            encoded = _encoded_audio(result)
            if encoded is not None:
                await self._send(websocket, {"type": "audio_chunk", "data": encoded})
            return
        if isinstance(result, str):
            if result and len(result) <= MAX_TEXT_CHARS:
                await self._send(websocket, {"type": "text_delta", "text": result})
            return
        if isinstance(result, Mapping):
            events = result.get("events")
            if isinstance(events, (list, tuple)):
                for event in events:
                    await self._emit_result(websocket, event)
                return
            event_type = result.get("type")
            if event_type == "text_delta":
                text = result.get("text")
                if isinstance(text, str) and text and len(text) <= MAX_TEXT_CHARS:
                    await self._send(websocket, {"type": "text_delta", "text": text})
            elif event_type == "transcript":
                role = result.get("role")
                text = result.get("text")
                if (
                    role in {"user", "assistant"}
                    and isinstance(text, str)
                    and text
                    and len(text) <= MAX_TEXT_CHARS
                ):
                    # The browser persists this hidden event for the
                    # configured study store; persona.js never renders it.
                    await self._send(
                        websocket,
                        {"type": "transcript", "role": role, "text": text},
                    )
            elif event_type == "audio_chunk":
                encoded = _encoded_audio(result.get("data"))
                if encoded is not None:
                    event: dict[str, Any] = {"type": "audio_chunk", "data": encoded}
                    audio_format = self._audio_format(result.get("audio_format"))
                    if audio_format is not None:
                        event["audio_format"] = audio_format
                    await self._send(websocket, event)
            elif event_type == "ready":
                # The adapter emits exactly one lifecycle-ready event below;
                # a provider Welcome event must not duplicate it.
                return
            elif event_type == "settings_applied":
                event = {"type": event_type}
                audio_format = self._audio_format(result.get("audio_format"))
                if audio_format is not None:
                    event["audio_format"] = audio_format
                await self._send(websocket, event)
            elif event_type == "speaking":
                speaking = result.get("speaking")
                if isinstance(speaking, bool):
                    event = {"type": "speaking", "speaking": speaking}
                    role = result.get("role")
                    if role in {"user", "agent"}:
                        event["role"] = role
                    await self._send(websocket, event)
            elif event_type == "audio_done":
                await self._send(websocket, {"type": "audio_done"})
            elif event_type == "status":
                status = result.get("status")
                if isinstance(status, str) and status and len(status) <= 80:
                    await self._send(websocket, {"type": "status", "status": status})
            elif event_type == "timing":
                await self._send(websocket, _timing_payload(result))
            elif event_type == "error":
                await self._error(websocket, "Session error")
            # Session ready/stopped values are intentionally ignored or
            # replaced by this adapter's own fixed lifecycle events.
            return
        if isinstance(result, AsyncIterable):
            async for event in result:
                await self._emit_result(websocket, event)
            return
        if isinstance(result, Iterable):
            for event in result:
                await self._emit_result(websocket, event)

    async def _start(self, websocket: Any, message: Mapping[str, Any]) -> tuple[Any | None, bool]:
        persona_id = message.get("persona_id")
        if not isinstance(persona_id, str) or not persona_id.strip() or len(persona_id) > 200:
            await self._error(websocket, "Invalid persona")
            return None, False
        task_context = message.get("task_context")
        if task_context is not None and not isinstance(task_context, (str, Mapping, list, tuple)):
            await self._error(websocket, "Invalid task context")
            return None, False
        try:
            profile = self._resolve_persona(persona_id)
            session = await self._new_session(profile, task_context)
            result = await self._call_session(session, ("start", "open"))
            await self._emit_result(websocket, result)
        except Exception:
            await self._error(websocket, "Unable to start session")
            return None, False
        supports_audio = getattr(session, "supports_audio_input", None)
        if supports_audio is None:
            supports_audio = any(callable(getattr(session, name, None)) for name in ("send_audio", "push_audio"))
        ready: dict[str, Any] = {
            "type": "ready",
            "persona_id": persona_id,
            "audio_input_supported": bool(supports_audio),
        }
        audio_format = self._audio_format(getattr(session, "audio_format", None))
        if audio_format is not None:
            ready["audio_format"] = audio_format
        await self._send(websocket, ready)
        return session, True

    async def _audio(self, websocket: Any, session: Any, message: Mapping[str, Any]) -> None:
        if session is None:
            await self._error(websocket, "Start a session before audio")
            return
        audio = _valid_base64(message.get("data"))
        if audio is None:
            await self._error(websocket, "Invalid audio data")
            return
        supports_audio = getattr(session, "supports_audio_input", None)
        if supports_audio is False or not any(
            callable(getattr(session, name, None)) for name in ("send_audio", "push_audio")
        ):
            await self._error(websocket, "Live audio ingestion is not available in this MVP")
            return
        try:
            result = await self._call_session(session, ("send_audio", "push_audio"), audio)
            await self._emit_result(websocket, result)
        except UnsupportedAudioIngestion:
            await self._error(websocket, "Live audio ingestion is not available in this MVP")
        except Exception:
            await self._error(websocket, "Audio processing failed")

    async def _stop(self, websocket: Any, session: Any) -> None:
        if session is None:
            await self._error(websocket, "Start a session before stop")
            return
        try:
            stream_stop = getattr(session, "stream_stop", None)
            if callable(stream_stop):
                result = await _maybe_await(stream_stop())
            else:
                result = await self._call_session(session, ("stop", "close", "cancel", "complete"))
            await self._emit_result(websocket, result)
            timing = getattr(session, "timing", None)
            if timing is not None:
                await self._send(websocket, _timing_payload(timing))
        except Exception:
            await self._error(websocket, "Unable to stop session")
        await self._send(websocket, {"type": "stopped"})

    async def handle_client(self, websocket: Any, path: str | None = None) -> None:
        """Consume JSON protocol messages until ``stop`` or disconnect."""

        del path
        session: Any | None = None
        started = False
        stopped = False

        async def process(raw: Any) -> bool:
            nonlocal session, started, stopped
            message = _json_message(raw)
            if message is None:
                await self._error(websocket, "Invalid JSON message")
                return True
            message_type = message.get("type")
            if not isinstance(message_type, str):
                await self._error(websocket, "Invalid message type")
                return True
            if message_type == "start":
                if started:
                    await self._error(websocket, "Session already started")
                    return True
                session, started = await self._start(websocket, message)
                return True
            if message_type == "audio":
                await self._audio(websocket, session if started else None, message)
                return True
            if message_type == "stop":
                await self._stop(websocket, session if started else None)
                stopped = True
                return False
            await self._error(websocket, "Unsupported message type")
            return True

        try:
            if hasattr(websocket, "__aiter__"):
                async for raw in websocket:
                    if not await process(raw):
                        break
            else:
                recv = getattr(websocket, "recv", None)
                if not callable(recv):
                    recv = getattr(websocket, "receive_text", None)
                if not callable(recv):
                    recv = getattr(websocket, "receive", None)
                if not callable(recv):
                    return
                while True:
                    try:
                        raw = await _maybe_await(recv())
                    except Exception:
                        break
                    if not await process(raw):
                        break
        except Exception:
            # Disconnects and framework errors are not safe to expose.  The
            # adapter intentionally does not send exception bodies.
            pass
        finally:
            if session is not None and not stopped:
                try:
                    await self._call_session(session, ("stop", "close", "cancel"))
                except Exception:
                    pass


def build_protocol(
    session_factory: Callable[..., Any] | None = None,
    registry: Any | None = None,
    *,
    persona_registry: Any | None = None,
    config: Model1Config | None = None,
) -> Model1Protocol:
    """Build a testable protocol adapter without importing a WebSocket package."""

    if registry is not None and persona_registry is not None and registry is not persona_registry:
        raise TypeError("pass either registry or persona_registry")
    return Model1Protocol(
        session_factory=session_factory,
        registry=persona_registry if persona_registry is not None else registry,
        config=config,
    )


def create_app(
    session_factory: Callable[..., Any] | None = None,
    registry: Any | None = None,
    *,
    persona_registry: Any | None = None,
    config: Model1Config | None = None,
) -> Model1Protocol:
    """Create the framework-neutral application used by ``serve``."""

    return build_protocol(
        session_factory,
        registry,
        persona_registry=persona_registry,
        config=config,
    )


async def handle_client(
    websocket: Any,
    path: str | None = None,
    *,
    session_factory: Callable[..., Any] | None = None,
    registry: Any | None = None,
    persona_registry: Any | None = None,
    config: Model1Config | None = None,
) -> None:
    """Convenience entry point for WebSocket servers and fake clients."""

    app = create_app(
        session_factory=session_factory,
        registry=registry,
        persona_registry=persona_registry,
        config=config,
    )
    await app.handle_client(websocket, path)


async def serve(
    app: Model1Protocol | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    env_file: str = ".env.local",
    persona_root: str = "voices/personas",
) -> Any:
    """Start the WebSocket server and serve the browser MVP on the same port."""

    try:
        import websockets  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("The optional websockets package is required to serve the MVP") from exc
    if app is None:
        try:
            env_values = read_env_file(env_file)
            env_values.update(dict(os.environ))
            if deepgram_agent_enabled(env_values):
                config = DeepgramAgentConfig.from_env(env_values)
            else:
                config = Model1Config.from_env(env_values)
            registry = PersonaRegistry(persona_root)
        except Exception as exc:
            raise RuntimeError("Model 1 environment or persona registry is unavailable") from exc
        adapter = create_app(config=config, persona_registry=registry)
    else:
        adapter = app

    static_root = Path(__file__).with_name("static").resolve()

    async def process_request(connection: Any, request: Any) -> Any:
        """Return the static browser client for ordinary HTTP GET requests."""

        headers = getattr(request, "headers", {})
        if str(headers.get("Upgrade", "")).lower() == "websocket":
            return None
        request_path = str(getattr(request, "path", "/")).split("?", 1)[0]
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        candidate = (static_root / relative).resolve()
        # Directory URLs (including nested persona routes) resolve to their
        # local index document while retaining the same traversal boundary.
        if candidate.is_dir():
            candidate = (candidate / "index.html").resolve()
        if static_root not in candidate.parents or not candidate.is_file():
            from websockets.http11 import Headers, Response

            return Response(404, "Not Found", Headers([("Content-Type", "text/plain")]), b"Not found")
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        from websockets.http11 import Headers, Response

        return Response(
            200,
            "OK",
            Headers(
                [
                    ("Content-Type", content_type),
                    ("Content-Length", str(len(body))),
                    ("Cache-Control", "no-store"),
                ]
            ),
            body,
        )

    return await websockets.serve(
        adapter.handle_client,
        host,
        port,
        process_request=process_request,
    )


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    app: Model1Protocol | None = None,
    env_file: str = ".env.local",
    persona_root: str = "voices/personas",
) -> None:
    """Run the browser/WebSocket MVP until interrupted."""

    async def runner() -> None:
        server = await serve(
            app,
            host,
            port,
            env_file=env_file,
            persona_root=persona_root,
        )
        await server.wait_closed()

    asyncio.run(runner())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Model 1 browser/WebSocket MVP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--env-file", default=".env.local")
    parser.add_argument("--persona-root", default="voices/personas")
    args = parser.parse_args()
    run_server(
        host=args.host,
        port=args.port,
        env_file=args.env_file,
        persona_root=args.persona_root,
    )


__all__ = [
    "Model1Protocol",
    "UnsupportedAudioIngestion",
    "build_protocol",
    "create_app",
    "handle_client",
    "run_server",
    "serve",
]
