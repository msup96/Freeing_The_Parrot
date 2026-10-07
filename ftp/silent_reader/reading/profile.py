"""Build a ReadingProfile from Phase 4B output."""

from __future__ import annotations

import re
from typing import Any


_FORBIDDEN_SEED_TOKENS = (
    "navarasa", "ocr", "sentiment", "evidence_id", "inference_id", "event_id",
    "telemetry", "shanta", "raudra", "hasya", "karuna", "bibhatsa", "adbhuta",
    "bhayanaka", "veera", "confidence", "gemini",
)

_SAFE_CATEGORY_FALLBACKS = {
    "temporal_pattern": "A rhythm changed as the exchange continued.",
    "engagement": "A quiet attention gathered and shifted.",
    "message_length": "The shape of the exchange left a gentle trace.",
    "interaction_pattern": "A small pattern held its place between the moments.",
    "emotional_tone": "A feeling moved softly beneath the surface.",
}
_DEFAULT_SAFE_FALLBACK = "A quiet pattern gathered at the edge of the exchange."


def build_reading_profile(
    *,
    bundle: dict[str, Any],
    evaluation: dict[str, Any],
    reader_result: dict[str, Any],
) -> dict[str, Any]:
    """Curate composition anchors from validated Phase 4B reader output."""
    anchors: list[dict[str, Any]] = []
    evidence_by_id = {
        item["evidence_id"]: item for item in bundle.get("evidence_items", [])
    }

    for record in reader_result.get("records") or []:
        interpretation = record.get("interpretation") or {}
        seed = interpretation.get("text") or interpretation.get("fallback_text") or record["claim"]
        anchors.append({
            "anchor_id": f"anchor_{record['inference_id']}",
            "inference_id": record["inference_id"],
            "category": record["category"],
            "evidence_refs": list(record.get("evidence_refs") or []),
            "reading_seed": _sanitize_seed(str(seed), category=record["category"]),
            "reader_status": interpretation.get("status"),
            "confidence": record.get("confidence"),
            "analytical_source": {
                "claim": record.get("claim"),
                "interpretation": interpretation,
                "evidence_refs": list(record.get("evidence_refs") or []),
            },
        })

    if not anchors:
        anchors.extend(_evidence_only_anchors(evidence_by_id, bundle))

    if not anchors:
        anchors.append({
            "anchor_id": "anchor_session_threshold",
            "inference_id": "reading_anchor_session_threshold",
            "category": "interaction_pattern",
            "evidence_refs": [],
            "reading_seed": "The exchange stayed brief, yet something still gathered at the edges.",
            "reader_status": "insufficient_evidence",
            "confidence": None,
        })

    return {
        "session_id": bundle["session_id"],
        "reader_status": reader_result.get("status", "insufficient_evidence"),
        "evaluation_status": evaluation.get("status"),
        "limitations": list(bundle.get("limitations") or []) + list(evaluation.get("limitations") or []),
        "anchors": anchors,
        "evidence_catalog": {
            item_id: {
                "signal_type": item.get("signal_type"),
                "observation": item.get("observation"),
            }
            for item_id, item in evidence_by_id.items()
        },
    }


def _evidence_only_anchors(
    evidence_by_id: dict[str, dict[str, Any]],
    bundle: dict[str, Any],
) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for item in bundle.get("evidence_items", []):
        item_id = item["evidence_id"]
        anchors.append({
            "anchor_id": f"anchor_{item_id}",
            "inference_id": f"reading_anchor_{item_id}",
            "category": "interaction_pattern",
            "evidence_refs": [item_id],
            "reading_seed": _sanitize_seed(str(item.get("observation") or "A quiet pattern held the session.")),
            "reader_status": "insufficient_evidence",
            "confidence": None,
        })
    return anchors


def _sanitize_seed(seed: str, *, category: str = "interaction_pattern") -> str:
    cleaned = seed.replace("Within this session,", "").replace("Within this interaction,", "")
    cleaned = cleaned.replace("Interaction evidence in this session is classified as", "A rhythm in this session resembled")
    cleaned = " ".join(cleaned.split())
    lowered = cleaned.lower()
    has_internal_identifier = bool(re.search(r"\b(?:ev|inf)_[a-z0-9_]+\b", lowered))
    has_forbidden_token = any(re.search(rf"\b{re.escape(token)}\b", lowered) for token in _FORBIDDEN_SEED_TOKENS)
    if has_internal_identifier or has_forbidden_token:
        return _SAFE_CATEGORY_FALLBACKS.get(category, _DEFAULT_SAFE_FALLBACK)
    return cleaned or _SAFE_CATEGORY_FALLBACKS.get(category, _DEFAULT_SAFE_FALLBACK)
