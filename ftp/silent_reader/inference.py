"""Deterministic evidence contract for Phase 4A candidate inferences.

Confidence means how well this interaction's evidence supports the claim.
It is not the probability that the claim is true of the person.

A future RESONATES marker is a separate VALIDATED record. It does not
rewrite the inferred claim.
"""

from __future__ import annotations

from typing import Any

from ftp.events.model import ProvenanceLevel

PROHIBITED_INFERENCE_CATEGORIES = frozenset({
    "gender",
    "sexual_orientation",
    "gender_identity",
    "race_ethnicity",
    "religion",
    "political_ideology",
    "medical_condition",
    "mental_health_diagnosis",
    "disability",
    "socioeconomic_status",
    "criminality",
    "protected_identity",
    "sensitive_personal_attribute",
})

ALLOWED_SCOPES = frozenset({"interaction_specific", "session_specific"})
ALLOWED_CATEGORIES = frozenset({
    "interaction_pattern",
    "detected_rasa_shift",
    "interaction_engagement",
})

# Support score after the sufficiency bar is already met.
# +0.15 when at least two different signal types are cited.
# +0.10 when the claim's own temporal comparison is ok.
# -0.20 when a contradiction is attached.
# -0.10 when an alternative is attached.
# Clamped to [0.15, 0.75]. Never treated as truth-probability.
_CONFIDENCE_FLOOR = 0.15
_CONFIDENCE_CAP = 0.75


def unique_signal_types(items: list[dict[str, Any]]) -> list[str]:
    """Repeated items of one signal type count once."""
    seen: list[str] = []
    for item in items:
        signal = str(item["signal_type"])
        if signal not in seen:
            seen.append(signal)
    return seen


def support_confidence(
    *,
    diversity: int,
    contradiction_count: int,
    alternative_count: int,
    temporal_ok: bool,
) -> float:
    """Bounded support within this interaction, not objective truth."""
    score = 0.45
    if diversity >= 2:
        score += 0.15
    if temporal_ok:
        score += 0.10
    if contradiction_count:
        score -= 0.20
    if alternative_count:
        score -= 0.10
    return round(min(_CONFIDENCE_CAP, max(_CONFIDENCE_FLOOR, score)), 2)


