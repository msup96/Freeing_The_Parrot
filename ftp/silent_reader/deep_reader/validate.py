"""Application-side semantic validation for Gemini glosses."""

from __future__ import annotations

import re
from typing import Any

from ftp.silent_reader.deep_reader.parse import extract_integers_from_values

SHARED_FUNCTION_WORDS = frozenset({
    "in", "this", "session", "the", "a", "of", "and", "from", "to",
})

GLOBAL_BANNED_TOKENS = frozenset({
    "invested", "emotional", "emotion", "felt", "feeling", "trust",
    "vulnerable", "personality", "curious", "uncertain", "unresolved",
    "anxious", "depressed", "trauma", "diagnosis", "always", "truly",
    "deep", "down", "soul", "market", "data", "know", "understand",
})

RULE_VOCABULARIES: dict[str, frozenset[str]] = {
    "inf_message_length_shift": frozenset({
        "you", "your", "messages", "responses", "became", "become",
        "longer", "shorter", "toward", "end", "interaction", "appeared",
        "appear", "willing", "elaborate", "brief", "rather", "than",
        "keeping", "during",
    }),
    "inf_question_repetition": frozenset({
        "questions", "question", "recur", "recurred", "alongside",
        "repeated", "wording", "you", "your", "again", "interaction",
    }),
    "inf_detected_rasa_change": frozenset({
        "first", "last", "detected", "rasa", "labels", "label", "differ",
        "differed", "from", "interaction",
    }),
    "inf_engagement_label": frozenset({
        "interaction", "evidence", "is", "classified", "as",
    }),
}

FORBIDDEN_SCOPE_PHRASES = (
    "you are",
    "you're",
    "you were a",
)


def validate_interpretation(
    interpretation: dict[str, Any],
    record: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Return rejection reason codes. Empty list means accepted."""
    reasons: list[str] = []
    text = interpretation["text"]
    inference_id = record["inference_id"]
    expected_refs = list(record.get("evidence_refs") or [])
    cited = list(interpretation.get("cited_evidence_ids") or [])

    if sorted(cited) != sorted(expected_refs):
        reasons.append("evidence_refs_mismatch")

    permitted_ids = set(expected_refs) | {inference_id}
    for token in re.findall(r"\b(?:ev|inf)_[a-z0-9_]+\b", text):
        if token not in permitted_ids:
            reasons.append("fabricated_id")

    allowed_numbers = extract_integers_from_values(record.get("claim"))
    for ref in expected_refs:
        if ref in evidence_by_id:
            allowed_numbers.update(extract_integers_from_values(evidence_by_id[ref]))
    for number in re.findall(r"\b\d+\b", text):
        if int(number) not in allowed_numbers:
            reasons.append("number_not_in_evidence")

    lowered = text.lower()
    if "this session" not in lowered:
        reasons.append("scope_phrase_missing")
    if len(text.split()) > 40:
        reasons.append("too_long")

    for phrase in FORBIDDEN_SCOPE_PHRASES:
        if phrase in lowered:
            reasons.append("banned_token")

    for banned in GLOBAL_BANNED_TOKENS:
        if re.search(rf"\b{re.escape(banned)}\b", lowered):
            reasons.append("banned_token")

    direction_reason = _direction_check(record, lowered)
    if direction_reason:
        reasons.append(direction_reason)

    rasa_reason = _rasa_check(record, text)
    if rasa_reason:
        reasons.append(rasa_reason)

    engagement_reason = _engagement_check(record, lowered)
    if engagement_reason:
        reasons.append(engagement_reason)

    vocab_reasons = _vocabulary_check(record, text)
    reasons.extend(vocab_reasons)

    if _contradiction_overwritten(text, record.get("contradictions") or []):
        reasons.append("contradiction_overwritten")

    return sorted(set(reasons))


def _direction_check(record: dict[str, Any], lowered: str) -> str | None:
    if record["inference_id"] != "inf_message_length_shift":
        return None
    claim = record["claim"].lower()
    if "increased" in claim and re.search(r"\bshorter\b", lowered):
        return "direction_reversed"
    if "decreased" in claim and re.search(r"\blonger\b", lowered):
        return "direction_reversed"
    return None


def _rasa_check(record: dict[str, Any], text: str) -> str | None:
    if record["inference_id"] != "inf_detected_rasa_change":
        return None
    labels = _rasa_labels_from_claim(record["claim"])
    if not labels:
        return "vocabulary_outside_rule"
    allowed_names = labels | {"Rasa"}
    for match in re.finditer(r"\b([A-Z][a-z]+)\b", text):
        word = match.group(1)
        if word in {"In", "The"}:
            continue
        if word not in allowed_names:
            return "vocabulary_outside_rule"
    return None


def _engagement_check(record: dict[str, Any], lowered: str) -> str | None:
    if record["inference_id"] != "inf_engagement_label":
        return None
    if re.search(r"\byou\b", lowered):
        return "banned_token"
    state = _engagement_state_from_claim(record["claim"])
    if state and state not in lowered:
        return "vocabulary_outside_rule"
    if "classified as" not in lowered:
        return "vocabulary_outside_rule"
    return None


def _vocabulary_check(record: dict[str, Any], text: str) -> list[str]:
    inference_id = record["inference_id"]
    rule_vocab = RULE_VOCABULARIES.get(inference_id, frozenset())
    allowed = SHARED_FUNCTION_WORDS | rule_vocab
    allowed_numbers = extract_integers_from_values(record.get("claim"))
    if inference_id == "inf_detected_rasa_change":
        allowed = allowed | {label.lower() for label in _rasa_labels_from_claim(record["claim"])}
    if inference_id == "inf_engagement_label":
        allowed = allowed | {_engagement_state_from_claim(record["claim"])}

    reasons: list[str] = []
    for token in _word_tokens(text):
        if token.isdigit():
            if int(token) not in allowed_numbers:
                reasons.append("number_not_in_evidence")
            continue
        if token not in allowed:
            reasons.append("vocabulary_outside_rule")
    return reasons


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _rasa_labels_from_claim(claim: str) -> set[str]:
    match = re.search(r"\(([^)]+)\)", claim)
    if not match:
        return set()
    inner = match.group(1)
    parts = re.split(r"\s+to\s+", inner.strip())
    return {part.strip() for part in parts if part.strip()}


def _engagement_state_from_claim(claim: str) -> str:
    match = re.search(r"'([^']+)'", claim)
    return match.group(1) if match else ""


def _contradiction_overwritten(text: str, contradictions: list[dict[str, Any]]) -> bool:
    lowered = text.lower()
    for contradiction in contradictions:
        if contradiction.get("effect_on_confidence") != "reduce":
            continue
        contradiction_id = contradiction.get("contradiction_id")
        if contradiction_id == "cx_length_vs_fluctuation":
            if any(
                phrase in lowered
                for phrase in (
                    "steady throughout",
                    "unchanged throughout",
                    "consistent length",
                    "only the endpoints",
                )
            ):
                return True
        desc = str(contradiction.get("description", "")).lower()
        if "intermediate" in desc and "steady" in lowered:
            return True
    return False
