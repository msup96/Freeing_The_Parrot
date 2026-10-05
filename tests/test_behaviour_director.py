"""Pass 4 — Behaviour Director."""

import random
from unittest.mock import patch

import pytest

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel
from ftp.parrot.continuity import continuity_index_from_coordinator
from ftp.parrot.director import (
    FRACTURE_POOL,
    BehaviourDirector,
    PROHIBITED_OUTPUT_LABELS,
    sync_legacy_session_behaviour_counters,
)
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState

_NAV = {
    "primary_rasa": "Shanta",
    "rasa_scores": {"Shanta": 1.0},
    "sentiment": {"compound": 0.0},
}


def _live() -> SessionCoordinator:
    c = SessionCoordinator()
    c.start()
    c.advance(SessionState.LIVE_CONVERSATION)
    return c


def _fluctuating(coordinator: SessionCoordinator) -> None:
    for message in ("a", "bbbbbbbbbbbb", "a"):
        coordinator.record_parrot_turn(message, "Reply.")


class TestDirectorInstructionShape:
    def test_returns_structured_instruction_without_prose(self):
        c = _live()
        instruction = BehaviourDirector.decide(
            c,
            turn_index=1,
            turn_text="hello",
            navarasa_result=_NAV,
        )
        assert set(instruction) >= {
            "behaviour",
            "behaviour_family",
            "behaviour_intensity",
            "directive",
            "directive_basis",
        }
        for key in ("behaviour", "behaviour_family", "behaviour_intensity"):
            assert "\n" not in instruction[key]
            assert len(instruction[key]) < 40

    def test_no_psychological_or_evidence_fields(self):
        c = _live()
        instruction = BehaviourDirector.decide(
            c, turn_index=1, turn_text="hi", navarasa_result=_NAV
        )
        for label in PROHIBITED_OUTPUT_LABELS:
            assert label not in instruction


class TestTrustWindowAndFracture:
    def test_first_substantive_turns_understanding_floor(self):
        c = _live()
        for turn in (1, 2, 3):
            instruction = BehaviourDirector.decide(
                c,
                turn_index=turn,
                turn_text="thinking",
                navarasa_result=_NAV,
                rng=random.Random(turn),
            )
            assert instruction["behaviour"] == "understanding"
            assert instruction["selection_mode"] == "trust_window"

    def test_fracture_impossible_when_ineligible(self):
        c = _live()
        c.director_state.understanding_turns = 3
        with patch.object(
            SessionCoordinator,
            "live_engagement_snapshot",
            return_value={
                "behavioural_eligibility": {
                    "fracture_eligibility": "ineligible",
                    "fracture_intensity_band": "none",
                    "recovery_eligibility": "ineligible",
                }
            },
        ):
            for seed in range(50):
                instruction = BehaviourDirector.decide(
                    c,
                    turn_index=10,
                    turn_text="x",
                    navarasa_result=_NAV,
                    rng=random.Random(seed),
                )
                assert instruction["selection_mode"] != "fracture"

    def test_fracture_only_when_eligible(self):
        c = _live()
        c.director_state.understanding_turns = 3
        with patch.object(
            SessionCoordinator,
            "live_engagement_snapshot",
            return_value={
                "behavioural_eligibility": {
                    "fracture_eligibility": "eligible",
                    "fracture_intensity_band": "moderate",
                    "recovery_eligibility": "ineligible",
                }
            },
        ):
            seen_fracture = False
            for seed in range(200):
                instruction = BehaviourDirector.decide(
                    c,
                    turn_index=10,
                    turn_text="x",
                    navarasa_result=_NAV,
                    rng=random.Random(seed),
                )
                if instruction["selection_mode"] == "fracture":
                    seen_fracture = True
                    assert instruction["behaviour"] in FRACTURE_POOL
            assert seen_fracture

    def test_approx_fifty_percent_fracture_when_eligible(self):
        c = _live()
        c.director_state.understanding_turns = 3
        with patch.object(
            SessionCoordinator,
            "live_engagement_snapshot",
            return_value={
                "behavioural_eligibility": {
                    "fracture_eligibility": "eligible",
                    "fracture_intensity_band": "low",
                    "recovery_eligibility": "ineligible",
                }
            },
        ):
            fracture_count = 0
            samples = 800
            for seed in range(samples):
                trial = _live()
                trial.director_state.understanding_turns = 3
                instruction = BehaviourDirector.decide(
                    trial,
                    turn_index=10,
                    turn_text="x",
                    navarasa_result=_NAV,
                    rng=random.Random(seed),
                )
                if instruction["selection_mode"] == "fracture":
                    fracture_count += 1
            ratio = fracture_count / samples
            assert 0.40 <= ratio <= 0.60

    def test_unstable_pool_when_fracture_not_selected(self):
        c = _live()
        c.director_state.understanding_turns = 3
        modes = set()
        with patch.object(
            SessionCoordinator,
            "live_engagement_snapshot",
            return_value={
                "behavioural_eligibility": {
                    "fracture_eligibility": "eligible",
                    "fracture_intensity_band": "moderate",
                    "recovery_eligibility": "ineligible",
                }
            },
        ):
            for seed in range(100):
                instruction = BehaviourDirector.decide(
                    c,
                    turn_index=10,
                    turn_text="x",
                    navarasa_result=_NAV,
                    rng=random.Random(seed),
                )
                modes.add(instruction["selection_mode"])
        assert "unstable" in modes or "understanding" in modes


