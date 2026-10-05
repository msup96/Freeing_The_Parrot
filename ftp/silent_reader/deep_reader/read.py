"""Orchestrate Phase 4B gloss generation."""

from __future__ import annotations

from typing import Any

from ftp.events.model import ProvenanceLevel
from ftp.silent_reader.deep_reader.adapter import READER_INSTRUCTION, GeminiUnavailable
from ftp.silent_reader.deep_reader.packet import build_reader_input
from ftp.silent_reader.deep_reader.parse import ReaderParseError, parse_reader_response
from ftp.silent_reader.deep_reader.validate import validate_interpretation


def read_session_interpretations(
    bundle: dict[str, Any],
    evaluation: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """Run the gloss pipeline in memory. Does not write events."""
    eligible = [
        record for record in evaluation.get("records", [])
        if record.get("eligibility") == "eligible"
    ]
    if not eligible:
        return {
            "session_id": evaluation["session_id"],
            "status": "insufficient_evidence",
            "gemini_called": False,
            "records": [],
        }

    reader_input = build_reader_input(
        bundle=bundle,
        evaluation=evaluation,
        instruction=READER_INSTRUCTION,
    )
    if not reader_input["packet_consistent"]:
        return _fallback_all(eligible, evaluation["session_id"], gemini_called=False)

    try:
        raw = adapter.complete(reader_input)
        gemini_called = True
    except GeminiUnavailable:
        return _fallback_all(eligible, evaluation["session_id"], gemini_called=True)

    expected_ids = [record["inference_id"] for record in eligible]
    try:
        interpretations = parse_reader_response(raw, expected_ids)
    except ReaderParseError:
        return _fallback_all(eligible, evaluation["session_id"], gemini_called=True)

    evidence_by_id = {item["evidence_id"]: item for item in reader_input["evidence_items"]}
    by_inference = {item["inference_id"]: item for item in interpretations}
    records: list[dict[str, Any]] = []
    accepted_count = 0

    for source in eligible:
        interpretation_payload = by_inference[source["inference_id"]]
        reasons = validate_interpretation(
            interpretation_payload,
            source,
            evidence_by_id,
        )
        if reasons:
            records.append(_assemble_record(
                source,
                status="rejected",
                text=None,
                author="deterministic",
                rejection_reasons=reasons,
            ))
        else:
            accepted_count += 1
            records.append(_assemble_record(
                source,
                status="accepted",
                text=interpretation_payload["text"],
                author="gemini",
                rejection_reasons=[],
            ))

    if accepted_count == 0:
        status = "fallback"
    elif accepted_count == len(eligible):
        status = "ok"
    else:
        status = "partial"

    return {
        "session_id": evaluation["session_id"],
        "status": status,
        "gemini_called": gemini_called,
        "records": records,
    }


def _fallback_all(
    eligible: list[dict[str, Any]],
    session_id: str,
    *,
    gemini_called: bool,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "status": "fallback",
        "gemini_called": gemini_called,
        "records": [
            _assemble_record(
                source,
                status="fallback",
                text=None,
                author="deterministic",
                rejection_reasons=["whole_response_fallback"],
            )
            for source in eligible
        ],
    }


def _assemble_record(
    source: dict[str, Any],
    *,
    status: str,
    text: str | None,
    author: str,
    rejection_reasons: list[str],
) -> dict[str, Any]:
    if status == "accepted":
        interpretation_provenance = ProvenanceLevel.INFERRED.value
    else:
        interpretation_provenance = ProvenanceLevel.INFERRED.value

    return {
        "inference_id": source["inference_id"],
        "claim": source["claim"],
        "category": source["category"],
        "scope": source["scope"],
        "evidence_refs": list(source["evidence_refs"]),
        "confidence": source["confidence"],
        "confidence_basis": source["confidence_basis"],
        "alternative_interpretations": list(source["alternative_interpretations"]),
        "contradictions": list(source["contradictions"]),
        "limitations": list(source["limitations"]),
        "provenance_level": source["provenance_level"],
        "interpretation": {
            "status": status,
            "text": text,
            "fallback_text": source["claim"],
            "rejection_reasons": list(rejection_reasons),
            "provenance_level": interpretation_provenance,
            "author": author,
        },
    }
