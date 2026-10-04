"""Post-session Navarasa trajectory from stored participant turns.

Re-runs the existing Navarasa engine after lock. Results stay in memory and
are never written as NAVARASA_CLASSIFIED events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from navarasa_engine import analyse_text

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel

if TYPE_CHECKING:
    from ftp.session.coordinator import SessionCoordinator

_INSUFFICIENT = "insufficient"
_METHOD = "navarasa_engine.analyse_text"
_DEFAULT_QUALITIES = frozenset({"no_text", "no_emotion_detected"})


class NavarasaTrajectorySynthesizer:
    """Deterministic Navarasa trajectory synthesis."""

    def __init__(self, coordinator: SessionCoordinator) -> None:
        self._coordinator = coordinator

    def synthesize(self) -> dict:
        events = self._coordinator.store.all_events()
        turn_rows = self._build_turn_sequence(events)
        primaries = [row["primary_rasa"] for row in turn_rows]
        n = len(primaries)

        return {
            "session_id": self._coordinator.session_id,
            "observation_kind": "navarasa_trajectory",
            "provenance_level": ProvenanceLevel.INTERPRETED.value,
            "method": _METHOD,
            "turn_sequence": turn_rows,
            "rasa_sequence": primaries,
            "dominant_rasa": self._dominant_rasa(primaries),
            "rasa_distribution": self._distribution(primaries),
            "persistence": self._persistence(primaries),
            "transition_count": self._transition_count(primaries),
            "switching_rate": self._switching_rate(primaries),
            "beginning_rasa": primaries[0] if n else None,
            "ending_rasa": primaries[-1] if n else None,
            "beginning_end_changed": self._beginning_end_changed(primaries),
            "defaulted_shanta_turns": sum(
                1 for row in turn_rows if row["defaulted_primary"]
            ),
            "quality_limitations": self._quality_limitations(turn_rows),
            "initial_offering": self._initial_offering(events),
        }

    def _build_turn_sequence(
        self, events: tuple[InteractionEvent, ...]
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, parrot_event in enumerate(
            event
            for event in events
            if event.event_type == EventType.PARROT_TURN_GENERATED
        ):
            turn_index = int(parrot_event.payload.get("turn_index", index))
            user_text = str(parrot_event.payload.get("user_text") or "")
            analysis = analyse_text(user_text)
            quality = str(analysis.get("analysis_quality") or "")
            defaulted = quality in _DEFAULT_QUALITIES
            rows.append(
                {
                    "turn_index": turn_index,
                    "event_id": parrot_event.event_id,
                    "source_event_ids": [parrot_event.event_id],
                    "primary_rasa": analysis.get("primary_rasa"),
                    "rasa_scores": analysis.get("rasa_scores") or {},
                    "analysis_quality": quality,
                    "defaulted_primary": defaulted,
                    "emotional_words": analysis.get("emotional_words") or [],
                    "sentiment": analysis.get("sentiment") or {},
                    "method": _METHOD,
                }
            )
        return rows

    @staticmethod
    def _initial_offering(
        events: tuple[InteractionEvent, ...],
    ) -> dict[str, Any] | None:
        offering_events = [
            event
            for event in events
            if event.event_type == EventType.NAVARASA_CLASSIFIED
        ]
        if not offering_events:
            return None
        event = offering_events[0]
        payload = event.payload
        quality = str(payload.get("analysis_quality") or "")
        return {
            "event_id": event.event_id,
            "source_event_ids": [event.event_id],
            "primary_rasa": payload.get("primary_rasa"),
            "rasa_scores": payload.get("rasa_scores") or {},
            "analysis_quality": quality,
            "defaulted_primary": quality in _DEFAULT_QUALITIES,
            "text": payload.get("text"),
            "method": "stored_navarasa_classified_event",
        }

    @staticmethod
    def _dominant_rasa(primaries: list[str]) -> dict[str, Any]:
        if not primaries:
            return {
                "label": None,
                "count": 0,
                "tie": False,
                "status": _INSUFFICIENT,
            }
        counts: dict[str, int] = {}
        first_seen: dict[str, int] = {}
        for index, label in enumerate(primaries):
            counts[label] = counts.get(label, 0) + 1
            first_seen.setdefault(label, index)
        max_count = max(counts.values())
        leaders = [label for label, count in counts.items() if count == max_count]
        # Ties resolve by earliest occurrence in the conversational sequence.
        winner = min(leaders, key=lambda label: first_seen[label])
        return {
            "label": winner,
            "count": max_count,
            "tie": len(leaders) > 1,
            "status": "ok",
        }

    @staticmethod
    def _distribution(primaries: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for label in primaries:
            counts[label] = counts.get(label, 0) + 1
        return counts

    @staticmethod
    def _persistence(primaries: list[str]) -> dict[str, Any]:
        if not primaries:
            return {"rasa": None, "run_length": 0, "status": _INSUFFICIENT}
        best_rasa = primaries[0]
        best_run = 1
        current_rasa = primaries[0]
        current_run = 1
        for label in primaries[1:]:
            if label == current_rasa:
                current_run += 1
            else:
                current_rasa = label
                current_run = 1
            if current_run > best_run:
                best_run = current_run
                best_rasa = current_rasa
        return {"rasa": best_rasa, "run_length": best_run, "status": "ok"}

    @staticmethod
    def _transition_count(primaries: list[str]) -> int:
        return sum(
            1 for left, right in zip(primaries, primaries[1:]) if left != right
        )

    @staticmethod
    def _switching_rate(primaries: list[str]) -> dict[str, Any]:
        n = len(primaries)
        if n < 2:
            return {"value": None, "status": _INSUFFICIENT}
        transitions = NavarasaTrajectorySynthesizer._transition_count(primaries)
        return {
            "value": round(transitions / (n - 1), 3),
            "status": "ok",
        }

    @staticmethod
    def _beginning_end_changed(primaries: list[str]) -> bool | None:
        if len(primaries) < 2:
            return None
        return primaries[0] != primaries[-1]

    @staticmethod
    def _quality_limitations(turn_rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not turn_rows:
            return {
                "defaulted_shanta_turns": 0,
                "status": _INSUFFICIENT,
            }
        defaulted = sum(1 for row in turn_rows if row["defaulted_primary"])
        return {
            "defaulted_shanta_turns": defaulted,
            "status": "ok",
        }
