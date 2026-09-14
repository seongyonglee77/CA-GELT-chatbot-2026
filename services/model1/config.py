"""Configuration and shared timing types for Model 1.

Configuration is read from the process environment.  Loading a ``.env`` file
is intentionally left to the application boundary so this library never
prints, persists, or implicitly discovers secret values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


REQUIRED_ENV_VARS = (
    "DEEPGRAM_API_KEY",
    "DASHSCOPE_API_KEY",
    "QWEN_BASE_URL",
    "QWEN_MODEL",
    "DASHSCOPE_API_KEY_COSYVOICE",
    "COSYVOICE_WS_URL",
    "COSYVOICE_MODEL",
)


class ConfigurationError(ValueError):
    """Raised when one or more required Model 1 settings are absent."""


def read_env_file(path: str | os.PathLike[str] = ".env.local") -> dict[str, str]:
    """Read simple ``KEY=VALUE`` settings without mutating ``os.environ``.

    The application boundary decides whether file values should be merged with
    process environment values.  This parser intentionally supports only the
    dotenv subset needed by this project: blank lines, comments, and optional
    matching single or double quotes around values.
    """

    env_path = Path(path)
    try:
        lines = env_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise ConfigurationError(f"Could not read environment file: {env_path}") from exc
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ConfigurationError(f"Invalid environment file line {line_number}: expected KEY=VALUE")
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_" for character in name):
            raise ConfigurationError(f"Invalid environment variable name on line {line_number}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[name] = value
    return values


def utc_now_iso() -> str:
    """Return an unambiguous UTC ISO-8601 timestamp."""

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class RequestTiming:
    """Provider request timing measured with a monotonic clock.

    The wall-clock timestamps are useful in project logs; ``duration_seconds``
    is monotonic and therefore the value to use for latency comparisons.
    """

    started_ts: str
    ended_ts: str
    duration_seconds: float


@dataclass(frozen=True)
class Model1Config:
    """Resolved Model 1 provider settings.

    Secret fields opt out of dataclass ``repr`` so accidentally inspecting a
    config or a containing object cannot reveal credentials.
    """

    deepgram_api_key: str = field(repr=False)
    dashscope_api_key: str = field(repr=False)
    qwen_base_url: str
    qwen_model: str
    dashscope_api_key_cosyvoice: str = field(repr=False)
    cosyvoice_ws_url: str
    cosyvoice_model: str
    qwen_enable_thinking: bool = False
    qwen_max_tokens: int = 96
    request_timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Model1Config":
        """Build config from ``env`` (or ``os.environ`` when omitted).

        Empty values are treated as missing.  A caller may pass a copied
        mapping in tests without changing process-global environment state.
        """

        source = os.environ if env is None else env
        missing = [name for name in REQUIRED_ENV_VARS if not source.get(name, "").strip()]
        if missing:
            names = ", ".join(missing)
            raise ConfigurationError(f"Missing required Model 1 environment variable(s): {names}")

        enable_thinking = source.get("QWEN_ENABLE_THINKING", "false").strip().lower()
        if enable_thinking not in {"true", "false"}:
            raise ConfigurationError("QWEN_ENABLE_THINKING must be true or false")
        try:
            max_tokens = int(source.get("QWEN_MAX_TOKENS", "96").strip())
        except ValueError as exc:
            raise ConfigurationError("QWEN_MAX_TOKENS must be an integer") from exc
        if max_tokens < 1:
            raise ConfigurationError("QWEN_MAX_TOKENS must be positive")

        return cls(
            deepgram_api_key=source["DEEPGRAM_API_KEY"].strip(),
            dashscope_api_key=source["DASHSCOPE_API_KEY"].strip(),
            qwen_base_url=source["QWEN_BASE_URL"].strip(),
            qwen_model=source["QWEN_MODEL"].strip(),
            dashscope_api_key_cosyvoice=source["DASHSCOPE_API_KEY_COSYVOICE"].strip(),
            cosyvoice_ws_url=source["COSYVOICE_WS_URL"].strip(),
            cosyvoice_model=source["COSYVOICE_MODEL"].strip(),
            qwen_enable_thinking=enable_thinking == "true",
            qwen_max_tokens=max_tokens,
        )

    @classmethod
    def from_env_file(
        cls,
        path: str | os.PathLike[str] = ".env.local",
        *,
        env: Mapping[str, str] | None = None,
    ) -> "Model1Config":
        """Load a local dotenv file, with process environment taking precedence."""

        file_values = read_env_file(path)
        merged = {**file_values, **(dict(os.environ) if env is None else dict(env))}
        return cls.from_env(merged)

    # Keep a named loader available to application code while making
    # ``from_env`` the canonical API.
    load = from_env

    def __str__(self) -> str:
        return self.__repr__()


def load_config(env: Mapping[str, str] | None = None) -> Model1Config:
    """Canonical function spelling for application startup code."""

    return Model1Config.from_env(env)


__all__ = [
    "ConfigurationError",
    "Model1Config",
    "REQUIRED_ENV_VARS",
    "RequestTiming",
    "load_config",
    "read_env_file",
    "utc_now_iso",
]
