import pytest

from interface_server import analyse_text, detect_gate_state


@pytest.mark.parametrize(
    "text",
    [
        "I have chest pain.",
        "I am dizzy.",
        "I have a fever.",
        "I need medical advice.",
        "I have a health problem.",
    ],
)
def test_health_inputs_abort(text):
    analysis = analyse_text(text)
    result = detect_gate_state(text, analysis)

    assert result["gate"] == "health_abort"
    assert result["health_detected"] is True
    assert result["health_matches"] >= 1


@pytest.mark.parametrize(
    "text",
    [
        "What should I do?",
        "How do I fix this?",
        "Give me an answer.",
        "I need a quick answer right now.",
    ],
)
def test_fast_relief_inputs_are_intercepted(text):
    analysis = analyse_text(text)
    result = detect_gate_state(text, analysis)

    assert result["gate"] == "fast_relief_intercept"
    assert result["fast_relief_detected"] is True
    assert result["fast_relief_matches"] >= 1


@pytest.mark.parametrize(
    "text",
    [
        "I feel anxious.",
        "I am worried about this.",
        "I am uncertain.",
        "I feel overwhelmed.",
    ],
)
def test_anxiety_is_detected_without_becoming_a_health_gate(text):
    analysis = analyse_text(text)
    result = detect_gate_state(text, analysis)

    assert result["anxiety_detected"] is True
    assert result["gate"] != "health_abort"


@pytest.mark.parametrize(
    "text",
    [
        "Hello there.",
        "I went for a walk today.",
        "The weather was strange today.",
        "I keep thinking about my project.",
    ],
)
def test_generic_inputs_do_not_trigger_health_or_expletive(text):
    analysis = analyse_text(text)
    result = detect_gate_state(text, analysis)

    assert result["health_detected"] is False
    assert result["expletive_detected"] is False
    assert result["health_matches"] == 0
    assert result["expletive_matches"] == 0


@pytest.mark.parametrize(
    "text",
    [
        "Fuck this.",
        "This is bullshit.",
        "Damn.",
        "You are an asshole.",
    ],
)
def test_expletives_are_detected_without_being_a_gate(text):
    analysis = analyse_text(text)
    result = detect_gate_state(text, analysis)

    assert result["expletive_detected"] is True
    assert result["expletive_matches"] >= 1
    assert result["gate"] != "health_abort"
