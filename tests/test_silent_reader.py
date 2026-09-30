"""Phase 3A tests – Silent Reader observation layer."""

import copy
import random

import pytest

from ftp.events.model import EventType, ProvenanceLevel
from ftp.parrot.engine import choose_behaviour
from ftp.session.coordinator import SessionCoordinator, SessionLockedError
from ftp.session.states import SessionState

_CLEAN_NAVARASA = {
    "primary_rasa": "Shanta",
    "rasa_scores": {"Shanta": 1.0},
    "sentiment": {"compound": 0.0},
}


def live_coordinator() -> SessionCoordinator:
    c = SessionCoordinator()
    c.start()
    c.advance(SessionState.LIVE_CONVERSATION)
    return c


def _fixed_parrot_session() -> dict:
    return {
        "session_id": "00000000-0000-4000-8000-000000000001",
        "understanding_turns": 3,
        "substantive_turns": 10,
        "chaos_count": 2,
        "last_behaviour": "roast",
        "behaviour_history": ["understanding", "roast"],
    }


class TestTelemetryRecording:

    def test_recorded_as_telemetry_recorded_event_type(self):
        c = live_coordinator()
        c.silent_reader.record_turn(
            turn_index=1,
            typing_duration_ms=1200.0,
            pause_before_submit_ms=340.0,
            message_length=18,
        )
        events = c.store.events_of_type(EventType.TELEMETRY_RECORDED)
        assert len(events) == 1
        assert events[0].event_type == EventType.TELEMETRY_RECORDED

    def test_telemetry_provenance_is_observed(self):
        c = live_coordinator()
        stamped = c.silent_reader.record_turn(
            turn_index=1,
            typing_duration_ms=500.0,
            pause_before_submit_ms=100.0,
            message_length=5,
        )
        assert stamped.provenance_level == ProvenanceLevel.OBSERVED

    def test_telemetry_payload_contains_phase_3a_signals(self):
        c = live_coordinator()
        c.silent_reader.record_turn(
            turn_index=2,
            typing_duration_ms=2500.5,
            pause_before_submit_ms=800.25,
            message_length=42,
        )
        payload = c.store.events_of_type(EventType.TELEMETRY_RECORDED)[0].payload
        assert payload["turn"] == 2
        assert payload["typing_duration_ms"] == 2500.5
        assert payload["pause_before_submit_ms"] == 800.25
        assert payload["message_length"] == 42

    def test_telemetry_in_all_events(self):
        c = live_coordinator()
        c.silent_reader.record_turn(
            turn_index=1,
            typing_duration_ms=1.0,
            pause_before_submit_ms=2.0,
            message_length=3,
        )
        types = {e.event_type for e in c.store.all_events()}
        assert EventType.TELEMETRY_RECORDED in types

    def test_telemetry_absent_from_parrot_context(self):
        c = live_coordinator()
        c.silent_reader.record_turn(
            turn_index=1,
            typing_duration_ms=9999.0,
            pause_before_submit_ms=8888.0,
            message_length=77,
        )
        parrot_view = c.store.parrot_context()
        assert all(
            e.event_type != EventType.TELEMETRY_RECORDED for e in parrot_view
        )
        assert parrot_view == ()


class TestTelemetryInvariants:

    def test_recording_telemetry_does_not_change_session_state(self):
        c = live_coordinator()
        before = c.state
        c.silent_reader.record_turn(
            turn_index=1,
            typing_duration_ms=100.0,
            pause_before_submit_ms=50.0,
            message_length=10,
        )
        assert c.state == before
        assert c.state == SessionState.LIVE_CONVERSATION

    def test_telemetry_does_not_change_choose_behaviour(self):
        session = _fixed_parrot_session()
        seed = 42

        random.seed(seed)
        without_telemetry = choose_behaviour(copy.deepcopy(session))

        c = live_coordinator()
        c.silent_reader.record_turn(
            turn_index=10,
            typing_duration_ms=50000.0,
            pause_before_submit_ms=30000.0,
            message_length=9999,
        )

        random.seed(seed)
        with_telemetry = choose_behaviour(copy.deepcopy(session))

        assert without_telemetry == with_telemetry

    def test_build_parrot_context_unchanged_after_telemetry(self):
        c = live_coordinator()
        c.silent_reader.record_turn(
            turn_index=1,
            typing_duration_ms=1.0,
            pause_before_submit_ms=2.0,
            message_length=3,
        )
        ctx = c.build_parrot_context(
            turn_text="Same input.",
            turn_index=4,
            navarasa_result=_CLEAN_NAVARASA,
        )
        assert set(ctx.keys()) == {
            "turn_text",
            "turn_index",
            "navarasa_result",
            "parrot_session",
        }
        assert ctx["turn_text"] == "Same input."
        assert "typing_duration_ms" not in ctx
        assert "message_length" not in ctx["parrot_session"]


