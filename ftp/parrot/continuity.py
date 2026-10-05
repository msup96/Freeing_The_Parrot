"""Session-local conversational continuity index (Pass 2).

Deterministic OBSERVED signals from current-session ``PARROT_TURN_GENERATED``
dialogue only. No psychological inference, engagement, or Silent Reader data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from ftp.events.model import EventType, ProvenanceLevel
from ftp.session.coordinator import SessionCoordinator

MAX_EXCERPT_CHARS = 100
MAX_CONTINUITY_REFS = 5
MIN_TOPIC_TOKEN_LEN = 4
MIN_REPEATED_NGRAM_WORDS = 3
OPEN_THREAD_MAX_USER_WORDS = 4
OPEN_THREAD_MAX_USER_CHARS = 24

FRACTURE_BEHAVIOURS = frozenset({
    "memory_loss",
    "system_glitch",
    "absurd",
    "help_me",
    "mixed",
})

PROHIBITED_INDEX_LABELS = frozenset({
    "engaged",
    "attached",
    "lonely",
    "loneliness",
    "vulnerable",
    "vulnerability",
    "trusting",
    "dependency",
    "emotionally_invested",
    "engagement_state",
    "engagement_score",
    "participant_profile",
    "psychological",
    "personality",
})

_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "to", "of", "in",
    "on", "at", "for", "with", "is", "are", "was", "were", "be", "been", "it",
    "its", "this", "that", "these", "those", "i", "you", "he", "she", "we",
    "they", "my", "your", "his", "her", "our", "their", "me", "him", "them",
    "do", "does", "did", "have", "has", "had", "not", "no", "yes", "just",
    "very", "really", "about", "from", "into", "as", "by", "up", "out",
})

_INTERROGATIVE_START = re.compile(
    r"^\s*(what|why|how|when|where|who|whom|which|do|does|did|is|are|was|"
    r"were|can|could|would|should|will|shall)\b",
    re.IGNORECASE,
)

_SELF_REFERENCE = re.compile(r"\b(I|me|my|mine|myself)\b", re.IGNORECASE)
_TOKEN = re.compile(r"[a-zA-Z']{2,}")


@dataclass(frozen=True)
class DialogueTurn:
    turn_index: int
    user_text: str
    parrot_reply: str
    behaviour: str = ""


def dialogue_turns_from_coordinator(coordinator: SessionCoordinator) -> list[DialogueTurn]:
    """Load current-session Parrot turns from the event store."""
    turns: list[DialogueTurn] = []
    for event in coordinator.store.events_of_type(EventType.PARROT_TURN_GENERATED):
        if event.session_id != coordinator.session_id:
            continue
        payload = event.payload
        turns.append(
            DialogueTurn(
                turn_index=int(payload.get("turn_index") or 0),
                user_text=str(payload.get("user_text") or ""),
                parrot_reply=str(payload.get("parrot_reply") or ""),
                behaviour=str(payload.get("behaviour") or ""),
            )
        )
    return sorted(turns, key=lambda item: item.turn_index)


def continuity_index_from_coordinator(
    coordinator: SessionCoordinator,
    *,
    previous_behaviour: str | None = None,
) -> dict[str, Any]:
    """Build a continuity index for one coordinator's session."""
    turns = dialogue_turns_from_coordinator(coordinator)
    if previous_behaviour is None:
        previous_behaviour = coordinator.director_state.last_behaviour
    return build_session_continuity_index(
        turns,
        previous_behaviour=previous_behaviour,
    )


def build_session_continuity_index(
    turns: Sequence[DialogueTurn],
    *,
    previous_behaviour: str | None = None,
) -> dict[str, Any]:
    """Derive bounded continuity observations from dialogue turns."""
    refs: list[dict[str, Any]] = []

    repeated_phrase = _detect_repeated_phrase(turns, refs)
    prior_question = _detect_prior_question(turns, refs)
    open_thread = _detect_open_thread(turns, refs)
    topic_overlap = _detect_topic_overlap(turns, refs)
    explicit_self_reference = _detect_explicit_self_reference(turns, refs)

    previous_fracture = (
        previous_behaviour is not None
        and str(previous_behaviour).lower() in FRACTURE_BEHAVIOURS
    )

    bounded_refs = _bound_refs(refs)

    result: dict[str, Any] = {
        "observation_kind": "session_continuity_index",
        "provenance_level": ProvenanceLevel.OBSERVED.value,
        "turn_count": len(turns),
        "continuity_refs": bounded_refs,
        "repeated_phrase": repeated_phrase,
        "prior_question": prior_question,
        "open_thread": open_thread,
        "previous_fracture": previous_fracture,
        "topic_overlap": topic_overlap,
        "explicit_self_reference": explicit_self_reference,
    }
    _validate_index(result)
    return result


