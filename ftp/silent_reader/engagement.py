"""Post-lock engagement evidence and a bounded interaction state.

Evidence is OBSERVED interaction measurement. The state names describe the
exchange, not a person. Behavioural eligibility is a separate instruction
boundary for a future Behaviour Director. The Parrot must not receive the
evidence or the state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ftp.events.model import ProvenanceLevel

if TYPE_CHECKING:
    from ftp.session.coordinator import SessionCoordinator

_STATES = frozenset({
    "insufficient",
    "emerging",
    "sustained",
    "high",
    "fluctuating",
    "declining",
})

_DISCLAIMER = (
    "Describes the interaction pattern, not the participant. "
    "Not a psychological claim."
)


def derive_engagement_state(signals: dict[str, Any]) -> dict[str, Any]:
    """Map measured signals to one bounded interaction state.

    Order is fixed: insufficient, fluctuating, declining, high, sustained,
    otherwise emerging.
    """
    turn_count = int(signals.get("turn_count") or 0)
    if turn_count < 2:
        return _state("insufficient", ["turn_count"])

    volatility_transitions = signals.get("length_volatility_transitions")
    length_range = signals.get("length_range")
    if (
        volatility_transitions is not None
        and int(volatility_transitions) >= 2
        and length_range is not None
        and float(length_range) > 0
    ):
        return _state("fluctuating", ["message_length_volatility"])

    length_direction = signals.get("length_direction")
    gap_direction = signals.get("gap_direction")
    if length_direction == "decreased" and gap_direction == "increased":
        return _state("declining", ["message_length", "inter_turn_gap"])

    question_rate = signals.get("question_rate")
    self_mean = signals.get("self_reference_mean")
    if (
        turn_count >= 4
        and question_rate is not None
        and float(question_rate) >= 0.5
        and self_mean is not None
        and float(self_mean) >= 1
        and length_direction != "decreased"
    ):
        return _state("high", ["question_rate", "self_reference_count", "message_length"])

    if (
        turn_count >= 3
        and length_direction in {"unchanged", "increased"}
        and gap_direction != "increased"
    ):
        return _state("sustained", ["message_length", "inter_turn_gap"])

    return _state("emerging", ["turn_count"])


def derive_behavioural_eligibility(engagement_state: str) -> dict[str, Any]:
    """Eligibility for a future Behaviour Director. Not a participant profile."""
    # Sustained/high interaction is what earns behavioural freedom. A
    # fluctuation is not evidence that the participant trusts the Parrot.
    if engagement_state in {"sustained", "high"}:
        fracture = "eligible"
        band = "moderate" if engagement_state == "high" else "low"
        recovery = "eligible"
    else:
        fracture = "ineligible"
        band = "none"
        recovery = "eligible" if engagement_state == "fluctuating" else "ineligible"
    return {
        "provenance_level": ProvenanceLevel.INTERPRETED.value,
        "fracture_eligibility": fracture,
        "fracture_intensity_band": band,
        "recovery_eligibility": recovery,
        "scope": "behaviour_director_interface",
    }


def selected_behaviour_instruction(
    *,
    behaviour: str,
    behaviour_family: str,
    behaviour_intensity: str,
) -> dict[str, str]:
    """What the Parrot may be told to perform. No engagement reasoning."""
    return {
        "behaviour": behaviour,
        "behaviour_family": behaviour_family,
        "behaviour_intensity": behaviour_intensity,
    }


def _state(name: str, basis: list[str]) -> dict[str, Any]:
    if name not in _STATES:
        raise ValueError(f"Unknown engagement state {name!r}.")
    return {
        "provenance_level": ProvenanceLevel.INTERPRETED.value,
        "state": name,
        "basis": basis,
        "disclaimer": _DISCLAIMER,
    }


class EngagementSynthesizer:
    """Deterministic engagement synthesis from existing trajectory measurements."""

    def __init__(self, coordinator: SessionCoordinator) -> None:
        self._coordinator = coordinator

    def synthesize(self) -> dict[str, Any]:
        from ftp.silent_reader.linguistic import LinguisticTrajectorySynthesizer
        from ftp.silent_reader.trajectories import TemporalTrajectorySynthesizer

        temporal = TemporalTrajectorySynthesizer(self._coordinator).synthesize()
        linguistic = LinguisticTrajectorySynthesizer(self._coordinator).synthesize()
        evidence = self._evidence(temporal, linguistic)
        state = derive_engagement_state(evidence["signals"])
        eligibility = derive_behavioural_eligibility(state["state"])
        return {
            "session_id": self._coordinator.session_id,
            "observation_kind": "engagement_trajectory",
            "evidence": evidence,
            "engagement_state": state,
            "behavioural_eligibility": eligibility,
        }

    @staticmethod
    def _evidence(temporal: dict[str, Any], linguistic: dict[str, Any]) -> dict[str, Any]:
        turns = temporal["turn_sequence"]
        length = temporal["message_length_trajectory"]
        latency = temporal["response_latency_trajectory"]
        gap = temporal["inter_turn_gap_trajectory"]
        length_vol = temporal["volatility"]["message_length"]
        question = linguistic["question_rate"]
        self_ref = linguistic["self_reference_trajectory"]
        duration = None
        if len(turns) >= 2:
            from datetime import datetime

            start = datetime.fromisoformat(turns[0]["timestamp"])
            end = datetime.fromisoformat(turns[-1]["timestamp"])
            duration = round(max(0.0, (end - start).total_seconds()), 3)

        signals = {
            "turn_count": len(turns),
            "length_direction": length["change"]["direction"],
            "length_volatility_transitions": length_vol.get("transition_count"),
            "length_range": length_vol.get("range"),
            "gap_direction": gap["change"]["direction"],
            "question_rate": question.get("value"),
            "self_reference_mean": self_ref.get("mean"),
        }
        source_ids: list[str] = []
        for turn in turns:
            event_id = turn["event_id"]
            if event_id not in source_ids:
                source_ids.append(event_id)
        return {
            "provenance_level": ProvenanceLevel.OBSERVED.value,
            "status": "ok" if turns else "insufficient",
            "turn_count": len(turns),
            "message_length": {
                "first": length.get("first"),
                "final": length.get("final"),
                "mean": length.get("mean"),
                "direction": length["change"]["direction"],
                "status": length["status"],
            },
            "response_latency": {
                "first": latency.get("first"),
                "final": latency.get("final"),
                "mean": latency.get("mean"),
                "status": latency["status"],
            },
            "inter_turn_gap": {
                "first": gap.get("first"),
                "final": gap.get("final"),
                "mean": gap.get("mean"),
                "status": gap["status"],
            },
            "question_rate": question.get("value"),
            "self_reference_mean": self_ref.get("mean"),
            "repetition_count": temporal["repetition"]["repetition_count"],
            "interaction_duration_seconds": duration,
            "source_event_ids": source_ids,
            "signals": signals,
        }


def build_live_engagement_snapshot(
    coordinator: SessionCoordinator,
    *,
    current_turn_text: str = "",
) -> dict[str, Any]:
    """Coordinator-private engagement view during ``LIVE_CONVERSATION``.

    Uses the same synthesis path as post-lock ``synthesize_engagement()``,
    without writing to the event store or exposing data to the Parrot.
    """
    from ftp.session.states import SessionState

    if coordinator.machine.is_locked():
        raise ValueError(
            "Live engagement snapshot is only available before session lock."
        )
    if coordinator.state != SessionState.LIVE_CONVERSATION:
        raise ValueError(
            "Live engagement snapshot is only available during LIVE_CONVERSATION."
        )
    payload = EngagementSynthesizer(coordinator).synthesize()
    from ftp.parrot.continuity import dialogue_turns_from_coordinator
    from ftp.silent_reader.live_relationship import derive_live_relationship_signals

    turns = dialogue_turns_from_coordinator(coordinator)
    relationship = derive_live_relationship_signals(
        turns,
        current_text=current_turn_text,
    )
    # Live relationship signals are an internal Director input. They remain
    # outside Parrot context and are never recorded as a participant profile.
    return {
        **payload,
        "observation_kind": "live_engagement_snapshot",
        "relationship": relationship,
    }
