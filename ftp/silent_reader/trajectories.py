"""Session-level temporal trajectories from existing InteractionEvents.

This layer answers what changed across a session. It does not claim what
that change means about a person. Provenance stays below INFERRED.
"""

from __future__ import annotations

import datetime
import hashlib
import statistics
from typing import TYPE_CHECKING, Any

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel

if TYPE_CHECKING:
    from ftp.session.coordinator import SessionCoordinator

_INSUFFICIENT = "insufficient"
_MISSING = "missing"


def _parse_ts(iso: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(iso)


def _seconds_between(earlier: str, later: str) -> float:
    delta = _parse_ts(later) - _parse_ts(earlier)
    return max(0.0, delta.total_seconds())


def _round_optional(value: float | None, digits: int = 3) -> float | None:
    if value is None:
        return None
    return round(value, digits)


class TemporalTrajectorySynthesizer:
    """Deterministic temporal synthesis. The Parrot never reads this output."""

    def __init__(self, coordinator: SessionCoordinator) -> None:
        self._coordinator = coordinator

    def synthesize(self) -> dict:
        events = self._coordinator.store.all_events()
        turns = self._build_turn_sequence(events)
        length_values = [turn["message_length"] for turn in turns]
        latency_values = [turn["response_latency"] for turn in turns]
        gap_values = [turn["inter_turn_gap"] for turn in turns]
        length_ids = [turn["event_id"] for turn in turns]
        latency_ids = [
            eid
            for turn in turns
            for eid in turn["latency_source_event_ids"]
        ]
        gap_ids = [
            eid
            for turn in turns
            for eid in turn["gap_source_event_ids"]
        ]

        payload = {
            "session_id": self._coordinator.session_id,
            "observation_kind": "temporal_trajectory",
            "provenance_level": ProvenanceLevel.INTERPRETED.value,
            "turn_sequence": [
                {
                    "turn_index": turn["turn_index"],
                    "event_id": turn["event_id"],
                    "timestamp": turn["timestamp"],
                    "message_length": turn["message_length"],
                    "response_latency": turn["response_latency"],
                    "inter_turn_gap": turn["inter_turn_gap"],
                    "repeated_message": turn["repeated_message"],
                    "typing_duration_ms": turn["typing_duration_ms"],
                    "pause_before_submit_ms": turn["pause_before_submit_ms"],
                    "source_event_ids": turn["source_event_ids"],
                }
                for turn in turns
            ],
            "message_length_trajectory": self._numeric_trajectory(
                length_values,
                length_ids,
                unit="characters",
            ),
            "response_latency_trajectory": self._numeric_trajectory(
                latency_values,
                latency_ids,
                unit="seconds",
            ),
            "inter_turn_gap_trajectory": self._numeric_trajectory(
                gap_values,
                gap_ids,
                unit="seconds",
            ),
            "repetition": self._repetition(turns),
            "beginning_vs_ending": self._beginning_vs_ending(turns),
            "volatility": {
                "message_length": self._volatility(length_values),
                "response_latency": self._volatility(latency_values),
                "inter_turn_gap": self._volatility(gap_values),
            },
        }
        return payload

    def _build_turn_sequence(
        self, events: tuple[InteractionEvent, ...]
    ) -> list[dict[str, Any]]:
        parrot_turns = [
            event
            for event in events
            if event.event_type == EventType.PARROT_TURN_GENERATED
        ]
        derived_by_turn = self._index_derived_features(events)
        composer_by_turn = self._index_composer(events)
        sequence: list[dict[str, Any]] = []
        prior_hashes: list[str] = []

        for index, parrot_event in enumerate(parrot_turns):
            turn_index = int(parrot_event.payload.get("turn_index", index))
            user_text = str(parrot_event.payload.get("user_text") or "")
            derived = derived_by_turn.get(turn_index, {})
            composer = composer_by_turn.get(turn_index, {})

            message_length = self._first_present_number(
                derived.get("message_length"),
                len(user_text),
            )
            response_latency, latency_ids = self._resolve_latency(
                parrot_event, events, derived
            )
            inter_turn_gap, gap_ids = self._resolve_gap(
                parrot_event, parrot_turns, derived
            )
            text_hash = hashlib.sha256(user_text.encode("utf-8")).hexdigest()
            repeated = derived.get("repeated_message")
            if repeated is None:
                repeated = text_hash in prior_hashes
            prior_hashes.append(text_hash)

            source_ids = [parrot_event.event_id]
            for extra_ids in (latency_ids, gap_ids):
                for event_id in extra_ids:
                    if event_id not in source_ids:
                        source_ids.append(event_id)
            if composer.get("event_id") and composer["event_id"] not in source_ids:
                source_ids.append(composer["event_id"])

            sequence.append(
                {
                    "turn_index": turn_index,
                    "event_id": parrot_event.event_id,
                    "timestamp": parrot_event.timestamp,
                    "message_length": int(message_length),
                    "response_latency": _round_optional(response_latency),
                    "inter_turn_gap": _round_optional(inter_turn_gap),
                    "repeated_message": bool(repeated),
                    "typing_duration_ms": composer.get("typing_duration_ms"),
                    "pause_before_submit_ms": composer.get("pause_before_submit_ms"),
                    "source_event_ids": source_ids,
                    "latency_source_event_ids": latency_ids,
                    "gap_source_event_ids": gap_ids,
                }
            )
        return sequence

    @staticmethod
    def _index_derived_features(
        events: tuple[InteractionEvent, ...]
    ) -> dict[int, dict[str, Any]]:
        indexed: dict[int, dict[str, Any]] = {}
        for event in events:
            payload = event.payload
            if event.event_type != EventType.TELEMETRY_RECORDED:
                continue
            if payload.get("observation_type") != "derived":
                continue
            turn_index = payload.get("turn_index")
            feature = payload.get("feature")
            if turn_index is None or feature is None:
                continue
            bucket = indexed.setdefault(int(turn_index), {})
            bucket[str(feature)] = payload.get("value")
            bucket.setdefault("_source_ids", {})
            bucket["_source_ids"][str(feature)] = list(
                payload.get("source_event_ids") or [event.event_id]
            )
        return indexed

    @staticmethod
    def _index_composer(
        events: tuple[InteractionEvent, ...]
    ) -> dict[int, dict[str, Any]]:
        indexed: dict[int, dict[str, Any]] = {}
        for event in events:
            payload = event.payload
            if event.event_type != EventType.TELEMETRY_RECORDED:
                continue
            if payload.get("observation_type") != "composer":
                continue
            turn_index = payload.get("turn")
            if turn_index is None:
                continue
            indexed[int(turn_index)] = {
                "event_id": event.event_id,
                "typing_duration_ms": payload.get("typing_duration_ms"),
                "pause_before_submit_ms": payload.get("pause_before_submit_ms"),
            }
        return indexed

    @staticmethod
    def _resolve_latency(
        parrot_event: InteractionEvent,
        all_events: tuple[InteractionEvent, ...],
        derived: dict[str, Any],
    ) -> tuple[float | None, list[str]]:
        if "response_latency" in derived and derived["response_latency"] is not None:
            return (
                float(derived["response_latency"]),
                list(derived.get("_source_ids", {}).get("response_latency") or []),
            )
        preceding_raw = None
        for event in reversed(all_events):
            if event.sequence_num >= parrot_event.sequence_num:
                continue
            if event.event_type != EventType.INPUT_RAW_INGESTED:
                continue
            if event.payload.get("modality") == "TEXT":
                preceding_raw = event
                break
        if preceding_raw is None:
            return None, []
        return (
            _seconds_between(preceding_raw.timestamp, parrot_event.timestamp),
            [preceding_raw.event_id, parrot_event.event_id],
        )

    @staticmethod
    def _resolve_gap(
        parrot_event: InteractionEvent,
        parrot_turns: list[InteractionEvent],
        derived: dict[str, Any],
    ) -> tuple[float | None, list[str]]:
        if "inter_turn_gap" in derived and derived["inter_turn_gap"] is not None:
            return (
                float(derived["inter_turn_gap"]),
                list(derived.get("_source_ids", {}).get("inter_turn_gap") or []),
            )
        prior = [
            event
            for event in parrot_turns
            if event.sequence_num < parrot_event.sequence_num
        ]
        if not prior:
            return None, []
        return (
            _seconds_between(prior[-1].timestamp, parrot_event.timestamp),
            [prior[-1].event_id, parrot_event.event_id],
        )

    @staticmethod
    def _first_present_number(preferred: Any, fallback: int) -> int:
        if preferred is None:
            return fallback
        return int(preferred)

    def _numeric_trajectory(
        self,
        values: list[float | None],
        source_event_ids: list[str],
        *,
        unit: str,
    ) -> dict[str, Any]:
        present = [value for value in values if value is not None]
        unique_ids: list[str] = []
        for event_id in source_event_ids:
            if event_id not in unique_ids:
                unique_ids.append(event_id)

        if not present:
            return {
                "provenance_level": ProvenanceLevel.OBSERVED.value,
                "unit": unit,
                "sufficient": False,
                "status": _MISSING if values else _INSUFFICIENT,
                "per_turn": values,
                "first": None,
                "final": None,
                "mean": None,
                "minimum": None,
                "maximum": None,
                "change": {
                    "status": _MISSING if values else _INSUFFICIENT,
                    "absolute": None,
                    "direction": _INSUFFICIENT,
                },
                "source_event_ids": unique_ids,
            }

        first = present[0]
        final = present[-1]
        change_status = "ok" if len(present) >= 2 else _INSUFFICIENT
        absolute = round(final - first, 3) if len(present) >= 2 else None
        return {
            "provenance_level": ProvenanceLevel.OBSERVED.value,
            "unit": unit,
            "sufficient": len(present) >= 1,
            "status": "ok",
            "per_turn": values,
            "first": first,
            "final": final,
            "mean": round(statistics.fmean(present), 3),
            "minimum": min(present),
            "maximum": max(present),
            "change": {
                "status": change_status,
                "absolute": absolute,
                "direction": self._direction(first, final, len(present)),
            },
            "source_event_ids": unique_ids,
        }

    @staticmethod
    def _direction(first: float, final: float, count: int) -> str:
        if count < 2:
            return _INSUFFICIENT
        if final > first:
            return "increased"
        if final < first:
            return "decreased"
        return "unchanged"

    def _repetition(self, turns: list[dict[str, Any]]) -> dict[str, Any]:
        repeated = [turn for turn in turns if turn["repeated_message"]]
        phases = {"early": 0, "mid": 0, "late": 0}
        for turn in repeated:
            phases[self._phase(turn["turn_index"], turns)] += 1
        return {
            "provenance_level": ProvenanceLevel.OBSERVED.value,
            "repetition_count": len(repeated),
            "repeated_turns": [
                {
                    "turn_index": turn["turn_index"],
                    "event_id": turn["event_id"],
                    "phase": self._phase(turn["turn_index"], turns),
                }
                for turn in repeated
            ],
            "phases": phases,
            "source_event_ids": [turn["event_id"] for turn in repeated],
        }

    @staticmethod
    def _phase(turn_index: int, turns: list[dict[str, Any]]) -> str:
        if not turns:
            return "early"
        ordered = sorted(turn["turn_index"] for turn in turns)
        position = ordered.index(turn_index) if turn_index in ordered else 0
        n = len(ordered)
        if n <= 1:
            return "early"
        third = max(n / 3.0, 1.0)
        if position < third:
            return "early"
        if position < 2 * third:
            return "mid"
        return "late"

    def _beginning_vs_ending(self, turns: list[dict[str, Any]]) -> dict[str, Any]:
        if not turns:
            return {
                "provenance_level": ProvenanceLevel.OBSERVED.value,
                "sufficient": False,
                "status": _INSUFFICIENT,
                "beginning": None,
                "ending": None,
                "message_length_change": {"status": _INSUFFICIENT, "absolute": None},
                "latency_change": {"status": _INSUFFICIENT, "absolute": None},
                "inter_turn_gap_change": {"status": _INSUFFICIENT, "absolute": None},
                "source_event_ids": [],
            }

        beginning = turns[0]
        ending = turns[-1]
        sufficient = len(turns) >= 2
        return {
            "provenance_level": ProvenanceLevel.OBSERVED.value,
            "sufficient": sufficient,
            "status": "ok" if sufficient else _INSUFFICIENT,
            "beginning": self._snapshot(beginning),
            "ending": self._snapshot(ending),
            "message_length_change": self._pair_change(
                beginning["message_length"],
                ending["message_length"],
                sufficient,
            ),
            "latency_change": self._pair_change(
                beginning["response_latency"],
                ending["response_latency"],
                sufficient,
            ),
            "inter_turn_gap_change": self._pair_change(
                beginning["inter_turn_gap"],
                ending["inter_turn_gap"],
                sufficient,
            ),
            "source_event_ids": [beginning["event_id"], ending["event_id"]]
            if beginning["event_id"] != ending["event_id"]
            else [beginning["event_id"]],
        }

    @staticmethod
    def _snapshot(turn: dict[str, Any]) -> dict[str, Any]:
        return {
            "turn_index": turn["turn_index"],
            "event_id": turn["event_id"],
            "timestamp": turn["timestamp"],
            "message_length": turn["message_length"],
            "response_latency": turn["response_latency"],
            "inter_turn_gap": turn["inter_turn_gap"],
        }

    @staticmethod
    def _pair_change(
        first: float | None,
        final: float | None,
        sufficient: bool,
    ) -> dict[str, Any]:
        if not sufficient:
            return {"status": _INSUFFICIENT, "absolute": None, "direction": _INSUFFICIENT}
        if first is None or final is None:
            return {"status": _MISSING, "absolute": None, "direction": _MISSING}
        absolute = round(final - first, 3)
        if absolute > 0:
            direction = "increased"
        elif absolute < 0:
            direction = "decreased"
        else:
            direction = "unchanged"
        return {"status": "ok", "absolute": absolute, "direction": direction}

    def _volatility(self, values: list[float | None]) -> dict[str, Any]:
        present = [value for value in values if value is not None]
        if len(present) < 3:
            return {
                "provenance_level": ProvenanceLevel.OBSERVED.value,
                "sufficient": False,
                "status": _INSUFFICIENT,
                "transition_count": None,
                "consecutive_repeat_count": None,
                "range": None,
                "normalized_variation": None,
            }

        transitions = sum(
            1 for left, right in zip(present, present[1:]) if left != right
        )
        consecutive_repeats = sum(
            1 for left, right in zip(present, present[1:]) if left == right
        )
        value_range = round(max(present) - min(present), 3)
        mean = statistics.fmean(present)
        stdev = statistics.pstdev(present)
        if mean == 0:
            normalized = None if stdev == 0 else _INSUFFICIENT
        else:
            normalized = round(stdev / abs(mean), 3)
        return {
            "provenance_level": ProvenanceLevel.OBSERVED.value,
            "sufficient": True,
            "status": "ok",
            "transition_count": transitions,
            "consecutive_repeat_count": consecutive_repeats,
            "range": value_range,
            "normalized_variation": normalized,
        }
