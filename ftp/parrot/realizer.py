"""FTP 2.0 Language Realizer — renders Director instructions (Pass 5)."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping, MutableMapping, Protocol

from ftp.parrot.continuity import dialogue_turns_from_coordinator
from ftp.session.coordinator import SessionCoordinator

MAX_REALIZER_TEXT_CHARS = 1200

ALLOWED_REQUEST_KEYS = frozenset({
    "turn_text",
    "turn_index",
    "navarasa_result",
    "recent_turn_texts",
    "behaviour",
    "behaviour_family",
    "behaviour_intensity",
    "directive",
    "directive_basis",
})

FORBIDDEN_REQUEST_KEYS = frozenset({
    "engagement_state",
    "engagement_score",
    "behavioural_eligibility",
    "fracture_eligibility",
    "recovery_eligibility",
    "evidence",
    "evidence_bundle",
    "candidate_inference",
    "reading_profile",
    "hidden_provenance",
    "selection_mode",
    "silent_reader",
})

_FORBIDDEN_OUTPUT_PATTERNS = [
    re.compile(r"\bengagement_(state|score|evidence)\b", re.I),
    re.compile(r"\bevidence bundle\b", re.I),
    re.compile(r"\binference\b", re.I),
    re.compile(r"\breading profile\b", re.I),
    re.compile(r"\bhidden provenance\b", re.I),
    re.compile(r"\bbarnum\b", re.I),
    re.compile(r"\bsilent reader\b", re.I),
    re.compile(r"\bbehaviour director\b", re.I),
    re.compile(r"\bdirector state\b", re.I),
    re.compile(r"\bi feel\b", re.I),
    re.compile(r"\bi know you\b", re.I),
    re.compile(r"\bdon't leave\b", re.I),
    re.compile(r"\bdo not leave\b", re.I),
    re.compile(r"\byou need me\b", re.I),
    re.compile(r"\bi missed you\b", re.I),
    re.compile(r"\battached to me\b", re.I),
    re.compile(r"\byour personality\b", re.I),
    re.compile(r"\bi know what you'?re feeling\b", re.I),
    re.compile(r"\bi am conscious\b", re.I),
    re.compile(r"\bi have feelings\b", re.I),
    re.compile(r"\bdebug\b", re.I),
    re.compile(r"\btelemetry\b", re.I),
]

_DIRECTIVE_VALUES = frozenset({
    "familiarity",
    "reciprocity",
    "curiosity",
    "expectation",
    "repair",
})


class ParrotLanguageAdapter(Protocol):
    """Optional model backend. Returns JSON ``{"text": "..."}`` only."""

    def complete(self, request: Mapping[str, Any]) -> str:
        """Return raw JSON with a single ``text`` field."""


class LanguageRealizer:
    """Deterministic renderer with optional one-shot model adapter."""

    _adapter: ParrotLanguageAdapter | None = None

    @classmethod
    def configure_adapter(cls, adapter: ParrotLanguageAdapter | None) -> None:
        cls._adapter = adapter

    @classmethod
    def realize(
        cls,
        request: Mapping[str, Any],
        *,
        session: MutableMapping[str, Any],
        roast: str,
        analysis: Mapping[str, Any] | None = None,
    ) -> str:
        _validate_request(request)
        instruction = _instruction_view(request)
        base = cls._deterministic_base(
            instruction,
            session=session,
            roast=roast,
            turn_text=str(request["turn_text"]),
            analysis=analysis or {},
        )
        candidate = _apply_directive_overlay(
            base,
            directive=instruction.get("directive"),
            directive_basis=list(instruction.get("directive_basis") or []),
            turn_text=str(request["turn_text"]),
            recent_turn_texts=list(request.get("recent_turn_texts") or []),
        )
        if not validate_realizer_output(candidate, instruction):
            candidate = base
        if validate_realizer_output(candidate, instruction):
            deterministic = candidate
        else:
            deterministic = base if validate_realizer_output(base, instruction) else base[:MAX_REALIZER_TEXT_CHARS]

        if cls._adapter is None:
            return deterministic

        try:
            raw = cls._adapter.complete(request)
            payload = json.loads(raw)
            if set(payload.keys()) != {"text"}:
                return deterministic
            model_text = str(payload.get("text") or "")
            if validate_realizer_output(model_text, instruction):
                return model_text
        except Exception:
            pass
        return deterministic

    @staticmethod
    def _deterministic_base(
        instruction: Mapping[str, Any],
        *,
        session: MutableMapping[str, Any],
        roast: str,
        turn_text: str,
        analysis: Mapping[str, Any],
    ) -> str:
        from interface_server import apply_behaviour

        return apply_behaviour(
            instruction["behaviour"],
            session,
            roast,
            text=turn_text,
            analysis=analysis,
        )


def build_realizer_request(
    coordinator: SessionCoordinator,
    instruction: Mapping[str, Any],
    *,
    turn_text: str,
    turn_index: int,
    navarasa_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble the bounded realizer input for one live turn."""
    turns = dialogue_turns_from_coordinator(coordinator)
    recent_turn_texts = [turn.user_text for turn in turns[-3:]]
    nav = {
        "primary_rasa": navarasa_result.get("primary_rasa"),
        "rasa_scores": navarasa_result.get("rasa_scores") or {},
        "sentiment": navarasa_result.get("sentiment") or {},
    }
    return {
        "turn_text": turn_text,
        "turn_index": turn_index,
        "navarasa_result": nav,
        "recent_turn_texts": recent_turn_texts,
        "behaviour": instruction["behaviour"],
        "behaviour_family": instruction["behaviour_family"],
        "behaviour_intensity": instruction["behaviour_intensity"],
        "directive": instruction.get("directive"),
        "directive_basis": list(instruction.get("directive_basis") or []),
    }