class TestRecoveryAndRepetition:
    def test_recovery_bias_toward_coherent_behaviour(self):
        c = _live()
        c.director_state.understanding_turns = 3
        coherent = 0
        with patch.object(
            SessionCoordinator,
            "live_engagement_snapshot",
            return_value={
                "behavioural_eligibility": {
                    "fracture_eligibility": "ineligible",
                    "fracture_intensity_band": "none",
                    "recovery_eligibility": "eligible",
                }
            },
        ):
            for seed in range(200):
                instruction = BehaviourDirector.decide(
                    c,
                    turn_index=6,
                    turn_text="x",
                    navarasa_result=_NAV,
                    rng=random.Random(seed),
                )
                if instruction["selection_mode"] == "recovery":
                    coherent += 1
                    assert instruction["behaviour"] in {"understanding", "mirroring"}
            assert coherent > 40

    def test_avoids_immediate_repeat_when_possible(self):
        c = _live()
        c.director_state.understanding_turns = 3
        c.director_state.last_behaviour = "absurd"
        repeats = 0
        with patch.object(
            SessionCoordinator,
            "live_engagement_snapshot",
            return_value={
                "behavioural_eligibility": {
                    "fracture_eligibility": "ineligible",
                    "fracture_intensity_band": "none",
                    "recovery_eligibility": "ineligible",
                }
            },
        ):
            for seed in range(100):
                trial = _live()
                trial.director_state.understanding_turns = 3
                trial.director_state.last_behaviour = "absurd"
                instruction = BehaviourDirector.decide(
                    trial,
                    turn_index=10,
                    turn_text="x",
                    navarasa_result=_NAV,
                    rng=random.Random(seed),
                )
                if instruction["behaviour"] == "absurd":
                    repeats += 1
        assert repeats == 0


class TestDirectorStateAuthority:
    def test_state_updates_after_decision(self):
        c = _live()
        BehaviourDirector.decide(
            c, turn_index=1, turn_text="a", navarasa_result=_NAV
        )
        assert c.director_state.last_behaviour == "understanding"
        assert c.director_state.behaviour_history

    def test_legacy_session_mirrors_director_state(self):
        c = _live()
        legacy = {
            "understanding_turns": 99,
            "chaos_count": 99,
            "last_behaviour": "wrong",
            "behaviour_history": [],
        }
        BehaviourDirector.decide(
            c, turn_index=1, turn_text="a", navarasa_result=_NAV
        )
        sync_legacy_session_behaviour_counters(legacy, c)
        assert legacy["understanding_turns"] == c.director_state.understanding_turns
        assert legacy["last_behaviour"] == c.director_state.last_behaviour

    def test_purge_clears_director_state(self):
        c = _live()
        BehaviourDirector.decide(
            c, turn_index=1, turn_text="a", navarasa_result=_NAV
        )
        c._on_state_change(
            SessionState.OUTPUT_GENERATION,
            SessionState.PURGE_AND_RESET,
        )
        assert c.director_state.behaviour_history == []


