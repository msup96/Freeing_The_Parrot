"""Phase 2 tests – State machine transition validity.

Covers TEST_STRATEGY.md §2.2:
- test_ai_output_cannot_transition_state
- test_trust_window_enforcement (cross-referenced with behaviour tests)
- valid/invalid transition matrix
"""

import pytest

from ftp.session.machine import IllegalTransitionError, SessionStateMachine
from ftp.session.states import LEGAL_TRANSITIONS, SessionState


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def fresh_machine() -> SessionStateMachine:
    return SessionStateMachine()


def advance_to(machine: SessionStateMachine, *states: SessionState) -> None:
    """Drive the machine through a sequence of states."""
    for s in states:
        machine.transition(s)


# ─────────────────────────────────────────────────────────────────────────────
# Basic construction
# ─────────────────────────────────────────────────────────────────────────────

class TestConstruction:

    def test_initial_state_is_idle_standby(self):
        m = fresh_machine()
        assert m.state == SessionState.IDLE_STANDBY

    def test_custom_initial_state_is_accepted(self):
        m = SessionStateMachine(
            initial_state=SessionState.LIVE_CONVERSATION
        )
        assert m.state == SessionState.LIVE_CONVERSATION

    def test_history_starts_with_initial_state(self):
        m = fresh_machine()
        assert m.history == (SessionState.IDLE_STANDBY,)


# ─────────────────────────────────────────────────────────────────────────────
# Legal transitions
# ─────────────────────────────────────────────────────────────────────────────

