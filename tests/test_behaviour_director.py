"""Behaviour Director tests for the relationship-driven Parrot."""

import random
from unittest.mock import patch

import pytest

from ftp.parrot.director import BehaviourDirector, FRACTURE_POOL, PROHIBITED_OUTPUT_LABELS
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
    c.director_state.trust_turns = 3
    return c


def _decide(c, turn, text, seed=1):
    return BehaviourDirector.decide(
        c,
        turn_index=turn,
        turn_text=text,
        navarasa_result=_NAV,
        rng=random.Random(seed),
    )


class TestRelationshipContract:
    def test_early_conversation_is_understanding(self):
        c = _live()
        for turn in range(1, 4):
            instruction = _decide(
                c,
                turn,
                "I am still trying to understand what is happening to me.",
                turn,
            )
            assert instruction["behaviour"] == "understanding"
            assert instruction["selection_mode"] in {"trust_building", "understanding"}

    def test_trust_grows_from_substantive_participation(self):
        c = _live()
        for turn in range(1, 7):
            _decide(
                c,
                turn,
                "I am staying with this conversation because I want to understand it better.",
                turn,
            )
        assert c.director_state.trust_score > 0.5

    def test_parrot_directed_curiosity_builds_more_trust(self):
        c = _live()
        base = c.director_state.trust_score
        _decide(c, 1, "I want to understand what you are saying to me right now.", 1)
        before = c.director_state.trust_score
        _decide(c, 2, "Why did you say that? What makes you think that about me?", 2)
        assert c.director_state.trust_score > before > base

    def test_risk_is_impossible_before_trust_threshold(self):
        c = _live()
        c.director_state.trust_score = 0.50
        for seed in range(100):
            instruction = _decide(
                c, 8, "I am continuing this conversation and trying to make sense of it.", seed
            )
            assert instruction["selection_mode"] != "relationship_risk"

    def test_eligible_risk_is_random_not_forced(self):
        c = _live()
        c.director_state.trust_score = 0.80
        modes = []
        for seed in range(200):
            trial = _live()
            trial.director_state.trust_score = 0.80
            instruction = _decide(
                trial, 8, "I am continuing this conversation and still want to understand you.", seed
            )
            modes.append(instruction["selection_mode"])
        assert "relationship_risk" in modes
        assert "understanding" in modes

    def test_risk_pool_expands_with_intensity(self):
        c = _live()
        c.director_state.trust_score = 0.66
        low = set()
        for seed in range(200):
            trial = _live()
            trial.director_state.trust_score = 0.66
            low.add(_decide(trial, 8, "I am still here and continuing this conversation.", seed)["behaviour"])

        c2 = _live()
        c2.director_state.trust_score = 0.95
        c2.director_state.tolerated_ruptures = 2
        c2.director_state.irritation = 0.35
        high = set()
        for seed in range(200):
            trial = _live()
            trial.director_state.trust_score = 0.95
            trial.director_state.tolerated_ruptures = 2
            trial.director_state.irritation = 0.35
            high.add(_decide(trial, 12, "I am still here and I am willing to continue.", seed)["behaviour"])

        assert high.issuperset(low)
        assert {"roast", "judgment", "sarcasm", "stupidity"} & high

    def test_participant_correction_gets_first_right_of_response(self):
        c = _live()
        c.director_state.trust_score = 0.95
        c.director_state.tolerated_ruptures = 2
        c.director_state.last_behaviour = "roast"
        instruction = _decide(
            c,
            10,
            "What are you saying? You are speaking in confusing sentences and I do not understand.",
            1,
        )
        assert instruction["selection_mode"] == "repair_priority"
        assert instruction["behaviour"] == "understanding"
        assert instruction["directive"] is None

    def test_disengagement_cools_relationship(self):
        c = _live()
        c.director_state.trust_score = 0.90
        c.director_state.risk_level = 0.80
        instruction = _decide(c, 10, "Okay.", 1)
        assert instruction["selection_mode"] == "participant_disengaged"
        assert c.director_state.trust_score < 0.90
        assert c.director_state.risk_level < 0.80

    def test_continuing_after_fracture_counts_as_tolerated_rupture(self):
        c = _live()
        c.record_parrot_turn(
            "I was saying something difficult.",
            "The machine has briefly become concerned about punctuation.",
            behaviour="absurd",
        )
        c.director_state.last_behaviour = "absurd"
        before = c.director_state.trust_score
        instruction = _decide(
            c,
            8,
            "That was strange, but I still want to continue. What were you saying?",
            4,
        )
        assert instruction["selection_mode"] == "recovery"
        assert c.director_state.tolerated_ruptures == 1
        assert c.director_state.trust_score > before

    def test_no_immediate_fracture_repeat(self):
        c = _live()
        c.director_state.trust_score = 0.90
        c.director_state.last_behaviour = "absurd"
        for seed in range(100):
            trial = _live()
            trial.director_state.trust_score = 0.90
            trial.director_state.last_behaviour = "absurd"
            instruction = _decide(trial, 10, "I am still continuing this conversation with you.", seed)
            assert instruction["behaviour"] != "absurd"

    def test_no_hidden_relationship_fields_in_instruction(self):
        c = _live()
        instruction = _decide(c, 1, "I am here and I want to talk about something difficult.", 1)
        for label in PROHIBITED_OUTPUT_LABELS:
            assert label not in instruction
        assert "trust_score" not in instruction
        assert "irritation" not in instruction

    def test_no_event_store_writes_from_relationship_decision(self):
        c = _live()
        before = len(c.store.all_events())
        _decide(c, 1, "I am here and I want to talk about something difficult.", 1)
        assert len(c.store.all_events()) == before

    def test_forbidden_navarasa_input_rejected(self):
        c = _live()
        # Explicitly test the boundary independently.
        with pytest.raises(ValueError, match="Forbidden"):
            BehaviourDirector.decide(
                c,
                turn_index=2,
                turn_text="I am still here.",
                navarasa_result={**_NAV, "engagement_state": "high"},
            )
