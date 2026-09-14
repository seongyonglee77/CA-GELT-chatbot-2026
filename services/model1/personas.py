"""Dependency-free registry for source-backed conversation personas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class PersonaProfile:
    persona_id: str
    voice_id: str
    display_label: str
    source_grounded: Mapping[str, Any]
    fictionalized: Mapping[str, Any]
    behavior: Mapping[str, Any]

    def __repr__(self) -> str:
        return (
            f"PersonaProfile(persona_id={self.persona_id!r}, "
            f"voice_id={self.voice_id!r}, display_label={self.display_label!r})"
        )

    @property
    def prompt_context(self) -> Mapping[str, Any]:
        return {
            "persona_id": self.persona_id,
            "display_label": self.display_label,
            "source_grounded": self.source_grounded,
            "fictionalized": self.fictionalized,
            "behavior": self.behavior,
        }


class PersonaRegistry:
    """Load persona profiles from a registry manifest and JSON profile files."""

    def __init__(self, root: str | Path = "voices/personas") -> None:
        self.root = Path(root)
        manifest_path = self.root if self.root.suffix.lower() == ".json" else self.root / "registry.json"
        self.root = manifest_path.parent
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = manifest["personas"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError(f"invalid persona registry: {manifest_path}") from exc
        if not isinstance(entries, Mapping):
            raise ValueError("persona registry personas must be an object")
        self._entries = dict(entries)

    def resolve(self, persona_id: str) -> PersonaProfile:
        if not isinstance(persona_id, str) or not persona_id.strip():
            raise ValueError("persona_id must be a non-empty string")
        filename = self._entries.get(persona_id)
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ValueError(f"Unknown persona_id: {persona_id}")
        path = self.root / filename
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid persona profile: {persona_id}") from exc
        required = ("persona_id", "voice_id", "display_label", "source_grounded", "fictionalized", "behavior")
        if data.get("persona_id") != persona_id or any(key not in data for key in required):
            raise ValueError(f"invalid persona profile: {persona_id}")
        if not all(isinstance(data[key], Mapping) for key in required[3:]):
            raise ValueError(f"invalid persona profile mappings: {persona_id}")
        return PersonaProfile(
            persona_id=persona_id,
            voice_id=data["voice_id"],
            display_label=data["display_label"],
            source_grounded=data["source_grounded"],
            fictionalized=data["fictionalized"],
            behavior=data["behavior"],
        )


__all__ = ["PersonaProfile", "PersonaRegistry"]
