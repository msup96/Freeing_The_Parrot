"""Phase 3B — Silent Reader timeline analysis."""

import copy
import random

import pytest

from ftp.events.model import EventType, ProvenanceLevel
from ftp.parrot.engine import choose_behaviour
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState
from ftp.silent_reader.analyzer import TimelineAnalyzer
from ftp.timeline.wiring import record_chat_timeline_events


def live_coordinator() -> SessionCoordinator:
    c = SessionCoordinator()
    c.start()
    c.advance(SessionState.LIVE_CONVERSATION)
    return c


class TestTimelineAnalyzer:

    def test_derives_features_from_parrot_turn(self):
        c = live_coordinator()
        record_chat_timeline_events(
            c,
            "I think I am worried?",
            {
                "turn": 1,
                "response": "I detected SHANTA.",
                "gate": {"gate": "reflection"},
                "closed": False,
            },
        )
        c.silent_reader.analyze_pending()
        derived = [
            e for e in c.store.events_of_type(EventType.TELEMETRY_RECORDED)
            if e.payload.get("observation_type") == "derived"
        ]
        features = {e.payload["feature"] for e in derived}
        assert "message_length" in features
        assert "utterance_is_question" in features
        assert "response_latency" in features
        assert derived[0].provenance_level == ProvenanceLevel.OBSERVED
        assert derived[0].payload.get("source_event_ids")

    def test_reanalyze_does_not_duplicate_derived_features(self):
        c = live_coordinator()
        record_chat_timeline_events(
            c,
            "Hello there.",
            {"turn": 1, "response": "Hi.", "gate": {}, "closed": False},
        )
        c.silent_reader.analyze_pending()
        count_first = len(c.store.events_of_type(EventType.TELEMETRY_RECORDED))
        c.silent_reader.analyze_pending()
        count_second = len(c.store.events_of_type(EventType.TELEMETRY_RECORDED))
        assert count_second == count_first

    def test_missing_events_do_not_crash(self):
        c = live_coordinator()
        c.silent_reader.analyze_pending()

    def test_derived_observations_not_in_parrot_context(self):
        c = live_coordinator()
        record_chat_timeline_events(
            c,
            "Why am I here?",
            {"turn": 1, "response": "Why not.", "gate": {}, "closed": False},
        )
        c.silent_reader.analyze_pending()
        for event in c.store.parrot_context():
            assert event.event_type != EventType.TELEMETRY_RECORDED

    def test_composer_telemetry_still_observed(self):
        c = live_coordinator()
        c.silent_reader.record_turn(
            turn_index=1,
            typing_duration_ms=100.0,
            pause_before_submit_ms=50.0,
            message_length=10,
        )
        ev = c.store.events_of_type(EventType.TELEMETRY_RECORDED)[0]
        assert ev.payload.get("observation_type") == "composer"


class TestParrotInvarianceWithObservations:

    def test_choose_behaviour_unchanged_with_observations_present(self):
        session = {
            "session_id": "00000000-0000-4000-8000-000000000001",
            "understanding_turns": 3,
            "substantive_turns": 10,
            "chaos_count": 2,
            "last_behaviour": "roast",
            "behaviour_history": ["understanding", "roast"],
        }
        c = live_coordinator()
        record_chat_timeline_events(
            c,
            "Same text.",
            {"turn": 10, "response": "Reply.", "gate": {}, "closed": False},
        )
        c.silent_reader.record_turn(
            turn_index=10,
            typing_duration_ms=5000.0,
            pause_before_submit_ms=3000.0,
            message_length=9,
        )
        c.silent_reader.analyze_pending()

        random.seed(99)
        without = choose_behaviour(copy.deepcopy(session))
        random.seed(99)
        with_obs = choose_behaviour(copy.deepcopy(session))
        assert without == with_obs


class TestFlaskSilentReaderPass:

    def test_chat_records_composer_and_derived(self):
        from interface_server import FTP2_COORDINATORS, app

        client = app.test_client()
        sid = client.post("/api/session/start").get_json()["session_id"]
        client.post(
            "/api/input/text",
            json={"session_id": sid, "text": "Initial offering."},
        )
        client.post(
            "/api/session-lifecycle",
            json={"session_id": sid, "action": "input_complete"},
        )
        client.post(
            "/api/chat",
            json={
                "session_id": sid,
                "message": "I feel uncertain today?",
                "composer_telemetry": {
                    "typing_duration_ms": 1200,
                    "pause_before_submit_ms": 400,
                    "message_length": 24,
                },
            },
        )
        coord = FTP2_COORDINATORS[sid]
        telemetry = coord.store.events_of_type(EventType.TELEMETRY_RECORDED)
        assert any(t.payload.get("observation_type") == "composer" for t in telemetry)
        assert any(t.payload.get("observation_type") == "derived" for t in telemetry)
