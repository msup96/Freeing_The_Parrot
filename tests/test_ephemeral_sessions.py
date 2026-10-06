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
