"""Multimodal RAW ingest — event store and Parrot boundary tests."""

import tempfile
import uuid
from pathlib import Path

import pytest

from ftp.events.model import EventType, ProvenanceLevel
from ftp.input.raw import build_raw_ingest_payload, save_session_media, sha256_bytes
from ftp.session.coordinator import SessionCoordinator, SessionLockedError
from ftp.session.states import SessionState


def live_coordinator() -> SessionCoordinator:
    c = SessionCoordinator()
    c.start()
    c.advance(SessionState.LIVE_CONVERSATION)
    return c


class TestRawPayloadBuilder:

    def test_build_payload_shape(self):
        payload = build_raw_ingest_payload(
            "IMAGE",
            "WEB_FILE_UPLOAD",
            byte_size=1024,
            content_sha256="abc",
            storage_ref="/tmp/x.png",
            media_format="PNG",
        )
        assert payload["modality"] == "IMAGE"
        assert payload["source_channel"] == "WEB_FILE_UPLOAD"
        assert payload["byte_size"] == 1024
        assert payload["sha256"] == "abc"
        assert payload["storage_ref"] == "/tmp/x.png"
        assert payload["media_format"] == "PNG"
        assert "ingest_id" in payload

    def test_save_session_media_writes_file(self):
        data = b"fake-image-bytes"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            path, ref = save_session_media(base, "sess-1", ".png", data)
            assert path.exists()
            assert path.read_bytes() == data
            assert ref == str(path)


class TestCoordinatorRawIngest:

    def test_records_input_raw_ingested(self):
        c = live_coordinator()
        payload = build_raw_ingest_payload(
            "AUDIO",
            "WEB_MICROPHONE",
            byte_size=10,
            content_sha256=sha256_bytes(b"0123456789"),
            storage_ref="C:\\ingest\\a.webm",
            media_format="WEBM",
            duration_ms=500,
        )
        event = c.record_raw_input(payload)
        assert event.event_type == EventType.INPUT_RAW_INGESTED
        assert event.provenance_level == ProvenanceLevel.RAW

    def test_raw_ingest_in_all_events_not_parrot_context(self):
        c = live_coordinator()
        c.record_raw_input(build_raw_ingest_payload(
            "IMAGE",
            "WEB_CAMERA",
            byte_size=1,
            content_sha256="d",
            storage_ref="/x.jpg",
            media_format="JPG",
        ))
        c.record_parrot_turn("hi", "hello")
        types_all = {e.event_type for e in c.store.all_events()}
        assert EventType.INPUT_RAW_INGESTED in types_all
        parrot_types = {e.event_type for e in c.store.parrot_context()}
        assert EventType.INPUT_RAW_INGESTED not in parrot_types

    def test_build_parrot_context_unchanged_after_raw_ingest(self):
        c = live_coordinator()
        nav = {"primary_rasa": "Shanta", "rasa_scores": {"Shanta": 1.0}}
        before = c.build_parrot_context("text", 1, nav)
        c.record_raw_input(build_raw_ingest_payload(
            "IMAGE",
            "WEB_FILE_UPLOAD",
            byte_size=100,
            content_sha256="x",
            storage_ref="/file.png",
            media_format="PNG",
        ))
        after = c.build_parrot_context("text", 1, nav)
        assert before == after

    def test_payload_has_no_embedded_bytes(self):
        c = live_coordinator()
        blob = b"binary-content-not-in-event"
        digest = sha256_bytes(blob)
        event = c.record_raw_input(build_raw_ingest_payload(
            "AUDIO",
            "WEB_MICROPHONE",
            byte_size=len(blob),
            content_sha256=digest,
            storage_ref="/disk/only.webm",
            media_format="WEBM",
        ))
        assert blob.decode("latin-1") not in str(event.payload.values())
        assert event.payload["storage_ref"] == "/disk/only.webm"

    def test_locked_session_rejects_raw_ingest(self):
        c = live_coordinator()
        c.lock()
        with pytest.raises(SessionLockedError):
            c.record_raw_input(build_raw_ingest_payload(
                "IMAGE",
                "WEB_FILE_UPLOAD",
                byte_size=1,
                content_sha256="a",
                storage_ref="/x",
                media_format="PNG",
            ))


class TestFlaskIngestRoute:

    def test_session_start_and_ingest_image(self):
        from interface_server import (
            FTP2_COORDINATORS,
            INGEST_MEDIA_DIR,
            app,
            begin_ftp2_participant_session,
        )

        client = app.test_client()
        start = client.post("/api/session/start")
        assert start.status_code == 200
        session_id = start.get_json()["session_id"]
        assert session_id in FTP2_COORDINATORS

        from io import BytesIO

        data = b"\x89PNG\r\n\x1a\n" + b"0" * 64
        response = client.post(
            "/api/input/ingest",
            data={
                "session_id": session_id,
                "modality": "IMAGE",
                "file": (BytesIO(data), "test.png"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["ok"] is True
        assert "analysis" not in body
        assert "gate" not in body

        coord = FTP2_COORDINATORS[session_id]
        raw_events = coord.store.events_of_type(EventType.INPUT_RAW_INGESTED)
        assert len(raw_events) == 1
        ref = raw_events[0].payload["storage_ref"]
        assert Path(ref).exists()
        assert Path(ref).read_bytes() == data
        assert session_id in ref

    def test_ingest_without_session_returns_404(self):
        from interface_server import app

        client = app.test_client()
        from io import BytesIO

        response = client.post(
            "/api/input/ingest",
            data={
                "session_id": str(uuid.uuid4()),
                "modality": "IMAGE",
                "file": (BytesIO(b"xx"), "x.png"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 404