def validate_realizer_output(
    text: str,
    instruction: Mapping[str, Any],
) -> bool:
    if not isinstance(text, str):
        return False
    cleaned = text.strip()
    if not cleaned:
        return False
    if len(cleaned) > MAX_REALIZER_TEXT_CHARS:
        return False
    for pattern in _FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.search(cleaned):
            return False
    lowered = cleaned.lower()
    for token in (
        "behaviour_family",
        "fracture_eligibility",
        "recovery_eligibility",
        "directive_basis",
        "selection_mode",
    ):
        if token in lowered:
            return False
    directive = instruction.get("directive")
    if directive is not None and directive not in _DIRECTIVE_VALUES:
        return False
    return True


def _instruction_view(request: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "behaviour": request["behaviour"],
        "behaviour_family": request["behaviour_family"],
        "behaviour_intensity": request["behaviour_intensity"],
        "directive": request.get("directive"),
        "directive_basis": list(request.get("directive_basis") or []),
    }


def _validate_request(request: Mapping[str, Any]) -> None:
    extra = set(request.keys()) - ALLOWED_REQUEST_KEYS
    if extra:
        raise ValueError(f"Unexpected realizer request keys: {sorted(extra)}")
    for key in request:
        if key in FORBIDDEN_REQUEST_KEYS:
            raise ValueError(f"Forbidden realizer request key {key!r}.")
    nested = request.get("navarasa_result")
    if isinstance(nested, Mapping):
        for key in nested:
            if key in FORBIDDEN_REQUEST_KEYS:
                raise ValueError(f"Forbidden navarasa key {key!r}.")


def _apply_directive_overlay(
    base: str,
    *,
    directive: str | None,
    directive_basis: list[dict[str, Any]],
    turn_text: str,
    recent_turn_texts: list[str],
) -> str:
    del turn_text, recent_turn_texts
    if not directive or directive not in _DIRECTIVE_VALUES or not directive_basis:
        return base
    excerpt = str(directive_basis[0].get("excerpt") or "").strip()
    if not excerpt:
        return base

    if directive == "familiarity":
        prefix = f"Earlier you mentioned {excerpt}."
    elif directive == "reciprocity":
        prefix = f'You called it "{excerpt}".'
    elif directive == "curiosity":
        prefix = f"You brought up {excerpt} —"
    elif directive == "expectation":
        prefix = "You left that question open —"
    elif directive == "repair":
        prefix = "Let's try that again."
    else:
        return base

    combined = f"{prefix} {base}".strip()
    if len(combined) > MAX_REALIZER_TEXT_CHARS:
        return base
    return combined
