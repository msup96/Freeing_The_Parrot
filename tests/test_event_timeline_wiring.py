"""Event timeline wiring — chat observations into SessionCoordinator."""

import copy
from unittest.mock import patch

import pytest

from ftp.events.model import EventType, ProvenanceLevel
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState
from ftp.timeline.wiring import (
    build_text_raw_ingest_payload,
    record_chat_timeline_events,
)


def live_coordinator() -> SessionCoordinator:
    c = SessionCoordinator()
    c.start()
    c.advance(SessionState.LIVE_CONVERSATION)
    return c


class TestTextRawPayload:

    def test_text_raw_metadata_not_full_duplicate(self):
        payload = build_text_raw_ingest_payload("Hello there.")
        assert payload["modality"] == "TEXT"
        assert payload["source_channel"] == "WEB_COMPOSER"
        assert payload["character_count"] == 12
        assert "Hello there." not in str(payload.values())
        assert payload["storage_ref"] == "canonical:PARROT_TURN_GENERATED"


class TestRecordChatTimeline:

    def test_creates_raw_then_parrot_in_order(self):
        c = live_coordinator()
        record_chat_timeline_events(
            c,
            "I feel uncertain.",
            {
                "session_id": c.session_id,
                "turn": 1,
                "response": "I detected SHANTA.",
                "gate": {"gate": "reflection"},
                "closed": False,
            },
        )
        events = c.store.all_events()
        types = [e.event_type for e in events]
        raw_idx = types.index(EventType.INPUT_RAW_INGESTED)
        parrot_idx = types.index(EventType.PARROT_TURN_GENERATED)
        assert raw_idx < parrot_idx

    def test_raw_and_parrot_provenance(self):
        c = live_coordinator()
        record_chat_timeline_events(
            c,
            "Test message.",
            {
                "turn": 1,
                "response": "Reply.",
                "gate": {},
                "closed": False,
            },
        )
        raw = c.store.events_of_type(EventType.INPUT_RAW_INGESTED)[0]
        parrot = c.store.events_of_type(EventType.PARROT_TURN_GENERATED)[0]
        assert raw.provenance_level == ProvenanceLevel.RAW
        assert parrot.provenance_level == ProvenanceLevel.OBSERVED
        assert parrot.payload["user_text"] == "Test message."
        assert parrot.payload["parrot_reply"] == "Reply."

    def test_parrot_context_only_eligible_events(self):
        c = live_coordinator()
        record_chat_timeline_events(
            c,
            "Hi.",
            {"turn": 1, "response": "Hello.", "gate": {}, "closed": False},
        )
        c.record_raw_input({
            "modality": "IMAGE",
            "source_channel": "WEB_FILE_UPLOAD",
            "byte_size": 1,
            "sha256": "a",
            "storage_ref": "/x.png",
            "ingest_id": "id",
        })
        parrot_view = c.store.parrot_context()
        assert all(e.is_live_parrot_eligible() for e in parrot_view)
        assert all(
            e.event_type != EventType.INPUT_RAW_INGESTED for e in parrot_view
        )

    def test_salutation_turn_zero_does_not_increment_coordinator_count(self):
        c = live_coordinator()
        record_chat_timeline_events(
            c,
            "Hello",
            {
                "turn": 0,
                "response": "GREETINGS ACKNOWLEDGED.",
                "gate": {"gate": "reflection"},
                "closed": False,
            },
        )
        assert c.turn_count == 0
        parrot = c.store.events_of_type(EventType.PARROT_TURN_GENERATED)[0]
        assert parrot.payload["turn_index"] == 0

    def test_closed_result_locks_coordinator(self):
        c = live_coordinator()
        record_chat_timeline_events(
            c,
            "bad word test",
            {
                "turn": 1,
                "response": "Stopped.",
                "gate": {"gate": "reflection"},
                "closed": True,
            },
        )
        assert c.machine.is_locked()

    def test_skips_when_coordinator_none(self):
        record_chat_timeline_events(None, "Hi", {"turn": 1, "response": "x"})

    def test_skips_on_error_result(self):
        c = live_coordinator()
        before = len(c.store.all_events())
        record_chat_timeline_events(c, "Hi", {"error": "Empty message."})
        assert len(c.store.all_events()) == before


class TestFlaskChatTimeline:

    def test_session_start_chat_records_timeline_same_session_id(self):
        from interface_server import FTP2_COORDINATORS, SESSIONS, app

        client = app.test_client()
        start = client.post("/api/session/start")
        session_id = start.get_json()["session_id"]
        assert session_id in SESSIONS
        assert session_id in FTP2_COORDINATORS
        client.post(
            "/api/input/text",
            json={"session_id": session_id, "text": "Initial offering."},
        )
        client.post(
            "/api/session-lifecycle",
            json={"session_id": session_id, "action": "input_complete"},
        )

        chat = client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "Hello, I am here."},
        )
        assert chat.status_code == 200
        body = chat.get_json()
        assert "response" in body
        assert "error" not in body

        coord = FTP2_COORDINATORS[session_id]
        assert len(coord.store.events_of_type(EventType.INPUT_RAW_INGESTED)) >= 1
        assert len(coord.store.events_of_type(EventType.PARROT_TURN_GENERATED)) >= 1

    def test_chat_succeeds_when_timeline_recording_raises(self):
        from interface_server import app

        client = app.test_client()
        session_id = client.post("/api/session/start").get_json()["session_id"]
        client.post(
            "/api/input/text",
            json={"session_id": session_id, "text": "Initial offering."},
        )
        client.post(
            "/api/session-lifecycle",
            json={"session_id": session_id, "action": "input_complete"},
        )

        with patch(
            "interface_server.record_chat_timeline_events",
            side_effect=RuntimeError("timeline down"),
        ):
            response = client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "I feel worried today."},
            )
        assert response.status_code == 200
        body = response.get_json()
        assert body.get("response")
        assert "error" not in body

    def test_legacy_route_still_serves(self):
        from interface_server import app

        client = app.test_client()
        response = client.get("/legacy")
        assert response.status_code == 200
        html = response.data.decode("utf-8", errors="ignore")
        assert "scan-file-input" in html or "SCAN" in html.upper()
