"""FTP 2.0 Behaviour Director — selects live Parrot behaviour (Pass 4).

Chooses structured instructions only. Does not generate natural language.
"""

from __future__ import annotations

import random
from typing import Any, Mapping, MutableMapping

from ftp.parrot.continuity import continuity_index_from_coordinator
from ftp.parrot.director_state import DirectorState
from ftp.parrot.engine import BEHAVIOUR_NAMES
from ftp.session.coordinator import SessionCoordinator

FRACTURE_POOL = frozenset({
    "absurd",
    "memory_loss",
    "system_glitch",
    "help_me",
    "mixed",
    "banana",
    "roast",
})

UNSTABLE_POOL = frozenset({
    "absurd",
    "memory_loss",
    "system_glitch",
    "help_me",
    "roast",
    "mixed",
    "mirroring",
    "banana",
})

COHERENT_POOL = ("understanding", "mirroring")

DIRECTIVE_VALUES = frozenset({
    "familiarity",
    "reciprocity",
    "curiosity",
    "expectation",
    "repair",
})

PROHIBITED_OUTPUT_LABELS = frozenset({
    "engaged",
    "attached",
    "lonely",
    "vulnerability",
    "dependency",
    "personality",
    "engagement_state",
    "engagement_score",
    "evidence_bundle",
    "candidate_inference",
    "reading_profile",
    "psychological",
})

BEHAVIOUR_FAMILY = {
    "understanding": "understanding",
    "mirroring": "mirroring",
    "roast": "roast",
    "absurd": "absurd",
    "memory_loss": "memory_loss",
    "system_glitch": "system_glitch",
    "help_me": "help_me",
    "mixed": "mixed",
    "banana": "banana",
}