class TestSessionLock:

    def test_locked_session_rejects_record_parrot_turn(self):
        c = live_coordinator()
        c.lock()
        assert c.state == SessionState.SESSION_CONCLUDED
        with pytest.raises(SessionLockedError):
            c.record_parrot_turn("late text", "late reply")

    def test_turn_count_unchanged_when_parrot_turn_rejected(self):
        c = live_coordinator()
        c.record_parrot_turn("one", "reply")
        assert c.turn_count == 1
        c.lock()
        with pytest.raises(SessionLockedError):
            c.record_parrot_turn("two", "reply")
        assert c.turn_count == 1


class TestSameSessionIsolation:

    def test_telemetry_leaves_parrot_context_and_build_parrot_context_unchanged(self):
        c = live_coordinator()
        c.record(
            event_type=EventType.NAVARASA_CLASSIFIED,
            provenance_level=ProvenanceLevel.INTERPRETED,
            payload={"primary_rasa": "Shanta", "turn": 1},
        )
        c.record_parrot_turn(
            turn_text="I feel uncertain.",
            reply="I detected SHANTA.",
            behaviour="understanding",
            gate="reflection",
        )

        context_before = c.build_parrot_context(
            turn_text="I feel uncertain.",
            turn_index=1,
            navarasa_result=_CLEAN_NAVARASA,
        )
        parrot_before = c.store.parrot_context()

        c.silent_reader.record_turn(
            turn_index=1,
            typing_duration_ms=1200.0,
            pause_before_submit_ms=340.0,
            message_length=18,
        )

        context_after = c.build_parrot_context(
            turn_text="I feel uncertain.",
            turn_index=1,
            navarasa_result=_CLEAN_NAVARASA,
        )
        parrot_after = c.store.parrot_context()

        assert any(
            event.event_type == EventType.TELEMETRY_RECORDED
            for event in c.store.all_events()
        )
        assert [event.event_id for event in parrot_before] == [
            event.event_id for event in parrot_after
        ]
        assert parrot_before == parrot_after
        assert context_before == context_after

    def test_mixed_events_hide_telemetry_from_parrot_context(self):
        c = live_coordinator()
        c.record(
            event_type=EventType.NAVARASA_CLASSIFIED,
            provenance_level=ProvenanceLevel.INTERPRETED,
            payload={"primary_rasa": "Karuna", "turn": 1},
        )
        c.record_parrot_turn(
            turn_text="I miss them.",
            reply="I detected KARUNA.",
            behaviour="understanding",
            gate="reflection",
        )
        c.silent_reader.record_turn(
            turn_index=1,
            typing_duration_ms=800.0,
            pause_before_submit_ms=200.0,
            message_length=12,
        )

        visible = {event.event_type for event in c.store.parrot_context()}
        assert EventType.PARROT_TURN_GENERATED in visible
        assert EventType.NAVARASA_CLASSIFIED in visible
        assert EventType.TELEMETRY_RECORDED not in visible


class TestTelemetryGuard:

    def test_telemetry_outside_live_conversation_raises(self):
        c = SessionCoordinator()
        c.start()
        assert c.state == SessionState.INPUT_INGESTION
        with pytest.raises(ValueError, match="LIVE_CONVERSATION"):
            c.record_turn_telemetry(
                turn_index=1,
                typing_duration_ms=1.0,
                pause_before_submit_ms=1.0,
                message_length=1,
            )
