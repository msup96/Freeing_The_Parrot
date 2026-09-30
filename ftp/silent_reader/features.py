"""OBSERVED feature payloads for Silent Reader (Phase 3B)."""

from __future__ import annotations

from typing import Any


def build_composer_telemetry_payload(
    turn_index: int,
    typing_duration_ms: float,
    pause_before_submit_ms: float,
    message_length: int,
) -> dict:
    """Phase 3A composer signals (unchanged semantics)."""
    return {
        "observation_type": "composer",
        "turn": turn_index,
        "typing_duration_ms": typing_duration_ms,
        "pause_before_submit_ms": pause_before_submit_ms,
        "message_length": message_length,
    }


def build_derived_feature_payload(
    feature: str,
    value: Any,
    unit: str,
    source_event_ids: list[str],
    turn_index: int | None = None,
) -> dict:
    """Structured OBSERVED feature derived from timeline events."""
    payload: dict = {
        "observation_type": "derived",
        "feature": feature,
        "value": value,
        "unit": unit,
        "source_event_ids": list(source_event_ids),
    }
    if turn_index is not None:
        payload["turn_index"] = turn_index
    return payload
