"""Stage 08 contract: the backend serializes plain-language limits and a fuller interaction profile."""

import ftp_backend_service as backend
from ftp.events.model import EventType
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState

TURNS = [
    "Why does it repeat me?",
    "Why does it repeat me?",
    "I feel strange and I want to know why this happens to me?",
]


def _reveal():
    coordinator = SessionCoordinator("reveal-serialization")
    coordinator.start()
    coordinator.record_raw_input({"modality": "TEXT", "text": "hello"})
    coordinator.mark_analysis_ready({"primary_rasa": "Karuna"})
    coordinator.advance(SessionState.LIVE_CONVERSATION)
    for text in TURNS:
        coordinator.record_parrot_turn(text, "echo")
    coordinator.lock()
    coordinator.advance(SessionState.POST_SESSION_INTERPRETATION)
    coordinator.generate_post_session_interpretation()
    coordinator.advance(SessionState.CARD_SELECTION)
    cards = coordinator.store.events_of_type(EventType.CARDS_GENERATED)[-1].payload["cards"]
    deck = {"cards": cards}
    return backend.build_participant_reveal(coordinator, deck, [cards[7], cards[18]]), cards


def test_limitations_are_plain_language_not_raw_codes():
    reveal, _ = _reveal()
    limits = reveal["what_we_cannot_know"]

    assert limits
    assert not any("_unavailable" in line or "_insufficient" in line for line in limits)
    assert any("does not permit the system to infer" in line for line in limits)


def test_records_carry_plain_language_limitation_notes():
    reveal, _ = _reveal()

    assert all("limitation_notes" in item for item in reveal["observed_signals"])
    assert all("limitation_notes" in item for item in reveal["inference_records"])


def test_interaction_profile_serializes_existing_artifacts_only():
    reveal, cards = _reveal()
    profile = reveal["interaction_profile"]

    assert profile["turn_count"] == 3
    assert profile["question_density"] == 1.0
    assert profile["repetition_count"] == 1
    assert profile["readings_constructed"] == len(cards) == 27
    assert profile["card_selection_count"] == 2
    assert profile["resonance"] == "participant-reported"
    # No Rasa was detected, so none may be reported as a trajectory.
    assert reveal["navarasa_trajectory"]["detected_sequence"] == []
    assert profile["navarasa_status"] == "insufficient_evidence"


def test_selection_pattern_keeps_order_and_marks_inspection_unavailable():
    reveal, cards = _reveal()
    pattern = reveal["selection_pattern"]

    assert pattern["selected_card_indices"] == [8, 19]
    assert pattern["selection_order"] == [cards[7]["card_id"], cards[18]["card_id"]]
    assert pattern["cards_inspected"] is None
    states = [c["selection_state"] for c in reveal["card_provenance"]]
    assert states.count("selected") == 2
