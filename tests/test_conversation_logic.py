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
    assert "repeats" in str(p1["question_hint"]).lower()
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


def test_questions_do_not_fire_on_consecutive_turns():
    first = choose_conversation_plan(
        "I keep noticing the same pattern.",
        turn_index=4,
        behaviour="understanding",
        last_move="reflect",
        roll=0.10,
    )
    second = choose_conversation_plan(
        "Yes.",
        turn_index=5,
        behaviour="understanding",
        last_move=first["conversation_move"],
        recent_questions=[str(first["question_hint"])],
        roll=0.10,
    )
    assert first["conversation_move"] == "ask"
    assert second["conversation_move"] != "ask"


def test_direct_pattern_question_gets_a_substantive_fallback_answer():
    plan = choose_conversation_plan(
        "How do I understand a pattern?",
        turn_index=4,
        behaviour="understanding",
    )
    answer = render_conversation_response(
        "How do I understand a pattern?",
        move=plan["conversation_move"],
        question_hint=plan["question_hint"],
        roll=0.12,
    )
    assert plan["conversation_move"] == "answer"
    assert "sequence" in answer.lower() or "instances" in answer.lower()


def test_two_same_theme_questions_create_space():
    questions = [
        "What repeats most clearly — what they do, what you do, or what you expect will happen?",
        "When you call it a pattern, which part keeps happening in almost the same shape?",
    ]
    plan = choose_conversation_plan(
        "I keep thinking about the pattern.",
        turn_index=7,
        behaviour="understanding",
        recent_questions=questions,
        roll=0.01,
    )
    assert plan["conversation_move"] != "ask"
    assert plan["question_hint"] is None


def test_question_does_not_follow_question_move():
    plan = choose_conversation_plan(
        "There is more I want to understand about the relationship.",
        turn_index=6,
        behaviour="understanding",
        last_move="ask",
        roll=0.01,
    )
    assert plan["conversation_move"] != "ask"


def test_correction_repairs_instead_of_repeating():
    plan = choose_conversation_plan(
        "You are repeating yourself. Can we have a real conversation?",
        turn_index=8,
        behaviour="banana",
        roll=0.01,
    )
    assert plan["conversation_move"] == "repair"
    rendered = render_conversation_response(
        "You are repeating yourself. Can we have a real conversation?",
        move=plan["conversation_move"],
        recent_replies=[],
        roll=0.2,
    )
    assert "try that again" in rendered.lower()


def test_semantic_repetition_guard_catches_paraphrase():
    recent = [
        "You are looking for perspective rather than a dramatic solution.",
    ]
    candidate = "You may be looking for perspective rather than a dramatic solution."
    assert is_response_repetitive(candidate, recent)



def test_explicit_request_for_help_overrides_reading_or_reflection_pattern():
    from ftp.parrot.conversation_logic import is_explicit_help_request

    message = "Without giving me any further readings, please answer, how do I deal with this? You are intelligent, you can help."
    assert is_explicit_help_request(message)
    plan = choose_conversation_plan(
        message, turn_index=7, behaviour="understanding", roll=0.01
    )
    assert plan["conversation_move"] == "answer"
    answer = render_conversation_response(
        message, move=plan["conversation_move"], roll=0.01
    )
    assert "action" in answer.lower() or "specific" in answer.lower() or "concrete" in answer.lower()


def test_waiting_for_answer_is_not_misclassified_as_ordinary_reflection():
    message = "I am still waiting for your answer."
    plan = choose_conversation_plan(
        message, turn_index=8, behaviour="understanding", roll=0.01
    )
    assert plan["conversation_move"] == "answer"


def test_loss_of_trust_triggers_repair_priority():
    message = "This is strange, you keep giving predictions one after the other. They are helpful at first, but now I am beginning to lose my trust."
    assert __import__("ftp.parrot.conversation_logic", fromlist=["is_correction_or_complaint"]).is_correction_or_complaint(message)
    plan = choose_conversation_plan(
        message, turn_index=9, behaviour="understanding", roll=0.01
    )
    assert plan["conversation_move"] == "repair"
