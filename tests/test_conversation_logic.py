"""High-signal tests for the live conversational agency layer."""

from ftp.parrot.conversation_logic import (
    GLITCH_BEHAVIOURS,
    choose_conversation_plan,
    count_questions,
    is_response_repetitive,
    render_conversation_response,
    response_mode_for_behaviour,
)


def test_contextual_question_tracks_topic_and_avoids_exact_reuse():
    p1 = choose_conversation_plan(
        "I keep trying to understand the pattern in the other person's behaviour.",
        turn_index=4,
        behaviour="understanding",
        roll=0.10,
    )
    assert p1["conversation_move"] == "ask"
    assert "pattern" in str(p1["question_hint"]).lower()
    p2 = choose_conversation_plan(
        "I keep trying to understand the pattern in the other person's behaviour.",
        turn_index=5,
        behaviour="understanding",
        recent_questions=[str(p1["question_hint"])],
        roll=0.10,
    )
    assert p2["conversation_move"] == "ask"
    assert p2["question_hint"] != p1["question_hint"]


def test_direct_question_gets_answer_priority():
    plan = choose_conversation_plan(
        "Why did you say that?",
        turn_index=6,
        behaviour="banana",
        roll=0.01,
    )
    assert plan["conversation_move"] == "answer"
    assert plan["question_hint"] is None


def test_correction_gets_repair_priority_even_during_glitch():
    plan = choose_conversation_plan(
        "You are repeating yourself. Can we have a real conversation?",
        turn_index=8,
        behaviour="banana",
        roll=0.01,
    )
    assert plan["conversation_move"] == "repair"
    assert plan["question_hint"] is None


def test_move_selection_changes_after_a_previous_move():
    previous = None
    moves = []
    for roll in (0.05, 0.30, 0.62, 0.91):
        plan = choose_conversation_plan(
            "That gives me something concrete to work with.",
            turn_index=2,
            behaviour="understanding",
            last_move=previous,
            roll=roll,
        )
        previous = plan["conversation_move"]
        moves.append(previous)
    assert len(set(moves)) >= 3


def test_repetition_guard_catches_generic_and_semantic_repeats():
    recent = [
        "You seem to be looking for perspective rather than a dramatic solution.",
        "There is a sense that you already know part of the answer.",
    ]
    assert is_response_repetitive(
        "You seem to be trying to find perspective rather than a dramatic solution.",
        recent,
    )
    assert not is_response_repetitive(
        "When the reaction starts, what do you usually do first?",
        recent,
    )


def test_banana_is_glitch_mode():
    assert "banana" in GLITCH_BEHAVIOURS
    assert response_mode_for_behaviour("banana") == "glitch"
    assert response_mode_for_behaviour("understanding") == "normal"


def test_deterministic_questioned_response_has_one_question():
    text = render_conversation_response(
        "I am trying to understand the pattern.",
        move="ask",
        question_hint="What repeats most clearly — what they do, what you do, or what you expect will happen?",
        recent_replies=[],
        roll=0.21,
    )
    assert count_questions(text) == 1
