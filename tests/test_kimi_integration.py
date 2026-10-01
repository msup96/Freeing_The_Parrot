"""Phase 2A checks for the optional Flask-served Kimi production bundle."""

from pathlib import Path

import interface_server as server


def test_kimi_source_is_copied_outside_read_only_references():
    production_source = Path(__file__).resolve().parents[1] / "frontend" / "kimi"
    reference_source = (
        Path(__file__).resolve().parents[1]
        / "references"
        / "Kimi_Agent_自由鹦鹉视觉层"
        / "app"
    )

    assert (production_source / "src" / "App.tsx").exists()
    assert (production_source / "package-lock.json").exists()
    assert production_source != reference_source


def test_kimi_bundle_route_is_safe_before_build():
    client = server.app.test_client()
    if server.KIMI_DIST_DIR.exists():
        response = client.get("/kimi/")
        assert response.status_code == 200
        assert b"root" in response.data
    else:
        response = client.get("/kimi/")
        assert response.status_code == 503
        assert response.get_json()["error"] == "Kimi production bundle is not built."


def test_kimi_api_sequence_uses_authoritative_ftp_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "BASE_DIR", tmp_path)
    monkeypatch.setattr(
        server,
        "SESSION_OUTPUT_STATUS_FILE",
        tmp_path / "session_output_status.json",
    )
    client = server.app.test_client()

    started = client.post("/api/session/start").get_json()
    session_id = started["session_id"]
    assert started["state"] == "INPUT_INGESTION"

    assert client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "premature"},
    ).status_code == 409

    ready = client.post(
        "/api/input/text",
        json={"session_id": session_id, "text": "Initial offering."},
    ).get_json()
    assert ready["analysis_ready"] is True
    assert "primary_rasa" not in ready
    assert "rasa_scores" not in ready

    live = client.post(
        "/api/session-lifecycle",
        json={"session_id": session_id, "action": "input_complete"},
    ).get_json()
    assert live["lifecycle_state"] == "LIVE_CONVERSATION"

    chat = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "Now speak."},
    ).get_json()
    assert chat["response"]
    assert "parrot_context" not in chat

    assert client.post(
        "/api/end-conversation",
        json={"session_id": session_id},
    ).get_json()["lifecycle_state"] == "CARD_SELECTION"
    assert client.post(
        "/api/session-lifecycle",
        json={
            "session_id": session_id,
            "action": "card_selection",
            "card_index": 1,
        },
    ).get_json()["lifecycle_state"] == "PROFILE_REVEAL"
    assert client.post(
        "/api/session-lifecycle",
        json={"session_id": session_id, "action": "reveal"},
    ).get_json()["lifecycle_state"] == "DATA_WALL_CONSENT"
    assert client.post(
        "/api/session-lifecycle",
        json={
            "session_id": session_id,
            "action": "consent",
            "consent_type": "KEEP_PRIVATE",
        },
    ).get_json()["lifecycle_state"] == "OUTPUT_GENERATION"
    assert client.post(
        "/api/session-output",
        json={"session_id": session_id},
    ).get_json()["success"] is True
    assert client.post(
        "/api/session-output-reset",
        json={"session_id": session_id, "consent_type": "KEEP_PRIVATE"},
    ).get_json()["lifecycle_state"] == "IDLE_STANDBY"