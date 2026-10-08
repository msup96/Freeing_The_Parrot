"""Focused tests for live participant-Parrot relationship signals."""

from ftp.parrot.continuity import DialogueTurn
from ftp.silent_reader.live_relationship import derive_live_relationship_signals


def _turn(behaviour="understanding"):
    return DialogueTurn(
        turn_index=1,
        user_text="I am trying to understand what you are saying.",
        parrot_reply="The machine is listening.",
        behaviour=behaviour,
    )


def test_parrot_directed_question_is_strong_relational_signal():
    signals = derive_live_relationship_signals(
        [_turn()],
        current_text="Why did you say that? What makes you think that?",
    )
    assert signals["parrot_directed"] is True
    assert signals["trust_delta"] > 0.10


def test_continuing_after_fracture_is_strongest_trust_signal():
    signals = derive_live_relationship_signals(
        [_turn("absurd")],
        current_text="That was strange, but I still want to continue. What were you saying?",
    )
    assert signals["previous_fracture"] is True
    assert signals["continued_after_fracture"] is True
    assert signals["trust_delta"] >= 0.18


def test_irritation_can_still_be_engagement():
    signals = derive_live_relationship_signals(
        [_turn("sarcasm")],
        current_text="You are being annoying. Why are you doing that?",
    )
    assert signals["irritation"] is True
    assert signals["parrot_directed"] is True
    assert signals["disengagement"] is False
    assert signals["engagement_delta"] > 0


def test_simple_exit_cools_relationship():
    signals = derive_live_relationship_signals(
        [_turn("roast")],
        current_text="Okay.",
    )
    assert signals["disengagement"] is True
    assert signals["engagement_delta"] < 0
    assert signals["trust_delta"] < 0


def test_correction_is_not_treated_as_permission_to_glitch():
    signals = derive_live_relationship_signals(
        [_turn("absurd")],
        current_text="What are you saying? You are confusing me.",
    )
    assert signals["correction"] is True
    assert signals["previous_fracture"] is True
