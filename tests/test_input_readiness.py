"""Authoritative hidden-reader readiness contract tests."""

import io

import pytest

import interface_server as server
from ftp.events.model import EventType
from ftp.session.states import SessionState


def start_session(client):
    response = client.post("/api/session/start")
    assert response.status_code == 200
    return response.get_json()["session_id"]


def test_start_stays_in_input_ingestion_and_hides_analysis():
    client = server.app.test_client()
    response = client.post("/api/session/start")
    body = response.get_json()
    coordinator = server.get_ftp2_coordinator(body["session_id"])

    assert body["state"] == "INPUT_INGESTION"
    assert body["analysis_ready"] is False
    assert coordinator.state is SessionState.INPUT_INGESTION
    assert set(body) == {"ok", "session_id", "state", "analysis_ready"}


def test_initial_text_is_analyzed_without_invoking_parrot(monkeypatch):
    client = server.app.test_client()
    session_id = start_session(client)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("live Parrot must not run for initial offering")

    monkeypatch.setattr(server, "process_chat_message", fail_if_called)
    response = client.post(
        "/api/input/text",
        json={"session_id": session_id, "text": "I feel uncertain."},
    )
    body = response.get_json()
    coordinator = server.get_ftp2_coordinator(session_id)

    assert response.status_code == 200
    assert body["analysis_ready"] is True
    assert "primary_rasa" not in body
    assert "rasa_scores" not in body
    assert coordinator.state is SessionState.INPUT_INGESTION
    assert coordinator.store.events_of_type(EventType.NAVARASA_CLASSIFIED)


def test_chat_is_rejected_before_readiness():
    client = server.app.test_client()
    session_id = start_session(client)
    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Do not answer yet."},
    )

    assert response.status_code == 409
    assert response.get_json()["state"] == "INPUT_INGESTION"
    assert response.get_json()["analysis_ready"] is False


def _ingest(client, session_id, modality, filename, payload):
    return client.post(
        "/api/input/ingest",
        data={
            "session_id": session_id,
            "modality": modality,
            "file": (io.BytesIO(payload), filename),
        },
        content_type="multipart/form-data",
    )


@pytest.mark.parametrize(
    ("modality", "filename", "payload"),
    [
        ("AUDIO", "offering.webm", b"not-audio"),
        ("IMAGE", "offering.jpg", b"not-an-image"),
        ("CAMERA", "offering.jpg", b"not-a-camera-frame"),
    ],
)
def test_multimodal_offering_is_ready_without_invented_analysis(
    monkeypatch,
    tmp_path,
    modality,
    filename,
    payload,
):
    monkeypatch.setattr(server, "INGEST_MEDIA_DIR", tmp_path / "media")
    client = server.app.test_client()
    session_id = start_session(client)
    response = _ingest(client, session_id, modality, filename, payload)
    body = response.get_json()
    coordinator = server.get_ftp2_coordinator(session_id)

    assert response.status_code == 200
    assert body["analysis_ready"] is True
    assert body["state"] == "INPUT_INGESTION"
    assert "primary_rasa" not in body
    assert coordinator.store.events_of_type(EventType.INPUT_RAW_INGESTED)
    assert not coordinator.store.events_of_type(EventType.NAVARASA_CLASSIFIED)
    assert not coordinator.store.events_of_type(EventType.OCR_TEXT_EXTRACTED)
    assert not coordinator.store.events_of_type(EventType.AUDIO_ASR_TRANSCRIBED)
    assert client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Still gated by lifecycle."},
    ).status_code == 409
    complete = client.post(
        "/api/session-lifecycle",
        json={"session_id": session_id, "action": "input_complete"},
    )
    assert complete.status_code == 200
    assert complete.get_json()["lifecycle_state"] == "LIVE_CONVERSATION"


def test_input_complete_requires_readiness_and_is_safe_to_repeat():
    client = server.app.test_client()
    session_id = start_session(client)
    before = client.post(
        "/api/session-lifecycle",
        json={"session_id": session_id, "action": "input_complete"},
    )
    assert before.status_code == 409

    client.post(
        "/api/input/text",
        json={"session_id": session_id, "text": "Ready now."},
    )
    complete = client.post(
        "/api/session-lifecycle",
        json={"session_id": session_id, "action": "input_complete"},
    )
    duplicate = client.post(
        "/api/session-lifecycle",
        json={"session_id": session_id, "action": "input_complete"},
    )

    assert complete.status_code == 200
    assert complete.get_json()["lifecycle_state"] == "LIVE_CONVERSATION"
    assert duplicate.status_code == 409


def test_live_chat_starts_only_after_input_complete():
    client = server.app.test_client()
    session_id = start_session(client)
    client.post(
        "/api/input/text",
        json={"session_id": session_id, "text": "A first offering."},
    )
    client.post(
        "/api/session-lifecycle",
        json={"session_id": session_id, "action": "input_complete"},
    )
    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Now we can speak."},
    )

    assert response.status_code == 200
    assert response.get_json()["response"]