"""Pass 1 — DirectorState session persistence on SessionCoordinator."""

import pytest

from ftp.parrot.engine import choose_behaviour
from ftp.session.coordinator import SessionCoordinator, _PARROT_FORBIDDEN_KEYS
from ftp.session.states import SessionState

_CLEAN_NAVARASA = {
    "primary_rasa": "Shanta",
    "rasa_scores": {"Shanta": 1.0},
    "sentiment": {"compound": 0.0},
}


def _live_coordinator() -> SessionCoordinator:
    c = SessionCoordinator()
    c.start()
    c.advance(SessionState.LIVE_CONVERSATION)
    return c


class TestDirectorStatePersistence:
    def test_new_session_starts_with_empty_director_state(self):
        c = _live_coordinator()
        assert c.director_state.understanding_turns == 0
        assert c.director_state.chaos_count == 0
        assert c.director_state.last_behaviour is None
        assert c.director_state.behaviour_history == []

    def test_director_state_persists_across_live_turns(self):
        c = _live_coordinator()
        for turn_index in (1, 2, 3, 4):
            ctx = c.build_parrot_context("hello", turn_index, _CLEAN_NAVARASA)
            behaviour = choose_behaviour(ctx["parrot_session"])
            c.apply_parrot_session_state(ctx["parrot_session"])
            assert c.director_state.last_behaviour == behaviour
        assert len(c.director_state.behaviour_history) >= 3
        assert c.director_state.understanding_turns == 3

    def test_build_parrot_context_does_not_reset_director_state(self):
        c = _live_coordinator()
        ctx = c.build_parrot_context("one", 1, _CLEAN_NAVARASA)
        choose_behaviour(ctx["parrot_session"])
        c.apply_parrot_session_state(ctx["parrot_session"])
        c.build_parrot_context("two", 2, _CLEAN_NAVARASA)
        assert c.director_state.understanding_turns == 2
        assert c.director_state.last_behaviour is not None
        assert c.director_state.behaviour_history

    def test_behaviour_history_survives_repeated_context_builds(self):
        c = _live_coordinator()
        ctx = c.build_parrot_context("one", 4, _CLEAN_NAVARASA)
        choose_behaviour(ctx["parrot_session"])
        c.apply_parrot_session_state(ctx["parrot_session"])
        history_after_one = list(c.director_state.behaviour_history)
        c.build_parrot_context("two", 4, _CLEAN_NAVARASA)
        assert c.director_state.behaviour_history == history_after_one

    def test_purge_transition_clears_director_state(self):
        c = _live_coordinator()
        ctx = c.build_parrot_context("one", 1, _CLEAN_NAVARASA)
        choose_behaviour(ctx["parrot_session"])
        c.apply_parrot_session_state(ctx["parrot_session"])
        assert c.director_state.behaviour_history
        c._on_state_change(
            SessionState.OUTPUT_GENERATION,
            SessionState.PURGE_AND_RESET,
        )
        assert c.director_state.understanding_turns == 0
        assert c.director_state.behaviour_history == []

    def test_reset_director_state_clears_without_new_coordinator(self):
        c = _live_coordinator()
        ctx = c.build_parrot_context("one", 2, _CLEAN_NAVARASA)
        choose_behaviour(ctx["parrot_session"])
        c.apply_parrot_session_state(ctx["parrot_session"])
        c.reset_director_state()
        assert c.director_state.last_behaviour is None
        assert c.director_state.behaviour_history == []


class TestDirectorStateParrotBoundary:
    def test_no_director_state_object_in_parrot_context(self):
        c = _live_coordinator()
        ctx = c.build_parrot_context("hello", 1, _CLEAN_NAVARASA)
        assert "director_state" not in ctx
        assert "director_state" not in ctx["parrot_session"]

    @pytest.mark.parametrize("forbidden_key", list(_PARROT_FORBIDDEN_KEYS))
    def test_forbidden_keys_absent_including_director_state(self, forbidden_key):
        c = _live_coordinator()
        ctx = c.build_parrot_context("hello", 1, _CLEAN_NAVARASA)
        assert forbidden_key not in ctx
        assert forbidden_key not in ctx["parrot_session"]

    def test_discarded_coordinator_replaced_with_empty_director_state(self):
        c1 = _live_coordinator()
        ctx = c1.build_parrot_context("hi", 1, _CLEAN_NAVARASA)
        choose_behaviour(ctx["parrot_session"])
        c1.apply_parrot_session_state(ctx["parrot_session"])
        assert c1.director_state.behaviour_history

        c2 = SessionCoordinator()
        c2.start()
        assert c2.director_state.behaviour_history == []
        assert c2.session_id != c1.session_id