def _bound_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[int, str, str]] = set()
    out: list[dict[str, Any]] = []
    for ref in refs:
        key = (int(ref["turn_index"]), str(ref["role"]), str(ref["excerpt"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(ref)
        if len(out) >= MAX_CONTINUITY_REFS:
            break
    return out


def _make_ref(
    *,
    turn_index: int,
    role: str,
    source: str,
    start: int,
    length: int | None = None,
) -> dict[str, Any]:
    if role not in {"user", "parrot"}:
        raise ValueError(f"Invalid continuity role {role!r}.")
    end = start + (length if length is not None else MAX_EXCERPT_CHARS)
    excerpt = source[start:end]
    if len(excerpt) > MAX_EXCERPT_CHARS:
        excerpt = excerpt[:MAX_EXCERPT_CHARS]
    if excerpt and excerpt not in source:
        raise ValueError("Continuity excerpt must be a literal substring.")
    return {
        "turn_index": turn_index,
        "role": role,
        "excerpt": excerpt,
    }


def _literal_excerpt(source: str, needle: str, turn_index: int, role: str) -> dict[str, Any]:
    idx = source.lower().find(needle.lower())
    if idx < 0:
        raise ValueError("Needle must appear in source for a literal excerpt.")
    actual = source[idx : idx + len(needle)]
    if len(actual) > MAX_EXCERPT_CHARS:
        actual = actual[:MAX_EXCERPT_CHARS]
    if actual not in source:
        raise ValueError("Continuity excerpt must be a literal substring.")
    return {
        "turn_index": turn_index,
        "role": role,
        "excerpt": actual,
    }


def _detect_repeated_phrase(
    turns: Sequence[DialogueTurn],
    refs: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if len(turns) < 2:
        return None
    ngram_turns: dict[str, set[int]] = {}
    ngram_sample: dict[str, tuple[int, str]] = {}
    for turn in turns:
        words = _content_words(turn.user_text)
        if len(words) < MIN_REPEATED_NGRAM_WORDS:
            continue
        for i in range(len(words) - MIN_REPEATED_NGRAM_WORDS + 1):
            chunk = words[i : i + MIN_REPEATED_NGRAM_WORDS]
            if all(w in _STOPWORDS for w in chunk):
                continue
            phrase = " ".join(chunk)
            ngram_turns.setdefault(phrase, set()).add(turn.turn_index)
            ngram_sample.setdefault(phrase, (turn.turn_index, turn.user_text))

    candidates = [
        phrase
        for phrase, indices in ngram_turns.items()
        if len(indices) >= 2
    ]
    if not candidates:
        return None
    phrase = sorted(candidates, key=lambda p: (-len(ngram_turns[p]), p))[0]
    indices = sorted(ngram_turns[phrase])
    for turn in turns:
        if turn.turn_index not in indices:
            continue
        if phrase.lower() not in turn.user_text.lower():
            continue
        refs.append(_literal_excerpt(turn.user_text, phrase, turn.turn_index, "user"))
        if len(indices) >= 2 and len(refs) >= MAX_CONTINUITY_REFS:
            break
    return {
        "phrase": phrase,
        "turn_indices": indices,
    }


def _detect_prior_question(
    turns: Sequence[DialogueTurn],
    refs: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for turn in reversed(turns):
        text = turn.user_text.strip()
        if not text:
            continue
        if "?" in text or _INTERROGATIVE_START.match(text):
            q_idx = text.find("?")
            if q_idx >= 0:
                start = max(0, q_idx - 40)
                ref = _make_ref(
                    turn_index=turn.turn_index,
                    role="user",
                    source=text,
                    start=start,
                )
            else:
                ref = _make_ref(
                    turn_index=turn.turn_index,
                    role="user",
                    source=text,
                    start=0,
                )
            refs.append(ref)
            return {
                "turn_index": turn.turn_index,
                "excerpt": ref["excerpt"],
            }
    return None


def _detect_open_thread(
    turns: Sequence[DialogueTurn],
    refs: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if len(turns) < 2:
        return None
    ordered = sorted(turns, key=lambda item: item.turn_index)
    for idx in range(len(ordered) - 1):
        current = ordered[idx]
        nxt = ordered[idx + 1]
        if "?" not in current.parrot_reply:
            continue
        response = nxt.user_text.strip()
        word_count = len(response.split())
        if word_count > OPEN_THREAD_MAX_USER_WORDS:
            continue
        if len(response) > OPEN_THREAD_MAX_USER_CHARS:
            continue
        q_idx = current.parrot_reply.find("?")
        start = max(0, q_idx - 30)
        ref = _make_ref(
            turn_index=current.turn_index,
            role="parrot",
            source=current.parrot_reply,
            start=start,
        )
        refs.append(ref)
        return {
            "parrot_turn_index": current.turn_index,
            "participant_turn_index": nxt.turn_index,
            "parrot_question_excerpt": ref["excerpt"],
            "participant_response_excerpt": response[:MAX_EXCERPT_CHARS],
        }
    return None


def _detect_topic_overlap(
    turns: Sequence[DialogueTurn],
    refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(turns) < 2:
        return []
    token_turns: dict[str, set[int]] = {}
    token_sample: dict[str, tuple[int, str, str]] = {}
    for turn in turns:
        for token in _topic_tokens(turn.user_text):
            token_turns.setdefault(token, set()).add(turn.turn_index)
            token_sample.setdefault(
                token,
                (turn.turn_index, turn.user_text, "user"),
            )
        for token in _topic_tokens(turn.parrot_reply):
            token_turns.setdefault(token, set()).add(turn.turn_index)
            if token not in token_sample:
                token_sample[token] = (
                    turn.turn_index,
                    turn.parrot_reply,
                    "parrot",
                )

    overlaps: list[dict[str, Any]] = []
    for token, indices in sorted(token_turns.items()):
        if len(indices) < 2:
            continue
        overlaps.append({
            "token": token,
            "turn_indices": sorted(indices),
        })
        turn_index, source, role = token_sample[token]
        refs.append(_literal_excerpt(source, token, turn_index, role))
        if len(overlaps) >= 3:
            break
    return overlaps


def _detect_explicit_self_reference(
    turns: Sequence[DialogueTurn],
    refs: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for turn in reversed(turns):
        match = _SELF_REFERENCE.search(turn.user_text)
        if not match:
            continue
        ref = _make_ref(
            turn_index=turn.turn_index,
            role="user",
            source=turn.user_text,
            start=match.start(),
            length=match.end() - match.start(),
        )
        refs.append(ref)
        return {
            "turn_index": turn.turn_index,
            "excerpt": ref["excerpt"],
        }
    return None


def _content_words(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN.finditer(text)]


def _topic_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for word in _content_words(text):
        if len(word) < MIN_TOPIC_TOKEN_LEN:
            continue
        if word in _STOPWORDS:
            continue
        tokens.add(word)
    return tokens


def _validate_index(index: dict[str, Any]) -> None:
    def walk(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_norm = str(key).lower()
                if key_norm in PROHIBITED_INDEX_LABELS:
                    raise ValueError(f"Prohibited continuity label at {path}{key!r}.")
                walk(value, f"{path}{key}.")
        elif isinstance(obj, list):
            for item in obj:
                walk(item, path)
        elif isinstance(obj, str):
            lowered = obj.lower()
            for label in PROHIBITED_INDEX_LABELS:
                if label in lowered and path.endswith("observation_kind."):
                    continue

    walk(index)
    for ref in index.get("continuity_refs") or []:
        if len(str(ref.get("excerpt") or "")) > MAX_EXCERPT_CHARS:
            raise ValueError("Continuity excerpt exceeds max length.")
    if len(index.get("continuity_refs") or []) > MAX_CONTINUITY_REFS:
        raise ValueError("Too many continuity refs.")
