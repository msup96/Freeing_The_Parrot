"""Post-session Navarasa trajectory from stored participant turns.

Re-runs the existing Navarasa engine after lock. Results stay in memory and
are never written as NAVARASA_CLASSIFIED events.

Raw ``turn_sequence`` / ``rasa_sequence`` keep every live turn, including
engine-default Shanta (``analysis_quality`` of ``no_text`` or
``no_emotion_detected``). Session aggregates use only detected turns.
Defaulted Shanta is a quality limitation, not detected emotional evidence.
There is no separate initial-offering trajectory.
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
        raw_primaries = [row["primary_rasa"] for row in turn_rows]
        # None marks a turn that must not enter detected aggregates.
        detected_slots = [
            None if row["defaulted_primary"] else row["primary_rasa"]
            for row in turn_rows
        ]
        detected = [label for label in detected_slots if label is not None]

        return {
            "session_id": self._coordinator.session_id,
            "observation_kind": "navarasa_trajectory",
            "provenance_level": ProvenanceLevel.INTERPRETED.value,
            "method": _METHOD,
            "turn_sequence": turn_rows,
            "rasa_sequence": raw_primaries,
            "detected_sequence": detected,
            "dominant_rasa": self._dominant_rasa(detected_slots),
            "rasa_distribution": self._distribution(detected),
            "persistence": self._persistence(detected_slots),
            "transition_count": self._transition_count(detected),
            "switching_rate": self._switching_rate(detected),
            "beginning_rasa": self._endpoint(detected, 0),
            "ending_rasa": self._endpoint(detected, -1),
            "beginning_end_changed": self._beginning_end_changed(detected),
            "defaulted_shanta_turns": sum(
                1 for row in turn_rows if row["defaulted_primary"]
            ),
            "quality_limitations": self._quality_limitations(turn_rows),
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
    def _dominant_rasa(slots: list[str | None]) -> dict[str, Any]:
        """Highest detected count wins. Ties use the earliest detected turn."""
        detected = [(index, label) for index, label in enumerate(slots) if label]
        if not detected:
            return {
                "label": None,
                "count": 0,
                "tie": False,
                "status": _INSUFFICIENT,
            }
        counts: dict[str, int] = {}
        first_seen: dict[str, int] = {}
        for index, label in detected:
            counts[label] = counts.get(label, 0) + 1
            first_seen.setdefault(label, index)
        max_count = max(counts.values())
        leaders = [label for label, count in counts.items() if count == max_count]
        winner = min(leaders, key=lambda label: first_seen[label])
        return {
            "label": winner,
            "count": max_count,
            "tie": len(leaders) > 1,
            "status": "ok",
        }

    @staticmethod
    def _distribution(detected: list[str]) -> dict[str, Any]:
        if not detected:
            return {
                "counts": {},
                "status": _INSUFFICIENT,
                "provenance_level": ProvenanceLevel.INTERPRETED.value,
            }
        counts: dict[str, int] = {}
        for label in detected:
            counts[label] = counts.get(label, 0) + 1
        return {
            "counts": counts,
            "status": "ok",
            "provenance_level": ProvenanceLevel.INTERPRETED.value,
        }

    @staticmethod
    def _persistence(slots: list[str | None]) -> dict[str, Any]:
        """Longest run of the same detected Rasa. A defaulted turn breaks the run."""
        best_rasa = None
        best_run = 0
        current_rasa = None
        current_run = 0
        for label in slots:
            if label is None:
                current_rasa = None
                current_run = 0
                continue
            if label == current_rasa:
                current_run += 1
            else:
                current_rasa = label
                current_run = 1
            if current_run > best_run:
                best_run = current_run
                best_rasa = current_rasa
        if best_rasa is None:
            return {"rasa": None, "run_length": 0, "status": _INSUFFICIENT}
        return {"rasa": best_rasa, "run_length": best_run, "status": "ok"}

    @staticmethod
    def _transition_count(detected: list[str]) -> dict[str, Any]:
        if len(detected) < 2:
            return {"value": None, "status": _INSUFFICIENT}
        value = sum(
            1 for left, right in zip(detected, detected[1:]) if left != right
        )
        return {"value": value, "status": "ok"}

    @staticmethod
    def _switching_rate(detected: list[str]) -> dict[str, Any]:
        n = len(detected)
        if n < 2:
            return {"value": None, "status": _INSUFFICIENT}
        transitions = NavarasaTrajectorySynthesizer._transition_count(detected)["value"]
        return {
            "value": round(transitions / (n - 1), 3),
            "status": "ok",
        }

    @staticmethod
    def _endpoint(detected: list[str], index: int) -> dict[str, Any]:
        if not detected:
            return {"label": None, "status": _INSUFFICIENT}
        return {"label": detected[index], "status": "ok"}

    @staticmethod
    def _beginning_end_changed(detected: list[str]) -> dict[str, Any]:
        if len(detected) < 2:
            return {"value": None, "status": _INSUFFICIENT}
        return {"value": detected[0] != detected[-1], "status": "ok"}

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
