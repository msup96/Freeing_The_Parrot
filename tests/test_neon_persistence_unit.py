from __future__ import annotations

import pytest

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
