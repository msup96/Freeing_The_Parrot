import time

import pytest

import ftp_backend_service as backend


@pytest.fixture(autouse=True)
def clean_sessions():
    stores = (
        backend.SESSIONS,
        backend.SESSION_OFFERINGS,
        backend.SESSION_MULTIMODAL_CONTEXT,
        backend.SESSION_DECKS,
        backend.SESSION_SELECTED,
        backend.SESSION_REVEALS,
        backend.SESSION_CREATED_AT,
    )
    for store in stores:
        store.clear()
    yield
    for store in stores:
        store.clear()


def test_session_creation_generates_unique_ids():
    first = backend.create_session()
    second = backend.create_session()
    assert first.session_id != second.session_id
    assert backend.get_session(first.session_id) is first
    assert backend.get_session(second.session_id) is second


def test_session_state_isolation():
    first = backend.create_session()
    second = backend.create_session()
    backend.SESSION_OFFERINGS[first.session_id] = {"text": "first"}
    backend.SESSION_OFFERINGS[second.session_id] = {"text": "second"}
    backend.SESSION_DECKS[first.session_id] = {"cards": [{"title": "first card"}]}

    assert backend.SESSION_OFFERINGS[first.session_id]["text"] == "first"
    assert backend.SESSION_OFFERINGS[second.session_id]["text"] == "second"
    assert second.session_id not in backend.SESSION_DECKS


def test_active_session_can_be_retrieved():
    session = backend.create_session()
    assert backend.require_session(session.session_id) is session


def test_expired_session_is_purged_and_rejected(monkeypatch):
    session = backend.create_session()
    sid = session.session_id
    backend.SESSION_OFFERINGS[sid] = {"text": "private"}
    backend.SESSION_DECKS[sid] = {"cards": ["private card"]}
    backend.SESSION_REVEALS[sid] = {"private": True}
    created_at = backend.SESSION_CREATED_AT[sid]

    purged = backend.purge_expired_sessions(now=created_at + backend.SESSION_TTL_SECONDS)

    assert purged == [sid]
    assert backend.get_session(sid) is None
    assert sid not in backend.SESSION_OFFERINGS
    assert sid not in backend.SESSION_DECKS
    assert sid not in backend.SESSION_REVEALS
    with pytest.raises(KeyError):
        backend.require_session(sid)


def test_purge_does_not_remove_active_sessions():
    session = backend.create_session()
    assert backend.purge_expired_sessions(now=time.time()) == []
    assert backend.get_session(session.session_id) is session


def test_unknown_session_ids_are_not_created():
    with pytest.raises(KeyError):
        backend.require_session("ftp2_unknown")
    assert "ftp2_unknown" not in backend.SESSIONS


def test_same_session_survives_normalized_multimodal_input():
    session = backend.create_session()
    sid = session.session_id

    session.record_raw_input({"modality": "IMAGE", "filename": "offering.png"})
    session.mark_raw_offering_ready()
    backend.SESSION_MULTIMODAL_CONTEXT[sid] = {"modality": "photo", "confidence": 0.84}
    backend.SESSION_OFFERINGS[sid] = {"channel": "show", "modality": "IMAGE"}

    assert backend.require_session(sid) is session
    assert backend.SESSION_MULTIMODAL_CONTEXT[sid]["modality"] == "photo"
    assert backend.SESSION_OFFERINGS[sid]["modality"] == "IMAGE"


def test_participant_reveal_preserves_structured_analysis_and_card_provenance():
    session = backend.create_session()
    sid = session.session_id
    session.advance(backend.SessionState.LIVE_CONVERSATION)
    session.record_parrot_turn("I keep returning to this question?", "reply")
    session.record_parrot_turn("I want to understand the pattern.", "reply")
    session.lock()
    deck = {"cards": [{
        "card_id": f"card_{index:02d}", "card_index": index,
        "title": f"Card {index}", "archetype": "ARCHIVE",
        "qualitative_reading": "A session reading.",
        "provenance_level": "INFERRED",
        "hidden_provenance": {"inference_ids": ["inf_x"], "evidence_ids": ["ev_message_length"]},
    } for index in range(1, 28)]}

    reveal = backend.build_participant_reveal(session, deck, [deck["cards"][0]])

    assert reveal["analytical_artifacts"]["linguistic"]["turn_sequence"]
    assert reveal["analytical_artifacts"]["temporal"]["turn_sequence"]
    assert "turn_sequence" in reveal["analytical_artifacts"]["navarasa"]
    assert reveal["observed_signals"]
    assert all("value" in item and "source_event_ids" in item for item in reveal["observed_signals"])
    assert "inference_records" in reveal
    assert len(reveal["card_provenance"]) == 27
    assert reveal["card_provenance"][0]["provenance"]["evidence_ids"] == ["ev_message_length"]
    assert reveal["selection_pattern"]["selected_card_ids"] == ["card_01"]
    assert reveal["analytical_artifacts"]["navarasa"]["dominant_rasa"]["label"] is not None or reveal["analytical_artifacts"]["navarasa"]["dominant_rasa"]["status"] == "insufficient"
