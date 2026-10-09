"""FTP 2.0 Behaviour Director — selects live Parrot behaviour (Pass 4).

Chooses structured instructions only. Does not generate natural language.
"""

from __future__ import annotations

import random
from typing import Any, Mapping, MutableMapping

from ftp.parrot.continuity import continuity_index_from_coordinator, dialogue_turns_from_coordinator
from ftp.parrot.conversation_logic import ALL_MOVES, choose_conversation_plan
from ftp.parrot.director_state import DirectorState
from ftp.parrot.engine import BEHAVIOUR_NAMES
from ftp.session.coordinator import SessionCoordinator

FRACTURE_POOL = frozenset({
    "absurd",
    "memory_loss",
    "system_glitch",
    "help_me",
    "banana",
    "roast",
    "binary",
    "sarcasm",
    "judgment",
    "stupidity",
    "irrelevant",
})

UNSTABLE_POOL = frozenset({
    "absurd",
    "memory_loss",
    "system_glitch",
    "help_me",
    "roast",
    "mirroring",
    "banana",
    "binary",
    "sarcasm",
    "judgment",
    "stupidity",
    "irrelevant",
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
    "binary": "binary",
    "sarcasm": "sarcasm",
    "judgment": "judgment",
    "stupidity": "stupidity",
    "irrelevant": "irrelevant",
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
        _validate_navarasa_input(navarasa_result or {})

        snapshot = coordinator.live_engagement_snapshot(
            current_turn_text=turn_text,
        )
        relationship = snapshot.get("relationship") or {}
        state = coordinator.director_state
        state.observe_relationship(relationship, turn_index=turn_index)

        continuity = continuity_index_from_coordinator(coordinator)
        roll = rng.random if rng is not None else random.random
        last = state.last_behaviour

        # The participant's current message always has first right of response.
        # Correction, confusion, or disengagement can therefore suppress a
        # behavioural risk even when trust is already high.
        if relationship.get("disengagement"):
            behaviour, intensity, selection_mode = "understanding", "steady", "participant_disengaged"
        elif relationship.get("correction"):
            behaviour, intensity, selection_mode = "understanding", "steady", "repair_priority"
        elif relationship.get("previous_fracture"):
            # A rupture is followed by a clean chance to continue. The
            # participant's decision to stay is what increases future risk.
            behaviour = cls._pick_without_repeat(
                list(COHERENT_POOL), last, roll
            )
            intensity, selection_mode = "steady", "recovery"
        elif state.trust_score < 0.62 or turn_index <= state.trust_turns:
            behaviour, intensity, selection_mode = "understanding", "steady", "trust_building"
        else:
            # Restore the original FTP experience contract: after the first
            # three apparent-understanding turns, chaos is genuinely possible
            # even when the newer relationship estimator remains conservative.
            # Corrections, disengagement, and one-turn recovery still take priority.
            instability = min(
                state.instability_cap,
                state.instability_base
                + max(0, turn_index - state.trust_turns - 1) * state.instability_ramp,
            )
            if roll() < instability:
                intensity = state.glitch_intensity()
                # The older trust score may never cross its threshold in a
                # normal session. Turn progression therefore also escalates
                # the available vocabulary without exposing relationship data.
                if turn_index >= 9 or state.chaos_count >= 2:
                    intensity = "high"
                elif turn_index >= 5:
                    intensity = "moderate"
                pool = cls._risk_pool(intensity)
                behaviour = cls._pick_without_repeat(pool, last, roll)
                selection_mode = "relationship_risk"
            else:
                behaviour, intensity, selection_mode = (
                    "understanding", "steady", "understanding"
                )

        directive, directive_basis = cls._select_directive(
            continuity,
            behaviour=behaviour,
            relationship=relationship,
            current_text=turn_text,
            state=state,
            roll=roll,
        )

        if directive and directive_basis:
            state.last_directive = directive
            state.last_directive_excerpt = str(
                directive_basis[0].get("excerpt") or ""
            )

        conversation_plan = cls.plan_conversation(
            coordinator,
            turn_text=turn_text,
            turn_index=turn_index,
            behaviour=behaviour,
            roll=roll(),
        )

        cls._commit_state(state, behaviour, selection_mode=selection_mode)

        instruction = {
            "behaviour": behaviour,
            "behaviour_family": BEHAVIOUR_FAMILY.get(behaviour, behaviour),
            "behaviour_intensity": intensity,
            "directive": directive,
            "directive_basis": directive_basis,
            "selection_mode": selection_mode,
            "conversation_move": conversation_plan["conversation_move"],
            "question_hint": conversation_plan.get("question_hint"),
        }
        _validate_instruction(instruction)
        return instruction

    @classmethod
    def plan_conversation(
        cls,
        coordinator: SessionCoordinator,
        *,
        turn_text: str,
        turn_index: int,
        behaviour: str,
        roll: float = 0.0,
    ) -> dict[str, Any]:
        state = coordinator.director_state
        turns = dialogue_turns_from_coordinator(coordinator)
        recent_replies = [turn.parrot_reply for turn in turns[-3:] if turn.parrot_reply]
        plan = choose_conversation_plan(
            turn_text,
            turn_index=turn_index,
            behaviour=behaviour,
            last_move=state.conversation_move_history[-1] if state.conversation_move_history else None,
            recent_questions=state.question_history[-8:],
            recent_replies=recent_replies,
            roll=roll,
        )
        move = str(plan["conversation_move"])
        if move not in ALL_MOVES:
            raise ValueError(f"Unknown conversational move {move!r}.")
        state.conversation_move_history.append(move)
        state.conversation_move_history = state.conversation_move_history[-8:]
        hint = plan.get("question_hint")
        if hint:
            state.question_history.append(str(hint))
            state.question_history = state.question_history[-8:]
        return plan

    @classmethod
    def record_implicit_understanding(cls, coordinator: SessionCoordinator) -> None:
        """Turn-1 legacy path: behaviour is understanding without full decide()."""
        cls._commit_state(
            coordinator.director_state,
            "understanding",
            selection_mode="trust_window",
        )

    @staticmethod
    def _risk_pool(intensity: str) -> list[str]:
        low = [
            "absurd",
            "memory_loss",
            "system_glitch",
            "help_me",
            "irrelevant",
            "binary",
            "banana",
            "sarcasm",
        ]
        moderate = low + ["stupidity", "roast"]
        high = moderate + ["judgment"]
        if intensity == "high":
            return high
        if intensity == "moderate":
            return moderate
        return low

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
        if selection_mode in {"unstable", "fracture", "relationship_risk"}:
            state.chaos_count += 1
        state.last_behaviour = behaviour
        state.behaviour_history.append(behaviour)
        state.behaviour_history = state.behaviour_history[-12:]

    @staticmethod
    def _select_directive(
        continuity: Mapping[str, Any],
        *,
        behaviour: str,
        relationship: Mapping[str, Any],
        current_text: str,
        state: DirectorState,
        roll,
    ) -> tuple[str | None, list[dict[str, Any]]]:
        refs = list(continuity.get("continuity_refs") or [])

        if behaviour in FRACTURE_POOL:
            return None, []

        # Current-message correction/disengagement always outranks continuity.
        if relationship.get("correction") or relationship.get("disengagement"):
            return None, []

        # Very short acknowledgements are not invitations to retrieve an old
        # conversational thread. Respond to the acknowledgement itself.
        current_words = {
            word.lower()
            for word in current_text.split()
            if len(word.strip(".,!?;:()[]{}'\"")) >= 5
        }
        if len(current_words) < 3:
            return None, []

        # A continuity reference must have a concrete lexical foothold in the
        # current turn. This prevents a stale question from becoming the topic
        # merely because it exists somewhere in the session history.
        relevant: list[dict[str, Any]] = []
        for ref in refs:
            excerpt_words = {
                word.lower().strip(".,!?;:()[]{}'\"")
                for word in str(ref.get("excerpt") or "").split()
                if len(word.strip(".,!?;:()[]{}'\"")) >= 5
            }
            if current_words & excerpt_words:
                relevant.append(ref)

        if not relevant:
            return None, []

        if state.last_directive and state.last_directive_excerpt:
            relevant = [
                ref for ref in relevant
                if not (
                    state.last_directive == "familiarity"
                    and str(ref.get("excerpt") or "") == state.last_directive_excerpt
                )
            ]
            if not relevant:
                return None, []

        if continuity.get("previous_fracture") and relevant:
            return "repair", relevant[:1]

        if continuity.get("open_thread") and relevant:
            choice = "expectation" if roll() < 0.5 else "curiosity"
            return choice, relevant[:1]

        if continuity.get("prior_question") and relevant:
            choice = "curiosity" if roll() < 0.5 else "expectation"
            return choice, relevant[:1]

        if continuity.get("repeated_phrase") and relevant:
            choice = "reciprocity" if roll() < 0.5 else "familiarity"
            return choice, relevant[:1]

        if continuity.get("topic_overlap") and relevant:
            return "familiarity", relevant[:1]

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
    move = instruction.get("conversation_move")
    if move not in ALL_MOVES:
        raise ValueError(f"Unknown conversational move {move!r}.")
    question_hint = instruction.get("question_hint")
    if question_hint is not None and (not isinstance(question_hint, str) or len(question_hint) > 260):
        raise ValueError("Question hint must be short text or None.")
    for key in ("behaviour", "behaviour_family", "behaviour_intensity"):
        value = instruction.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Instruction field {key!r} must be non-empty text.")
        if " " in value or "\n" in value:
            raise ValueError("Director must not emit prose in instruction fields.")
