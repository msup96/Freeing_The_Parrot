"""HTTP wiring for the participant-facing FTP2 lifecycle."""

import interface_server as server


def test_participant_lifecycle_reaches_output_and_resets(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "BASE_DIR", tmp_path)
    monkeypatch.setattr(
        server,
        "SESSION_OUTPUT_STATUS_FILE",
        tmp_path / "session_output_status.json",
    )

    client = server.app.test_client()
    session_id = client.post("/api/session/start").get_json()["session_id"]
    client.post(
        "/api/input/text",
        json={"session_id": session_id, "text": "I am ready."},
    )
    client.post(
        "/api/session-lifecycle",
        json={"session_id": session_id, "action": "input_complete"},
    )

    response = client.post(
        "/api/end-conversation",
        json={"session_id": session_id},
    )
    assert response.get_json()["lifecycle_state"] == "CARD_SELECTION"

    transitions = [
        ({"action": "card_selection", "card_index": 7, "card_text": "A reading."}, "PROFILE_REVEAL"),
        ({"action": "reveal"}, "DATA_WALL_CONSENT"),
        ({"action": "consent", "consent_type": "KEEP_PRIVATE"}, "OUTPUT_GENERATION"),
    ]
    for payload, expected_state in transitions:
        payload["session_id"] = session_id
        response = client.post("/api/session-lifecycle", json=payload)
        assert response.status_code == 200
        assert response.get_json()["lifecycle_state"] == expected_state

    output = client.post("/api/session-output", json={"session_id": session_id})
    assert output.status_code == 200
    assert output.get_json()["success"] is True

    reset = client.post(
        "/api/session-output-reset",
        json={"session_id": session_id, "consent_type": "KEEP_PRIVATE"},
    )
    assert reset.status_code == 200
    assert reset.get_json()["lifecycle_state"] == "IDLE_STANDBY"


def test_participant_lifecycle_rejects_invalid_consent():
    client = server.app.test_client()
    session_id = client.post("/api/session/start").get_json()["session_id"]
    client.post(
        "/api/input/text",
        json={"session_id": session_id, "text": "Ready."},
    )
    client.post(
        "/api/session-lifecycle",
        json={"session_id": session_id, "action": "input_complete"},
    )
    client.post("/api/end-conversation", json={"session_id": session_id})
    client.post(
        "/api/session-lifecycle",
        json={
            "session_id": session_id,
            "action": "card_selection",
            "card_index": 1,
        },
    )
    client.post(
        "/api/session-lifecycle",
        json={"session_id": session_id, "action": "reveal"},
    )

    response = client.post(
        "/api/session-lifecycle",
        json={
            "session_id": session_id,
            "action": "consent",
            "consent_type": "MAYBE",
        },
    )
    assert response.status_code == 400
    assert server.get_ftp2_coordinator(session_id).state.value == "DATA_WALL_CONSENT"