class TestLegalTransitions:

    def test_idle_to_ingestion(self):
        m = fresh_machine()
        m.transition(SessionState.INPUT_INGESTION)
        assert m.state == SessionState.INPUT_INGESTION

    def test_ingestion_to_live_conversation(self):
        m = fresh_machine()
        advance_to(m, SessionState.INPUT_INGESTION, SessionState.LIVE_CONVERSATION)
        assert m.state == SessionState.LIVE_CONVERSATION

    def test_live_conversation_to_itself(self):
        """Each participant turn stays within LIVE_CONVERSATION."""
        m = fresh_machine()
        advance_to(m, SessionState.INPUT_INGESTION, SessionState.LIVE_CONVERSATION)
        for _ in range(10):
            m.transition(SessionState.LIVE_CONVERSATION)
        assert m.state == SessionState.LIVE_CONVERSATION

    def test_full_happy_path(self):
        """Drive the machine through the complete lifecycle."""
        m = fresh_machine()
        path = [
            SessionState.INPUT_INGESTION,
            SessionState.LIVE_CONVERSATION,
            SessionState.SESSION_CONCLUDED,
            SessionState.POST_SESSION_INTERPRETATION,
            SessionState.CARD_SELECTION,
            SessionState.PROFILE_REVEAL,
            SessionState.DATA_WALL_CONSENT,
            SessionState.OUTPUT_GENERATION,
            SessionState.PURGE_AND_RESET,
            SessionState.IDLE_STANDBY,
        ]
        for target in path:
            m.transition(target)
        assert m.state == SessionState.IDLE_STANDBY

    def test_intervention_path(self):
        """Health/profanity trigger → BEHAVIORAL_INTERVENTION → SESSION_CONCLUDED."""
        m = fresh_machine()
        advance_to(
            m,
            SessionState.INPUT_INGESTION,
            SessionState.LIVE_CONVERSATION,
            SessionState.BEHAVIORAL_INTERVENTION,
            SessionState.SESSION_CONCLUDED,
        )
        assert m.state == SessionState.SESSION_CONCLUDED

    def test_ingestion_timeout_resets_to_idle(self):
        """60s inactivity during ingestion returns to IDLE_STANDBY."""
        m = fresh_machine()
        m.transition(SessionState.INPUT_INGESTION)
        m.transition(SessionState.IDLE_STANDBY)
        assert m.state == SessionState.IDLE_STANDBY

    def test_history_records_all_transitions(self):
        m = fresh_machine()
        advance_to(
            m,
            SessionState.INPUT_INGESTION,
            SessionState.LIVE_CONVERSATION,
            SessionState.LIVE_CONVERSATION,
            SessionState.SESSION_CONCLUDED,
        )
        assert m.history == (
            SessionState.IDLE_STANDBY,
            SessionState.INPUT_INGESTION,
            SessionState.LIVE_CONVERSATION,
            SessionState.LIVE_CONVERSATION,
            SessionState.SESSION_CONCLUDED,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Illegal transition rejection
# ─────────────────────────────────────────────────────────────────────────────

class TestIllegalTransitions:

    def test_idle_cannot_jump_to_live_conversation(self):
        m = fresh_machine()
        with pytest.raises(IllegalTransitionError):
            m.transition(SessionState.LIVE_CONVERSATION)

    def test_idle_cannot_jump_to_concluded(self):
        m = fresh_machine()
        with pytest.raises(IllegalTransitionError):
            m.transition(SessionState.SESSION_CONCLUDED)

    def test_live_cannot_skip_to_card_selection(self):
        m = fresh_machine()
        advance_to(m, SessionState.INPUT_INGESTION, SessionState.LIVE_CONVERSATION)
        with pytest.raises(IllegalTransitionError):
            m.transition(SessionState.CARD_SELECTION)

    def test_concluded_cannot_return_to_live(self):
        m = fresh_machine()
        advance_to(
            m,
            SessionState.INPUT_INGESTION,
            SessionState.LIVE_CONVERSATION,
            SessionState.SESSION_CONCLUDED,
        )
        with pytest.raises(IllegalTransitionError):
            m.transition(SessionState.LIVE_CONVERSATION)

    def test_concluded_cannot_skip_to_card_selection(self):
        m = fresh_machine()
        advance_to(
            m,
            SessionState.INPUT_INGESTION,
            SessionState.LIVE_CONVERSATION,
            SessionState.SESSION_CONCLUDED,
        )
        with pytest.raises(IllegalTransitionError):
            m.transition(SessionState.CARD_SELECTION)

    def test_consent_cannot_go_backwards_to_card_selection(self):
        m = fresh_machine()
        advance_to(
            m,
            SessionState.INPUT_INGESTION,
            SessionState.LIVE_CONVERSATION,
            SessionState.SESSION_CONCLUDED,
            SessionState.POST_SESSION_INTERPRETATION,
            SessionState.CARD_SELECTION,
            SessionState.PROFILE_REVEAL,
            SessionState.DATA_WALL_CONSENT,
        )
        with pytest.raises(IllegalTransitionError):
            m.transition(SessionState.CARD_SELECTION)

    def test_state_unchanged_after_illegal_transition(self):
        """A rejected transition must not change the current state."""
        m = fresh_machine()
        original = m.state
        try:
            m.transition(SessionState.SESSION_CONCLUDED)
        except IllegalTransitionError:
            pass
        assert m.state == original

    def test_illegal_transition_error_message_contains_states(self):
        m = fresh_machine()
        try:
            m.transition(SessionState.OUTPUT_GENERATION)
        except IllegalTransitionError as exc:
            assert "IDLE_STANDBY" in str(exc)
            assert "OUTPUT_GENERATION" in str(exc)
        else:
            pytest.fail("Expected IllegalTransitionError was not raised.")


# ─────────────────────────────────────────────────────────────────────────────
# AI-output-cannot-drive-state invariant
# ─────────────────────────────────────────────────────────────────────────────

class TestAIOutputCannotDriveState:
    """AI content (Parrot reply strings, Gemini JSON) must never be able
    to trigger a state change.  This is tested by verifying that the
    state machine transition method is only callable with SessionState
    enum values and rejects arbitrary strings."""

    @pytest.mark.parametrize("fake_ai_output", [
        "S8_DATA_WALL_CONSENT",
        '{"next_state": "SESSION_CONCLUDED"}',
        "PURGE_AND_RESET",
        "IDLE_STANDBY",
        "live_conversation",
        "",
        "0",
    ])
    def test_string_inputs_raise_type_error(self, fake_ai_output):
        """The transition method must not accept raw strings from AI output."""
        m = fresh_machine()
        with pytest.raises((TypeError, ValueError, AttributeError, IllegalTransitionError)):
            # Passing a raw string (as might come from an AI model) must fail.
            m.transition(fake_ai_output)  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# Callback integration
# ─────────────────────────────────────────────────────────────────────────────

class TestTransitionCallback:

    def test_callback_fired_on_each_transition(self):
        calls: list[tuple[SessionState, SessionState]] = []

        def cb(prev, curr):
            calls.append((prev, curr))

        m = SessionStateMachine(on_transition=cb)
        m.transition(SessionState.INPUT_INGESTION)
        m.transition(SessionState.LIVE_CONVERSATION)

        assert calls == [
            (SessionState.IDLE_STANDBY, SessionState.INPUT_INGESTION),
            (SessionState.INPUT_INGESTION, SessionState.LIVE_CONVERSATION),
        ]

    def test_callback_not_called_on_illegal_transition(self):
        calls: list = []
        m = SessionStateMachine(on_transition=lambda p, c: calls.append((p, c)))
        try:
            m.transition(SessionState.SESSION_CONCLUDED)
        except IllegalTransitionError:
            pass
        assert calls == []

    def test_is_live_while_in_live_conversation(self):
        m = fresh_machine()
        assert not m.is_live()
        advance_to(m, SessionState.INPUT_INGESTION, SessionState.LIVE_CONVERSATION)
        assert m.is_live()

    def test_is_locked_after_conclusion(self):
        m = fresh_machine()
        advance_to(
            m,
            SessionState.INPUT_INGESTION,
            SessionState.LIVE_CONVERSATION,
            SessionState.SESSION_CONCLUDED,
        )
        assert m.is_locked()


# ─────────────────────────────────────────────────────────────────────────────
# Legal transition table completeness
# ─────────────────────────────────────────────────────────────────────────────

class TestTransitionTableCompleteness:

    def test_every_state_has_an_entry_in_legal_transitions(self):
        """Every SessionState must appear as a key in LEGAL_TRANSITIONS."""
        for state in SessionState:
            assert state in LEGAL_TRANSITIONS, (
                f"State {state.value!r} missing from LEGAL_TRANSITIONS table."
            )

    def test_all_target_states_are_valid_session_states(self):
        """Every target in LEGAL_TRANSITIONS must be a valid SessionState."""
        valid = set(SessionState)
        for source, targets in LEGAL_TRANSITIONS.items():
            for target in targets:
                assert target in valid, (
                    f"LEGAL_TRANSITIONS[{source.value!r}] contains unknown "
                    f"target {target!r}."
                )
