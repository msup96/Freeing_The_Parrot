"""Phase 2 tests – Session identity and full lifecycle via SessionCoordinator.

Covers:
- Session identity (UUID generation, uniqueness, created_at)
- SessionCoordinator: start(), advance(), record(), record_parrot_turn(), lock()
- Events emitted at each lifecycle milestone
- Turn counting
- Coordinator state tracking
"""

import uuid

import pytest

from ftp.events.model import EventType, ProvenanceLevel
from ftp.session.coordinator import SessionCoordinator
from ftp.session.machine import IllegalTransitionError
from ftp.session.states import SessionState
from ftp.session.identity import SessionIdentity


# ─────────────────────────────────────────────────────────────────────────────
# Session identity
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionIdentity:

    def test_generates_valid_uuid_by_default(self):
        si = SessionIdentity()
        parsed = uuid.UUID(si.session_id)
        assert str(parsed) == si.session_id

    def test_accepts_pre_existing_session_id(self):
        fixed = str(uuid.uuid4())
        si = SessionIdentity(session_id=fixed)
        assert si.session_id == fixed

    def test_every_new_identity_has_unique_session_id(self):
        ids = {SessionIdentity().session_id for _ in range(200)}
        assert len(ids) == 200

    def test_created_at_is_iso8601(self):
        import datetime
        si = SessionIdentity()
        # Should parse without raising
        dt = datetime.datetime.fromisoformat(si.created_at)
        assert dt.tzinfo is not None  # timezone-aware

    def test_to_dict_contains_required_keys(self):
        si = SessionIdentity()
        d = si.to_dict()
        assert "session_id" in d
        assert "created_at" in d
        assert d["session_id"] == si.session_id


# ─────────────────────────────────────────────────────────────────────────────
# Coordinator construction
# ─────────────────────────────────────────────────────────────────────────────

class TestCoordinatorConstruction:

    def test_starts_in_idle_standby(self):
        c = SessionCoordinator()
        assert c.state == SessionState.IDLE_STANDBY

    def test_session_id_is_valid_uuid(self):
        c = SessionCoordinator()
        uuid.UUID(c.session_id)

    def test_accepts_pre_provided_session_id(self):
        fixed = str(uuid.uuid4())
        c = SessionCoordinator(session_id=fixed)
        assert c.session_id == fixed

    def test_turn_count_starts_at_zero(self):
        c = SessionCoordinator()
        assert c.turn_count == 0

    def test_store_session_id_matches_coordinator_session_id(self):
        c = SessionCoordinator()
        assert c.store.session_id == c.session_id


# ─────────────────────────────────────────────────────────────────────────────
# Start lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestCoordinatorStart:

    def test_start_transitions_to_input_ingestion(self):
        c = SessionCoordinator()
        c.start()
        assert c.state == SessionState.INPUT_INGESTION

    def test_start_emits_session_started_event(self):
        c = SessionCoordinator()
        c.start()
        started_events = c.store.events_of_type(EventType.SESSION_STARTED)
        assert len(started_events) == 1

    def test_start_emits_state_changed_event(self):
        c = SessionCoordinator()
        c.start()
        changed_events = c.store.events_of_type(EventType.SESSION_STATE_CHANGED)
        assert len(changed_events) >= 1

    def test_session_started_payload_contains_session_id(self):
        c = SessionCoordinator()
        c.start()
        event = c.store.events_of_type(EventType.SESSION_STARTED)[0]
        assert event.payload["session_id"] == c.session_id


# ─────────────────────────────────────────────────────────────────────────────
# Advance (state transitions via coordinator)
# ─────────────────────────────────────────────────────────────────────────────

class TestCoordinatorAdvance:

    def test_advance_changes_state(self):
        c = SessionCoordinator()
        c.start()
        c.advance(SessionState.LIVE_CONVERSATION)
        assert c.state == SessionState.LIVE_CONVERSATION

    def test_illegal_advance_raises_and_preserves_state(self):
        c = SessionCoordinator()
        # From IDLE_STANDBY, jumping to LIVE_CONVERSATION is illegal
        with pytest.raises(IllegalTransitionError):
            c.advance(SessionState.LIVE_CONVERSATION)
        assert c.state == SessionState.IDLE_STANDBY

    def test_every_advance_emits_state_changed_event(self):
        c = SessionCoordinator()
        c.start()  # → INPUT_INGESTION
        c.advance(SessionState.LIVE_CONVERSATION)

        state_events = c.store.events_of_type(EventType.SESSION_STATE_CHANGED)
        # At least one for each transition (start() does one, advance() does one)
        assert len(state_events) >= 2


# ─────────────────────────────────────────────────────────────────────────────
# Recording events
# ─────────────────────────────────────────────────────────────────────────────

