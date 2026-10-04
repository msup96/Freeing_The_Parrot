"""Session-level linguistic trajectories from stored participant text.

Describes observable surface patterns only. Stays below INFERRED.
"""

from __future__ import annotations

import re
import statistics
from typing import TYPE_CHECKING, Any

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel

if TYPE_CHECKING:
    from ftp.session.coordinator import SessionCoordinator

_INSUFFICIENT = "insufficient"
_MISSING = "missing"
_METHOD = "deterministic_surface_linguistics_v1"

_SELF_REF_PATTERN = re.compile(r"\b(I|me|my|myself|mine)\b", re.IGNORECASE)


class LinguisticTrajectorySynthesizer:
    """Deterministic linguistic synthesis. The Parrot never reads this output."""

    def __init__(self, coordinator: SessionCoordinator) -> None:
        self._coordinator = coordinator

    def synthesize(self) -> dict:
        events = self._coordinator.store.all_events()
        turns = self._build_turn_sequence(events)
        question_flags = [turn["utterance_is_question"] for turn in turns]
        self_ref_values = [turn["self_reference_count"] for turn in turns]
        token_values = [turn["token_count"] for turn in turns]
        ttr_values = [turn["type_token_ratio"] for turn in turns]
        source_ids = [turn["event_id"] for turn in turns]

        return {
            "session_id": self._coordinator.session_id,
            "observation_kind": "linguistic_trajectory",
            "provenance_level": ProvenanceLevel.INTERPRETED.value,
            "method": _METHOD,
            "turn_sequence": turns,
            "message_length_trajectory": self._numeric_trajectory(
                [turn["message_length"] for turn in turns],
                source_ids,
                unit="characters",
            ),
            "question_rate": self._question_rate(question_flags, source_ids),
            "self_reference_trajectory": self._numeric_trajectory(
                self_ref_values,
                source_ids,
                unit="count",
            ),
            "token_count_trajectory": self._numeric_trajectory(
                token_values,
                source_ids,
                unit="tokens",
            ),
            "type_token_ratio_trajectory": self._numeric_trajectory(
                ttr_values,
                source_ids,
                unit="ratio",
                method="whitespace_ttr",
            ),
        }

    def _build_turn_sequence(
        self, events: tuple[InteractionEvent, ...]
    ) -> list[dict[str, Any]]:
        parrot_turns = [
            event
            for event in events
            if event.event_type == EventType.PARROT_TURN_GENERATED
        ]
        derived_by_turn = self._index_derived_features(events)
        sequence: list[dict[str, Any]] = []

        for index, parrot_event in enumerate(parrot_turns):
            turn_index = int(parrot_event.payload.get("turn_index", index))
            user_text = str(parrot_event.payload.get("user_text") or "")
            derived = derived_by_turn.get(turn_index, {})

            message_length = self._first_present_number(
                derived.get("message_length"),
                len(user_text),
            )
            is_question = derived.get("utterance_is_question")
            if is_question is None:
                is_question = user_text.strip().endswith("?")

            self_refs = derived.get("self_reference_count")
            if self_refs is None:
                self_refs = len(_SELF_REF_PATTERN.findall(user_text))

            tokens = user_text.split()
            token_count = len(tokens)
            if token_count == 0:
                ttr: float | None = None
            else:
                unique = {token.lower() for token in tokens}
                ttr = round(len(unique) / token_count, 3)

            sequence.append(
                {
                    "turn_index": turn_index,
                    "event_id": parrot_event.event_id,
                    "source_event_ids": [parrot_event.event_id],
                    "message_length": int(message_length),
                    "utterance_is_question": bool(is_question),
                    "self_reference_count": int(self_refs),
                    "token_count": token_count,
                    "type_token_ratio": ttr,
                    "type_token_ratio_method": "whitespace_ttr",
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
        return indexed

    @staticmethod
    def _first_present_number(preferred: Any, fallback: int) -> int:
        if preferred is None:
            return fallback
        return int(preferred)

    def _question_rate(
        self,
        question_flags: list[bool],
        source_event_ids: list[str],
    ) -> dict[str, Any]:
        turn_count = len(question_flags)
        if turn_count == 0:
            return {
                "provenance_level": ProvenanceLevel.OBSERVED.value,
                "value": None,
                "question_turns": 0,
                "turn_count": 0,
                "status": _INSUFFICIENT,
                "source_event_ids": [],
            }
        question_turns = sum(1 for flag in question_flags if flag)
        return {
            "provenance_level": ProvenanceLevel.OBSERVED.value,
            "value": round(question_turns / turn_count, 3),
            "question_turns": question_turns,
            "turn_count": turn_count,
            "status": "ok",
            "source_event_ids": list(source_event_ids),
        }

    def _numeric_trajectory(
        self,
        values: list[float | int | None],
        source_event_ids: list[str],
        *,
        unit: str,
        method: str | None = None,
    ) -> dict[str, Any]:
        present = [float(value) for value in values if value is not None]
        unique_ids: list[str] = []
        for event_id in source_event_ids:
            if event_id not in unique_ids:
                unique_ids.append(event_id)

        payload: dict[str, Any] = {
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
        if method is not None:
            payload["method"] = method

        if not present:
            return payload

        first = present[0]
        final = present[-1]
        change_status = "ok" if len(present) >= 2 else _INSUFFICIENT
        absolute = round(final - first, 3) if len(present) >= 2 else None
        payload.update(
            {
                "sufficient": len(present) >= 1,
                "status": "ok",
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
            }
        )
        return payload

    @staticmethod
    def _direction(first: float, final: float, count: int) -> str:
        if count < 2:
            return _INSUFFICIENT
        if final > first:
            return "increased"
        if final < first:
            return "decreased"
        return "unchanged"
