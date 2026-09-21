"""Shared three-layer prompt architecture for Model 1 engines.

Layer 1 and Layer 2 are immutable prompt assets.  Layer 3 is assembled from a
persona profile after filtering it to fields that affect conversation
behavior.  Provider adapters should call :func:`build_layered_system_prompt`
instead of carrying their own policy copy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


_ASSET_ROOT = Path(__file__).resolve().parents[2] / "prompts" / "voice_agents_system-prompt"


def _read_asset(filename: str) -> str:
    try:
        return (_ASSET_ROOT / filename).read_text(encoding="utf-8").strip()
    except OSError as exc:
        # Do not include a machine path (which may contain private workspace
        # details) in an import-time error.
        raise RuntimeError(f"prompt asset is unavailable: {filename}") from exc


# Keep the text in the human-readable assets, with one source for every
# provider.  In particular, do not duplicate these strings in an adapter.
LAYER1_SPOKEN_AGENT_BASE = _read_asset("layer1_spoken_agent_base.md")
LAYER2_ELF_POLICY = _read_asset("layer2_elf_policy.md")


_SOURCE_FIELDS = ("l1", "english_level", "proficiency", "level", "role")
_FICTIONALIZED_FIELDS = (
    "preferred_name",
    "preferred_name_is_fictional",
    "university",
    "hometown_city",
)
_CONTEXT_FIELDS = (
    "current_context",
    "current_country",
    "academic_status",
    "major",
    "field",
    "study_context",
    "current_role",
    "current_location",
)
_BLOCKED_FIELD_PARTS = (
    "api_key",
    "apikey",
    "password",
    "secret",
    "token",
    "credential",
    "audio",
    "path",
    "rights",
    "approval",
    "consent",
    "evidence",
    "permitted_use",
)


def _blocked_field(name: str) -> bool:
    lowered = name.casefold()
    return any(part in lowered for part in _BLOCKED_FIELD_PARTS)


def _safe_value(value: Any) -> Any:
    """Copy JSON-shaped data without invoking arbitrary object ``repr``."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        copied: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError("persona profile contains non-serializable fields")
            if _blocked_field(key):
                continue
            copied[key] = _safe_value(nested)
        return copied
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    raise TypeError("persona profile contains non-serializable fields")


def _persona_mapping(persona: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if persona is None:
        return {}
    if isinstance(persona, Mapping):
        return persona
    # PersonaProfile exposes prompt_context.  Supporting it here keeps all
    # callers on the same builder while the public type remains Mapping.
    context = getattr(persona, "prompt_context", None)
    if isinstance(context, Mapping):
        return context
    raise TypeError("persona must be a mapping or None")


def _profile_payload(persona: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = _persona_mapping(persona)
    source = raw.get("source_grounded")
    source = source if isinstance(source, Mapping) else {}

    source_payload: dict[str, Any] = {}
    for field in _SOURCE_FIELDS:
        if field in source:
            source_payload[field] = _safe_value(source[field])
    if "english_level" in source and "proficiency" not in source and "level" not in source:
        # Keep the source field name while exposing the behavior-oriented
        # concept used by the layered policy.
        source_payload["proficiency"] = _safe_value(source["english_level"])

    # ``current_context`` is a normalized container for the profile's
    # present-study/work context.  Preserve explicit nulls rather than making
    # an absent fact sound like a claim.
    current_context: dict[str, Any] = {}
    nested_context = source.get("current_context")
    if isinstance(nested_context, Mapping):
        current_context.update(_safe_value(nested_context))
    for field in _CONTEXT_FIELDS[1:]:
        if field in source:
            current_context[field] = _safe_value(source[field])
    source_payload["current_context"] = current_context

    fictionalized = raw.get("fictionalized")
    if not isinstance(fictionalized, Mapping):
        # Older callers sometimes passed the small fictionalized profile
        # fields alongside ``display_label`` rather than under a mapping.
        fictionalized = {
            field: raw[field] for field in _FICTIONALIZED_FIELDS if field in raw
        }
    behavior = raw.get("behavior")
    fictionalized_payload = (
        _safe_value(fictionalized) if isinstance(fictionalized, Mapping) else {}
    )
    behavior_payload = _safe_value(behavior) if isinstance(behavior, Mapping) else {}

    return {
        "persona_id": _safe_value(raw.get("persona_id")),
        "display_label": _safe_value(raw.get("display_label")),
        "source_grounded": source_payload,
        "fictionalized": fictionalized_payload,
        "behavior": behavior_payload,
    }


def _serialize(value: Any, *, error: str) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    except (TypeError, ValueError, OverflowError) as exc:
        # Never interpolate the offending value: it could contain a provider
        # secret or private metadata.
        raise TypeError(error) from exc


def build_persona_prompt(persona: Mapping[str, Any] | None) -> str:
    """Build the customizable persona layer from a filtered profile.

    The profile data is deliberately allow-listed.  Rights/approval evidence,
    source file paths, voice identifiers, and provider credentials are not
    conversational behavior and never enter this prompt.
    """

    payload = _profile_payload(persona)
    serialized = _serialize(
        payload,
        error="persona profile must contain JSON-serializable behavior fields",
    )
    return (
        "# Layer 3 — Persona-Specific Profile\n\n"
        "Use this profile as the only customizable layer. It includes source-grounded "
        "L1, proficiency or level, role, current context, behavior, and explicitly "
        "fictionalized details. Treat source-grounded "
        "facts as evidence-based context and fictionalized values as explicitly "
        "fictional; never infer a nationality stereotype or invent a hometown "
        "or private identity.\n\n"
        "For ordinary questions about the persona, answer only from the profile. "
        "When a personal fact is absent, null, or marked unspecified, say: "
        "\"I haven't specified that detail.\" Do not default to saying you are "
        "an AI agent. If the learner directly asks whether you are real, a "
        "person, synthetic, or AI, disclose honestly: \"I am an AI conversation "
        "partner using a fictionalized, source-grounded persona; I am not the "
        "real participant.\"\n\n"
        "Persona Profile (serialized; filtered JSON):\n"
        f"{serialized}"
    )


def build_layered_system_prompt(
    persona: Mapping[str, Any] | None,
    task_context: Any = None,
    *,
    max_words: int = 48,
) -> str:
    """Compose the reusable Layer 1 → Layer 2 → Layer 3 system prompt."""

    if isinstance(max_words, bool) or not isinstance(max_words, int) or max_words <= 0:
        raise ValueError("max_words must be a positive integer")

    layers = [
        LAYER1_SPOKEN_AGENT_BASE,
        LAYER2_ELF_POLICY,
        build_persona_prompt(persona),
        (
            "TURN LENGTH: Follow the one-or-two-sentence spoken style and keep "
            f"each reply to no more than {max_words} words unless the learner "
            "explicitly requests a longer explanation."
        ),
    ]
    if task_context is not None:
        layers.append(
            "Task context (serialized):\n"
            + _serialize(
                task_context,
                error="task_context must be JSON serializable",
            )
        )
    return "\n\n".join(layers)


__all__ = [
    "LAYER1_SPOKEN_AGENT_BASE",
    "LAYER2_ELF_POLICY",
    "build_persona_prompt",
    "build_layered_system_prompt",
]