class TestCoordinatorRecord:

    def test_record_appends_to_store(self):
        c = SessionCoordinator()
        c.record(
            event_type=EventType.NAVARASA_CLASSIFIED,
            provenance_level=ProvenanceLevel.INTERPRETED,
            payload={"primary_rasa": "Karuna"},
        )
        navarasa = c.store.events_of_type(EventType.NAVARASA_CLASSIFIED)
        assert len(navarasa) == 1

    def test_recorded_event_session_id_matches_coordinator(self):
        c = SessionCoordinator()
        stamped = c.record(
            event_type=EventType.NAVARASA_CLASSIFIED,
            provenance_level=ProvenanceLevel.INTERPRETED,
            payload={},
        )
        assert stamped.session_id == c.session_id

    def test_events_are_monotonically_sequenced(self):
        c = SessionCoordinator()
        c.start()
        c.advance(SessionState.LIVE_CONVERSATION)
        for _ in range(5):
            c.record(
                event_type=EventType.NAVARASA_CLASSIFIED,
                provenance_level=ProvenanceLevel.INTERPRETED,
                payload={},
            )
        seqs = [e.sequence_num for e in c.store.all_events()]
        assert seqs == sorted(seqs)
        assert seqs == list(range(1, len(seqs) + 1))


# ─────────────────────────────────────────────────────────────────────────────
# Turn counting
# ─────────────────────────────────────────────────────────────────────────────

class TestTurnCounting:

    def test_record_parrot_turn_increments_count(self):
        c = SessionCoordinator()
        c.start()
        c.advance(SessionState.LIVE_CONVERSATION)

        for expected in range(1, 6):
            c.record_parrot_turn(
                turn_text="Hello.",
                reply="Hello registered.",
                behaviour="understanding",
                gate="reflection",
            )
            assert c.turn_count == expected

    def test_record_parrot_turn_emits_correct_event_type(self):
        c = SessionCoordinator()
        c.start()
        c.advance(SessionState.LIVE_CONVERSATION)
        c.record_parrot_turn("test input", "test reply")

        events = c.store.events_of_type(EventType.PARROT_TURN_GENERATED)
        assert len(events) == 1
        assert events[0].payload["turn_index"] == 1

    def test_turn_payload_contains_user_text(self):
        c = SessionCoordinator()
        c.start()
        c.advance(SessionState.LIVE_CONVERSATION)
        c.record_parrot_turn("I feel uncertain.", "Interesting.")

        ev = c.store.events_of_type(EventType.PARROT_TURN_GENERATED)[0]
        assert ev.payload["user_text"] == "I feel uncertain."
        assert ev.payload["parrot_reply"] == "Interesting."


# ─────────────────────────────────────────────────────────────────────────────
# Lock
# ─────────────────────────────────────────────────────────────────────────────

class TestCoordinatorLock:

    def test_lock_transitions_to_session_concluded(self):
        c = SessionCoordinator()
        c.start()
        c.advance(SessionState.LIVE_CONVERSATION)
        c.lock()
        assert c.state == SessionState.SESSION_CONCLUDED

    def test_lock_emits_session_locked_event(self):
        c = SessionCoordinator()
        c.start()
        c.advance(SessionState.LIVE_CONVERSATION)
        c.lock()

        locked = c.store.events_of_type(EventType.SESSION_LOCKED)
        assert len(locked) == 1

    def test_locked_event_payload_contains_turn_count(self):
        c = SessionCoordinator()
        c.start()
        c.advance(SessionState.LIVE_CONVERSATION)
        for _ in range(3):
            c.record_parrot_turn("text", "reply")
        c.lock()

        ev = c.store.events_of_type(EventType.SESSION_LOCKED)[0]
        assert ev.payload["final_turn_count"] == 3

    def test_machine_is_locked_after_coordinator_lock(self):
        c = SessionCoordinator()
        c.start()
        c.advance(SessionState.LIVE_CONVERSATION)
        c.lock()
        assert c.machine.is_locked()


# ─────────────────────────────────────────────────────────────────────────────
# Multiple sessions are independent
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionIsolation:

    def test_two_coordinators_have_different_session_ids(self):
        a = SessionCoordinator()
        b = SessionCoordinator()
        assert a.session_id != b.session_id

    def test_events_from_one_session_do_not_appear_in_another(self):
        a = SessionCoordinator()
        b = SessionCoordinator()

        a.start()
        a.advance(SessionState.LIVE_CONVERSATION)
        a.record_parrot_turn("hello", "world")

        b.start()

        a_events = {e.session_id for e in a.store.all_events()}
        b_events = {e.session_id for e in b.store.all_events()}

        assert a_events == {a.session_id}
        assert b_events == {b.session_id}
        assert a_events.isdisjoint(b_events)