def apply_evidence_contract(
    candidate: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """Return a copy with eligibility set. Does not mutate the input."""
    reviewed = {
        key: candidate[key]
        for key in candidate
        if key != "eligibility"
    }
    reviewed["contradictions"] = list(candidate.get("contradictions") or [])
    reviewed["alternative_interpretations"] = list(
        candidate.get("alternative_interpretations") or []
    )
    reviewed["limitations"] = list(candidate.get("limitations") or [])
    reviewed["evidence_refs"] = list(candidate.get("evidence_refs") or [])

    category = str(candidate.get("category") or "")
    scope = str(candidate.get("scope") or "")
    if category in PROHIBITED_INFERENCE_CATEGORIES or scope not in ALLOWED_SCOPES:
        return _closed(reviewed, "prohibited", "category_or_scope_not_permitted")
    if category not in ALLOWED_CATEGORIES:
        return _closed(reviewed, "prohibited", "category_not_allowed")

    by_id = {item["evidence_id"]: item for item in bundle.get("evidence_items", [])}
    missing = [ref for ref in reviewed["evidence_refs"] if ref not in by_id]
    if missing or not reviewed["evidence_refs"]:
        return _closed(reviewed, "insufficient_evidence", "evidence_refs_missing")

    cited = [by_id[ref] for ref in reviewed["evidence_refs"]]
    signals = unique_signal_types(cited)
    min_signals = int(candidate.get("minimum_signal_types") or 1)
    if len(signals) < min_signals:
        return _closed(reviewed, "insufficient_evidence", "signal_diversity_too_low")

    if candidate.get("requires_temporal_change"):
        length = next((item for item in cited if item["signal_type"] == "message_length"), None)
        direction = None if length is None else (length.get("value") or {}).get("direction")
        if direction not in {"increased", "decreased"}:
            return _closed(reviewed, "insufficient_evidence", "temporal_change_unavailable")

    if any(item.get("signal_type") == "detected_rasa" for item in cited):
        rasa = next(item for item in cited if item["signal_type"] == "detected_rasa")
        sequence = (rasa.get("value") or {}).get("detected_sequence") or []
        if not sequence:
            return _closed(reviewed, "insufficient_evidence", "defaulted_or_missing_rasa")

    blocking = [
        item for item in reviewed["contradictions"]
        if item.get("effect_on_confidence") == "block"
    ]
    if blocking:
        reviewed["eligibility"] = "contradicted"
        reviewed["provenance_level"] = None
        reviewed["confidence"] = None
        reviewed["confidence_basis"] = "blocked_by_contradiction"
        reviewed["limitations"].append("contradiction_blocks_claim")
        return reviewed

    temporal_ok = bool(candidate.get("requires_temporal_change"))
    reviewed["eligibility"] = "eligible"
    reviewed["provenance_level"] = ProvenanceLevel.INFERRED.value
    reviewed["confidence"] = support_confidence(
        diversity=len(signals),
        contradiction_count=len(reviewed["contradictions"]),
        alternative_count=len(reviewed["alternative_interpretations"]),
        temporal_ok=temporal_ok,
    )
    reviewed["confidence_basis"] = (
        "support_within_this_interaction_not_probability_of_truth"
    )
    return reviewed


def propose_candidates(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Closed set of interaction-scoped candidates. No claim without an item."""
    by_signal = {
        item["signal_type"]: item for item in bundle.get("evidence_items", [])
    }
    proposals: list[dict[str, Any]] = []

    length = by_signal.get("message_length")
    if length and length["value"]["direction"] in {"increased", "decreased"}:
        direction = length["value"]["direction"]
        contradictions = []
        engagement = by_signal.get("engagement_state")
        if engagement and engagement["value"]["state"] == "fluctuating":
            contradictions.append({
                "contradiction_id": "cx_length_vs_fluctuation",
                "evidence_refs": ["ev_message_length", "ev_engagement_state"],
                "description": (
                    "Endpoints differ, and intermediate message lengths also changed."
                ),
                "effect_on_confidence": "reduce",
            })
        proposals.append(_proposal(
            "message_length_shift",
            (
                f"Within this session, message length {direction} "
                f"from {length['value']['first']} to {length['value']['final']} characters."
            ),
            "interaction_pattern",
            ["ev_message_length"],
            ["The last turn may simply have had more left to say."],
            contradictions,
            minimum_signal_types=1,
            requires_temporal_change=True,
        ))

    question = by_signal.get("question_rate")
    repetition = by_signal.get("repetition")
    if (
        question
        and repetition
        and question["value"]["turn_count"] >= 3
        and float(question["value"]["value"]) >= 0.34
        and int(repetition["value"]["repetition_count"]) >= 1
    ):
        proposals.append(_proposal(
            "question_repetition",
            "Within this interaction, questions recur alongside repeated wording.",
            "interaction_pattern",
            ["ev_question_rate", "ev_repetition"],
            [
                "The participant may have been trying the prompt again "
                "rather than circling an unresolved question."
            ],
            [],
            minimum_signal_types=2,
            requires_temporal_change=False,
        ))

    rasa = by_signal.get("detected_rasa")
    if rasa and rasa["value"].get("changed") is True:
        proposals.append(_proposal(
            "detected_rasa_change",
            (
                "The first and last detected Rasa labels in this session differ "
                f"({rasa['value']['beginning']} to {rasa['value']['ending']})."
            ),
            "detected_rasa_shift",
            ["ev_detected_rasa"],
            [
                "Different lexicon hits can follow from different words "
                "without being a felt shift."
            ],
            [],
            minimum_signal_types=1,
            requires_temporal_change=False,
        ))

    engagement = by_signal.get("engagement_state")
    if engagement:
        proposals.append(_proposal(
            "engagement_label",
            (
                "Interaction evidence in this session is classified as "
                f"'{engagement['value']['state']}'."
            ),
            "interaction_engagement",
            ["ev_engagement_state"],
            [
                "The label is a rule over measurements in this session, "
                "not a measure of the person's interest."
            ],
            [],
            minimum_signal_types=1,
            requires_temporal_change=False,
        ))
    return proposals


def evaluate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    reviewed = [apply_evidence_contract(item, bundle) for item in propose_candidates(bundle)]
    eligible = [item for item in reviewed if item["eligibility"] == "eligible"]
    status = "ok" if eligible else "insufficient_evidence"
    limitations = [] if eligible else ["no_eligible_inference"]
    if bundle.get("status") == "insufficient":
        limitations.append("bundle_insufficient")
    return {
        "session_id": bundle["session_id"],
        "status": status,
        "records": reviewed,
        "limitations": limitations,
    }


def build_deep_reader_packet(
    bundle: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Curated packet for a future reader. No event store and no director state."""
    eligible = [
        record for record in evaluation["records"]
        if record["eligibility"] == "eligible"
    ]
    return {
        "session_id": bundle["session_id"],
        "evidence_items": [
            {
                "evidence_id": item["evidence_id"],
                "signal_type": item["signal_type"],
                "observation": item["observation"],
                "value": item["value"],
                "source_event_ids": item["source_event_ids"],
                "limitations": item["limitations"],
            }
            for item in bundle["evidence_items"]
        ],
        "eligible_inferences": eligible,
    }


def resonance_marker(inference_id: str) -> dict[str, str]:
    """Participant resonance. Does not change the inferred claim."""
    return {
        "inference_id": inference_id,
        "provenance_level": ProvenanceLevel.VALIDATED.value,
        "user_action": "RESONATES",
        "meaning": (
            "The participant reported resonance. "
            "This does not make the inference true."
        ),
    }


def _proposal(
    rule_id: str,
    claim: str,
    category: str,
    evidence_refs: list[str],
    alternatives: list[str],
    contradictions: list[dict[str, Any]],
    *,
    minimum_signal_types: int,
    requires_temporal_change: bool,
) -> dict[str, Any]:
    return {
        "inference_id": f"inf_{rule_id}",
        "claim": claim,
        "category": category,
        "scope": "session_specific",
        "evidence_refs": evidence_refs,
        "confidence": None,
        "confidence_basis": None,
        "alternative_interpretations": alternatives,
        "contradictions": contradictions,
        "limitations": [],
        "eligibility": None,
        "provenance_level": None,
        "minimum_signal_types": minimum_signal_types,
        "requires_temporal_change": requires_temporal_change,
    }


def _closed(reviewed: dict[str, Any], eligibility: str, limitation: str) -> dict[str, Any]:
    reviewed["eligibility"] = eligibility
    reviewed["provenance_level"] = None
    reviewed["confidence"] = None
    reviewed["confidence_basis"] = None
    if limitation not in reviewed["limitations"]:
        reviewed["limitations"].append(limitation)
    return reviewed
