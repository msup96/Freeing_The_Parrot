"""Strict JSON parsing for Gemini gloss responses."""

from __future__ import annotations

import json
import re
from typing import Any

_INTERPRETATION_KEYS = frozenset({"inference_id", "cited_evidence_ids", "text"})
_ROOT_KEYS = frozenset({"interpretations"})


class ReaderParseError(Exception):
    """Malformed model JSON or roster mismatch."""


def parse_reader_response(raw: str, expected_inference_ids: list[str]) -> list[dict[str, Any]]:
    """Parse and validate roster shape. Does not salvage malformed output."""
    body = _strip_for_json(raw)
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ReaderParseError("malformed_json") from exc

    if not isinstance(parsed, dict):
        raise ReaderParseError("non_object_root")
    if set(parsed.keys()) != _ROOT_KEYS:
        raise ReaderParseError("schema_extra_field")

    interpretations = parsed["interpretations"]
    if not isinstance(interpretations, list):
        raise ReaderParseError("missing_interpretations")

    expected = list(expected_inference_ids)
    if len(interpretations) != len(expected):
        raise ReaderParseError("roster_count_mismatch")

    seen: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    for item in interpretations:
        if not isinstance(item, dict):
            raise ReaderParseError("interpretation_not_object")
        if set(item.keys()) != _INTERPRETATION_KEYS:
            raise ReaderParseError("schema_extra_field")
        inference_id = item["inference_id"]
        if inference_id in seen:
            raise ReaderParseError("duplicate_inference_id")
        seen.add(inference_id)
        if not isinstance(item["cited_evidence_ids"], list):
            raise ReaderParseError("cited_evidence_ids_invalid")
        if not isinstance(item["text"], str):
            raise ReaderParseError("text_invalid")
        by_id[inference_id] = item

    missing = [item for item in expected if item not in by_id]
    if missing:
        raise ReaderParseError("missing_inference_id")
    unknown = [item for item in by_id if item not in expected]
    if unknown:
        raise ReaderParseError("unknown_inference_id")

    return [by_id[item] for item in expected]


def _strip_for_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        raise ReaderParseError("markdown_fence")
    if not text.startswith("{"):
        raise ReaderParseError("prose_wrapper")
    return text


def extract_integers_from_values(value: Any) -> set[int]:
    found: set[int] = set()
    if isinstance(value, bool):
        return found
    if isinstance(value, int):
        found.add(value)
    elif isinstance(value, float) and value.is_integer():
        found.add(int(value))
    elif isinstance(value, str):
        for match in re.findall(r"\d+", value):
            found.add(int(match))
    elif isinstance(value, dict):
        for item in value.values():
            found.update(extract_integers_from_values(item))
    elif isinstance(value, list):
        for item in value:
            found.update(extract_integers_from_values(item))
    return found
