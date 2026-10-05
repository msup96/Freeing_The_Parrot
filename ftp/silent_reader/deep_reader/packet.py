"""Narrow reader input for Gemini. The wide Phase 4A packet must not be sent."""

from __future__ import annotations

from typing import Any, TypedDict


class ReaderInput(TypedDict):
    session_id: str
    instruction: str
    evidence_items: list[dict[str, Any]]
    inferences: list[dict[str, Any]]
    packet_consistent: bool


_INFERENCE_KEYS = (
    "inference_id",
    "claim",
    "category",
    "scope",
    "evidence_refs",
    "alternative_interpretations",
    "contradictions",
    "limitations",
)


def build_reader_input(
    *,
    bundle: dict[str, Any],
    evaluation: dict[str, Any],
    instruction: str,
) -> ReaderInput:
    """Build the only object the Gemini adapter may receive."""
    eligible = [
        record for record in evaluation.get("records", [])
        if record.get("eligibility") == "eligible"
    ]
    by_id = {item["evidence_id"]: item for item in bundle.get("evidence_items", [])}
    cited: set[str] = set()
    for record in eligible:
        cited.update(record.get("evidence_refs") or [])
        for contradiction in record.get("contradictions") or []:
            cited.update(contradiction.get("evidence_refs") or [])

    packet_consistent = all(ref in by_id for ref in cited)
    evidence_items = [_slim_evidence(by_id[ref]) for ref in sorted(cited) if ref in by_id]
    inferences = [_slim_inference(record) for record in eligible]

    return ReaderInput(
        session_id=str(bundle["session_id"]),
        instruction=instruction,
        evidence_items=evidence_items,
        inferences=inferences,
        packet_consistent=packet_consistent,
    )


def assert_narrow_reader_input(reader_input: dict[str, Any]) -> None:
    """Reject accidental use of the wide Phase 4A packet."""
    if "eligible_inferences" in reader_input:
        raise TypeError("Gemini adapter requires narrow reader input, not the wide packet.")
    if "packet_consistent" not in reader_input:
        raise TypeError("Gemini adapter requires narrow reader input with packet_consistent.")
    for item in reader_input.get("evidence_items", []):
        if "source_event_ids" in item:
            raise TypeError("reader input must not contain source_event_ids.")


def _slim_evidence(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("value")
    if item.get("signal_type") == "engagement_state" and isinstance(value, dict):
        value = {"state": value.get("state")}
    return {
        "evidence_id": item["evidence_id"],
        "signal_type": item["signal_type"],
        "observation": item["observation"],
        "value": value,
        "limitations": list(item.get("limitations") or []),
    }


def _slim_inference(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in _INFERENCE_KEYS
        if key in record
    }
