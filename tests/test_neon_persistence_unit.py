from __future__ import annotations

import pytest

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel
from ftp.session import neon_persistence


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self, responses):
        self.responses = list(responses)
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.statements.append((query, params))
        return FakeCursor(self.responses.pop(0) if self.responses else [])


def test_purge_expired_sessions_deletes_expired_rows_and_returns_ids(monkeypatch):
    connection = FakeConnection([[("expired-1",), ("expired-2",)]])
    monkeypatch.setattr(neon_persistence.psycopg, "connect", lambda _url: connection)
    adapter = neon_persistence.NeonSessionPersistence("postgresql://test")

    assert adapter.purge_expired_sessions() == ["expired-1", "expired-2"]
    query, params = connection.statements[0]
    assert "DELETE FROM ftp_sessions" in query
    assert "expires_at <= CURRENT_TIMESTAMP" in query
    assert "RETURNING session_id" in query
    assert params is None


def test_delete_session_returns_true_when_a_row_is_deleted(monkeypatch):
    connection = FakeConnection([[("session-1",)]])
    monkeypatch.setattr(neon_persistence.psycopg, "connect", lambda _url: connection)
    adapter = neon_persistence.NeonSessionPersistence("postgresql://test")

    assert adapter.delete_session("session-1") is True
    query, params = connection.statements[0]
    assert "DELETE FROM ftp_sessions" in query
    assert params == ("session-1",)


def test_delete_session_returns_false_when_session_is_missing(monkeypatch):
    connection = FakeConnection([[]])
    monkeypatch.setattr(neon_persistence.psycopg, "connect", lambda _url: connection)
    adapter = neon_persistence.NeonSessionPersistence("postgresql://test")

    assert adapter.delete_session("missing") is False


def test_build_neon_persistence_stays_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FTP_DURABLE_SESSIONS", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert neon_persistence.build_neon_persistence() is None


def test_build_neon_persistence_requires_database_url_when_enabled(monkeypatch):
    monkeypatch.setenv("FTP_DURABLE_SESSIONS", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        neon_persistence.build_neon_persistence()



def test_approved_archive_writes_session_events_and_consent_in_one_transaction(monkeypatch):
    connection = FakeConnection([])
    monkeypatch.setattr(neon_persistence.psycopg, "connect", lambda _url: connection)
    adapter = neon_persistence.NeonSessionPersistence("postgresql://test")
    event = InteractionEvent(
        session_id="session-1",
        event_type=EventType.CONSENT_RECORDED,
        provenance_level=ProvenanceLevel.OBSERVED,
        payload={"consent_type": "SHARE"},
        sequence_num=3,
        event_id="event-consent",
        timestamp="2026-10-09T10:00:00+00:00",
    )

    raw_turn = InteractionEvent(
        session_id="session-1",
        event_type=EventType.PARROT_TURN_GENERATED,
        provenance_level=ProvenanceLevel.OBSERVED,
        payload={"user_text": "private raw transcript", "reply": "parrot reply"},
        sequence_num=2,
        event_id="event-raw-turn",
        timestamp="2026-10-09T09:59:00+00:00",
    )
    adapter.persist_approved_archive(
        "session-1",
        "2026-10-09T11:00:00Z",
        [raw_turn, event],
        {"reveals": {"snapshot": "shown-to-participant"}},
        consent_type="SHARE",
    )

    assert len(connection.statements) == 3
    session_sql, session_params = connection.statements[0]
    event_sql, event_params = connection.statements[1]
    consent_sql, consent_params = connection.statements[2]
    assert "INSERT INTO ftp_sessions" in session_sql
    assert "INSERT INTO ftp_session_events" in event_sql
    assert "ON CONFLICT DO NOTHING" in event_sql
    # The raw conversation event is not written; only the consent/provenance
    # event is archived by this fixture.
    assert "INSERT INTO ftp_session_consents" in consent_sql
    assert session_params[0] == "session-1"
    assert event_params[0:5] == (
        "session-1", 3, "event-consent", "CONSENT_RECORDED", "OBSERVED"
    )
    assert consent_params == ("session-1", "SHARE")


def test_approved_archive_rejects_private_consent_before_any_database_write(monkeypatch):
    connection = FakeConnection([])
    monkeypatch.setattr(neon_persistence.psycopg, "connect", lambda _url: connection)
    adapter = neon_persistence.NeonSessionPersistence("postgresql://test")

    with pytest.raises(ValueError, match="explicit SHARE consent"):
        adapter.persist_approved_archive(
            "session-1", "2026-10-09T11:00:00Z", [], {}, consent_type="KEEP_PRIVATE"
        )

    assert connection.statements == []