class BehaviourDirector:
    """Deterministic live behaviour selection for one coordinator session."""

    @classmethod
    def decide(
        cls,
        coordinator: SessionCoordinator,
        *,
        turn_index: int,
        turn_text: str,
        navarasa_result: Mapping[str, Any] | None = None,
        rng: random.Random | None = None,
    ) -> dict[str, Any]:
        del turn_text  # reserved for future realizer; not used for inference here
        _validate_navarasa_input(navarasa_result or {})

        snapshot = coordinator.live_engagement_snapshot()
        continuity = continuity_index_from_coordinator(coordinator)
        eligibility = snapshot["behavioural_eligibility"]
        state = coordinator.director_state
        last = state.last_behaviour

        roll = rng.random if rng is not None else random.random

        if state.understanding_turns < state.trust_turns:
            behaviour = "understanding"
            intensity = "steady"
            selection_mode = "trust_window"
            # An occasional mild echo even inside the trust window (human-plausible, not chaotic).
            if turn_index >= 2 and state.early_slip_chance > 0 and roll() < state.early_slip_chance:
                behaviour = "mirroring"
        else:
            behaviour, intensity, selection_mode = cls._select_post_trust(
                substantive_turns=turn_index,
                last_behaviour=last,
                eligibility=eligibility,
                roll=roll,
                state=state,
            )

        directive, directive_basis = cls._select_directive(
            continuity,
            behaviour=behaviour,
            roll=roll,
        )

        cls._commit_state(state, behaviour, selection_mode=selection_mode)

        instruction = {
            "behaviour": behaviour,
            "behaviour_family": BEHAVIOUR_FAMILY.get(behaviour, behaviour),
            "behaviour_intensity": intensity,
            "directive": directive,
            "directive_basis": directive_basis,
            "selection_mode": selection_mode,
        }
        _validate_instruction(instruction)
        return instruction

    @classmethod
    def record_implicit_understanding(cls, coordinator: SessionCoordinator) -> None:
        """Turn-1 legacy path: behaviour is understanding without full decide()."""
        cls._commit_state(
            coordinator.director_state,
            "understanding",
            selection_mode="trust_window",
        )

    @classmethod
    def _select_post_trust(
        cls,
        *,
        substantive_turns: int,
        last_behaviour: str | None,
        eligibility: Mapping[str, Any],
        roll,
        state: DirectorState | None = None,
    ) -> tuple[str, str, str]:
        if eligibility.get("recovery_eligibility") == "eligible" and roll() < 0.55:
            behaviour = cls._pick_without_repeat(list(COHERENT_POOL), last_behaviour, roll)
            return behaviour, "steady", "recovery"

        if (
            eligibility.get("fracture_eligibility") == "eligible"
            and roll() < 0.5
        ):
            band = eligibility.get("fracture_intensity_band") or "moderate"
            intensity = "moderate" if band == "moderate" else "low"
            pool = sorted(FRACTURE_POOL)
            behaviour = cls._pick_without_repeat(pool, last_behaviour, roll)
            return behaviour, intensity, "fracture"

        base = state.instability_base if state else 0.35
        ramp = state.instability_ramp if state else 0.08
        cap = state.instability_cap if state else 0.75
        jitter = state.instability_jitter if state else 0.0
        trust = state.trust_turns if state else 3
        instability = base + (max(0, substantive_turns - (trust + 1)) * ramp)
        if jitter > 0:
            # Not monotonic: the machine can settle again, or slip early.
            instability += (roll() * 2 - 1) * jitter
        instability = min(cap, max(0.05, instability))
        if roll() >= instability:
            return "understanding", "steady", "understanding"

        pool = sorted(UNSTABLE_POOL)
        behaviour = cls._pick_without_repeat(pool, last_behaviour, roll)
        return behaviour, "moderate", "unstable"

    @staticmethod
    def _pick_without_repeat(
        choices: list[str],
        last: str | None,
        roll,
    ) -> str:
        filtered = [item for item in choices if item != last]
        if not filtered:
            filtered = choices
        index = int(roll() * len(filtered))
        if index >= len(filtered):
            index = len(filtered) - 1
        return filtered[index]

    @staticmethod
    def _commit_state(
        state: DirectorState,
        behaviour: str,
        *,
        selection_mode: str,
    ) -> None:
        if behaviour not in BEHAVIOUR_NAMES:
            raise ValueError(f"Unknown behaviour {behaviour!r}.")
        if state.understanding_turns < state.trust_turns and behaviour == "understanding":
            state.understanding_turns += 1
        if selection_mode in {"unstable", "fracture"}:
            state.chaos_count += 1
        state.last_behaviour = behaviour
        state.behaviour_history.append(behaviour)
        state.behaviour_history = state.behaviour_history[-12:]

    @staticmethod
    def _select_directive(
        continuity: Mapping[str, Any],
        *,
        behaviour: str,
        roll,
    ) -> tuple[str | None, list[dict[str, Any]]]:
        del behaviour
        refs = list(continuity.get("continuity_refs") or [])

        if continuity.get("previous_fracture") and refs:
            return "repair", refs[:2]

        if continuity.get("open_thread") and refs:
            choice = "expectation" if roll() < 0.5 else "curiosity"
            return choice, refs[:2]

        if continuity.get("prior_question") and refs:
            choice = "curiosity" if roll() < 0.5 else "expectation"
            return choice, refs[:1]

        if continuity.get("repeated_phrase") and refs:
            choice = "reciprocity" if roll() < 0.5 else "familiarity"
            return choice, refs[:2]

        if continuity.get("topic_overlap") and refs:
            return "familiarity", refs[:1]

        return None, []


def sync_legacy_session_behaviour_counters(
    session: MutableMapping[str, Any],
    coordinator: SessionCoordinator,
) -> None:
    """Mirror DirectorState into legacy Flask session (read-only compatibility)."""
    state = coordinator.director_state
    session["understanding_turns"] = state.understanding_turns
    session["chaos_count"] = state.chaos_count
    session["last_behaviour"] = state.last_behaviour
    session["behaviour_history"] = list(state.behaviour_history)


def _validate_navarasa_input(navarasa: Mapping[str, Any]) -> None:
    forbidden = {
        "engagement_state",
        "engagement_score",
        "behavioural_eligibility",
        "evidence_bundle",
        "candidate_inference",
        "reading_profile",
        "hidden_provenance",
        "participant_profile",
    }
    for key in navarasa:
        if key in forbidden:
            raise ValueError(f"Forbidden director input key {key!r}.")


def _validate_instruction(instruction: Mapping[str, Any]) -> None:
    for key in instruction:
        if str(key).lower() in PROHIBITED_OUTPUT_LABELS:
            raise ValueError(f"Forbidden director output key {key!r}.")
    directive = instruction.get("directive")
    if directive is not None and directive not in DIRECTIVE_VALUES:
        raise ValueError(f"Unknown directive {directive!r}.")
    for key in ("behaviour", "behaviour_family", "behaviour_intensity"):
        value = instruction.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Instruction field {key!r} must be non-empty text.")
        if " " in value or "\n" in value:
            raise ValueError("Director must not emit prose in instruction fields.")