class TestContinuityDirectives:
    def test_repeated_phrase_can_yield_familiarity_or_reciprocity(self):
        c = _live()
        c.record_parrot_turn("I keep thinking about the old garden path.", "ok")
        c.record_parrot_turn("The old garden path still matters.", "ok")
        c.director_state.understanding_turns = 3
        instruction = BehaviourDirector.decide(
            c,
            turn_index=4,
            turn_text="again",
            navarasa_result=_NAV,
            rng=random.Random(1),
        )
        assert instruction["directive"] in {"familiarity", "reciprocity", None}

    def test_open_thread_can_yield_expectation_or_curiosity(self):
        c = _live()
        c.record_parrot_turn("hello", "What do you mean by that?")
        c.record_parrot_turn("unsure", "ok")
        c.director_state.understanding_turns = 3
        instruction = BehaviourDirector.decide(
            c,
            turn_index=3,
            turn_text="next",
            navarasa_result=_NAV,
            rng=random.Random(2),
        )
        assert instruction["directive"] in {"expectation", "curiosity", None}

    def test_previous_fracture_can_yield_repair(self):
        c = _live()
        c.record_parrot_turn("hello", "What do you mean?")
        c.record_parrot_turn("unsure", "ok")
        c.director_state.understanding_turns = 3
        c.director_state.last_behaviour = "memory_loss"
        instruction = BehaviourDirector.decide(
            c,
            turn_index=3,
            turn_text="next",
            navarasa_result=_NAV,
            rng=random.Random(3),
        )
        assert instruction["directive"] == "repair"

    def test_no_signal_no_forced_directive(self):
        c = _live()
        c.director_state.understanding_turns = 3
        instruction = BehaviourDirector.decide(
            c,
            turn_index=2,
            turn_text="only line",
            navarasa_result=_NAV,
            rng=random.Random(4),
        )
        assert instruction["directive"] is None
        assert instruction["directive_basis"] == []

    def test_no_turn_count_parasocial_scripting(self):
        c = _live()
        c.director_state.understanding_turns = 3
        for turn in (4, 5, 6, 7):
            instruction = BehaviourDirector.decide(
                c,
                turn_index=turn,
                turn_text="neutral text without overlap",
                navarasa_result=_NAV,
                rng=random.Random(turn),
            )
            assert instruction["directive"] is None


class TestIsolation:
    def test_no_event_store_writes(self):
        c = _live()
        before = len(c.store.all_events())
        BehaviourDirector.decide(
            c, turn_index=1, turn_text="a", navarasa_result=_NAV
        )
        assert len(c.store.all_events()) == before

    def test_no_cross_session_leakage(self):
        a = _live()
        b = _live()
        BehaviourDirector.decide(a, turn_index=1, turn_text="a", navarasa_result=_NAV)
        assert b.director_state.last_behaviour is None

    def test_forbidden_navarasa_input_rejected(self):
        c = _live()
        with pytest.raises(ValueError, match="Forbidden"):
            BehaviourDirector.decide(
                c,
                turn_index=1,
                turn_text="a",
                navarasa_result={**_NAV, "engagement_state": "high"},
            )

    def test_cards_do_not_enter_director_output(self):
        c = _live()
        c.store.append(
            InteractionEvent(
                session_id=c.session_id,
                event_type=EventType.CARDS_GENERATED,
                provenance_level=ProvenanceLevel.INFERRED,
                payload={"reading_profile": {"x": 1}, "hidden_provenance": {}},
            )
        )
        instruction = BehaviourDirector.decide(
            c, turn_index=1, turn_text="a", navarasa_result=_NAV
        )
        assert "reading_profile" not in str(instruction)


class TestFtp2ChatWiring:
    def test_choose_behaviour_not_called_on_ftp2_live_path(
        self, monkeypatch, tmp_path
    ):
        import interface_server as server

        def _boom(_session):
            raise AssertionError("choose_behaviour must not run on FTP2 live path")

        monkeypatch.setattr(server, "choose_behaviour", _boom)
        monkeypatch.setattr(server, "DB_FILE", tmp_path / "chat.sqlite3")
        client = server.app.test_client()
        session_id = client.post("/api/session/start").get_json()["session_id"]
        client.post(
            "/api/input/text",
            json={"session_id": session_id, "text": "Initial offering."},
        )
        client.post(
            "/api/session-lifecycle",
            json={"session_id": session_id, "action": "input_complete"},
        )
        client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "hello"},
        )
        for turn in range(3):
            result = client.post(
                "/api/chat",
                json={
                    "session_id": session_id,
                    "message": f"Substantive message number {turn}.",
                },
            ).get_json()
            assert "error" not in result
