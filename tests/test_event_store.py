"""Phase 2 tests – Event ordering, persistence, and monotonic sequencing.

Covers TEST_STRATEGY.md §2.3:
- test_event_immutability (in-memory equivalent)
- test_microsecond_monotonicity
"""

import threading
import time
import uuid

import pytest

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel
from ftp.events.store import EventStore, StrictBoundaryViolationError


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_store() -> tuple[EventStore, str]:
    sid = str(uuid.uuid4())
    return EventStore(session_id=sid), sid


def make_event(session_id: str, event_type: EventType = EventType.NAVARASA_CLASSIFIED) -> InteractionEvent:
    return InteractionEvent(
        session_id=session_id,
        event_type=event_type,
        provenance_level=ProvenanceLevel.INTERPRETED,
        payload={"primary_rasa": "Shanta"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Monotonic sequencing
# ─────────────────────────────────────────────────────────────────────────────

class TestMonotonicSequencing:

    def test_first_event_gets_sequence_1(self):
        store, sid = make_store()
        stamped = store.append(make_event(sid))
        assert stamped.sequence_num == 1

    def test_sequence_numbers_are_contiguous(self):
        store, sid = make_store()
        events = [store.append(make_event(sid)) for _ in range(20)]
        nums = [e.sequence_num for e in events]
        assert nums == list(range(1, 21))

    def test_sequence_never_decreases(self):
        store, sid = make_store()
        for _ in range(50):
            store.append(make_event(sid))
        seqs = [e.sequence_num for e in store.all_events()]
        for a, b in zip(seqs, seqs[1:]):
            assert b > a, f"Sequence went backwards: {a} -> {b}"

    def test_concurrent_appends_produce_unique_sequences(self):
        """100 concurrent threads must produce 100 distinct sequence numbers."""
        store, sid = make_store()
        results: list[int] = []
        lock = threading.Lock()

        def worker():
            stamped = store.append(make_event(sid))
            with lock:
                results.append(stamped.sequence_num)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 100
        assert len(set(results)) == 100, "Duplicate sequence numbers detected."
        assert sorted(results) == list(range(1, 101))

    def test_sequence_matches_store_length(self):
        store, sid = make_store()
        for i in range(1, 11):
            store.append(make_event(sid))
            assert len(store) == i


# ─────────────────────────────────────────────────────────────────────────────
# Immutability & session isolation
# ─────────────────────────────────────────────────────────────────────────────

class TestImmutabilityAndIsolation:

    def test_appended_event_is_frozen(self):
        store, sid = make_store()
        stamped = store.append(make_event(sid))
        with pytest.raises((AttributeError, TypeError)):
            stamped.sequence_num = 999  # type: ignore[misc]

    def test_snapshot_is_immutable_tuple(self):
        store, sid = make_store()
        store.append(make_event(sid))
        snapshot = store.all_events()
        assert isinstance(snapshot, tuple)
        with pytest.raises((TypeError, AttributeError)):
            snapshot[0] = None  # type: ignore[index]

    def test_wrong_session_id_rejected(self):
        store, _ = make_store()
        alien_event = InteractionEvent(
            session_id=str(uuid.uuid4()),   # different UUID
            event_type=EventType.NAVARASA_CLASSIFIED,
            provenance_level=ProvenanceLevel.INTERPRETED,
            payload={},
        )
        with pytest.raises(ValueError, match="session_id"):
            store.append(alien_event)

    def test_two_stores_are_completely_independent(self):
        store_a, sid_a = make_store()
        store_b, sid_b = make_store()
        assert sid_a != sid_b

        for _ in range(5):
            store_a.append(make_event(sid_a))
        store_b.append(make_event(sid_b))

        assert len(store_a) == 5
        assert len(store_b) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Filtering & Parrot read-path
# ─────────────────────────────────────────────────────────────────────────────

class TestReadPaths:

    def test_events_of_type_filters_correctly(self):
        store, sid = make_store()
        store.append(make_event(sid, EventType.NAVARASA_CLASSIFIED))
        store.append(make_event(sid, EventType.PARROT_TURN_GENERATED))
        store.append(make_event(sid, EventType.SESSION_STARTED))
        store.append(make_event(sid, EventType.NAVARASA_CLASSIFIED))

        navarasa_only = store.events_of_type(EventType.NAVARASA_CLASSIFIED)
        assert len(navarasa_only) == 2
        assert all(
            e.event_type == EventType.NAVARASA_CLASSIFIED
            for e in navarasa_only
        )

    def test_parrot_context_excludes_non_eligible_events(self):
        store, sid = make_store()
        store.append(make_event(sid, EventType.SESSION_STARTED))
        store.append(make_event(sid, EventType.NAVARASA_CLASSIFIED))
        store.append(make_event(sid, EventType.PARROT_TURN_GENERATED))
        store.append(make_event(sid, EventType.TELEMETRY_RECORDED))
        store.append(make_event(sid, EventType.CARDS_GENERATED))

        parrot_view = store.parrot_context()

        assert len(parrot_view) == 2
        for e in parrot_view:
            assert e.is_live_parrot_eligible(), (
                f"Non-eligible event {e.event_type} slipped through parrot_context()"
            )

    def test_parrot_context_never_contains_telemetry(self):
        store, sid = make_store()
        store.append(make_event(sid, EventType.TELEMETRY_RECORDED))
        store.append(make_event(sid, EventType.OCR_TEXT_EXTRACTED))
        store.append(make_event(sid, EventType.SESSION_LOCKED))

        assert store.parrot_context() == ()

    def test_parrot_context_never_contains_cards_or_profile(self):
        store, sid = make_store()
        for etype in (
            EventType.CARDS_GENERATED,
            EventType.CARD_RESONANCE_MARKED,
            EventType.PROFILE_REVEAL_VIEWED,
            EventType.CONSENT_RECORDED,
        ):
            store.append(make_event(sid, etype))

        assert store.parrot_context() == ()


# ─────────────────────────────────────────────────────────────────────────────
# Boundary violation assertion
# ─────────────────────────────────────────────────────────────────────────────

class TestBoundaryViolationAssertion:

    def _make_forbidden_event(self, session_id: str, forbidden_key: str) -> InteractionEvent:
        return InteractionEvent(
            session_id=session_id,
            event_type=EventType.PARROT_TURN_GENERATED,
            provenance_level=ProvenanceLevel.OBSERVED,
            payload={forbidden_key: "some_value"},
        )

    @pytest.mark.parametrize("forbidden_key", [
        "silent_reader_telemetry",
        "gemini_inferences",
        "profile_data",
        "card_selections",
        "participant_profile",
        "gender_inference",
        "identity_inference",
        "long_term_history",
    ])
    def test_forbidden_payload_keys_raise_boundary_error(self, forbidden_key):
        store, sid = make_store()
        event = self._make_forbidden_event(sid, forbidden_key)
        with pytest.raises(StrictBoundaryViolationError, match="boundary violation"):
            store.assert_no_forbidden_payload(event)

    def test_clean_payload_passes_boundary_check(self):
        store, sid = make_store()
        clean_event = InteractionEvent(
            session_id=sid,
            event_type=EventType.PARROT_TURN_GENERATED,
            provenance_level=ProvenanceLevel.OBSERVED,
            payload={"behaviour": "understanding", "gate": "reflection"},
        )
        # Should not raise
        store.assert_no_forbidden_payload(clean_event)

    def test_event_id_is_unique_per_event(self):
        store, sid = make_store()
        events = [store.append(make_event(sid)) for _ in range(50)]
        ids = [e.event_id for e in events]
        assert len(set(ids)) == 50, "Duplicate event_ids detected."
