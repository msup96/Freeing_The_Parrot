"""Pass 3 — live coordinator-private engagement snapshot."""

import pytest

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel
from ftp.session.coordinator import SessionCoordinator, _PARROT_FORBIDDEN_KEYS
from ftp.session.states import SessionState
from ftp.silent_reader.engagement import derive_behavioural_eligibility

_CLEAN_NAVARASA = {
    "primary_rasa": "Shanta",
    "rasa_scores": {"Shanta": 1.0},
    "sentiment": {"compound": 0.0},
}


def _live() -> SessionCoordinator:
    coordinator = SessionCoordinator()
    coordinator.start()
    coordinator.advance(SessionState.LIVE_CONVERSATION)
    return coordinator


def _fluctuating_turns(coordinator: SessionCoordinator) -> None:
    for message in ("a", "bbbbbbbbbbbb", "a"):
        coordinator.record_parrot_turn(message, "Reply.")


class TestLiveSnapshotAvailability:
    def test_snapshot_exists_during_live_conversation(self):
        coordinator = _live()
        coordinator.record_parrot_turn("hello", "Reply.")
        snapshot = coordinator.live_engagement_snapshot()
        assert snapshot["observation_kind"] == "live_engagement_snapshot"
        assert snapshot["session_id"] == coordinator.session_id

    def test_snapshot_updates_after_additional_turns(self):
        coordinator = _live()
        first = coordinator.live_engagement_snapshot()
        assert first["engagement_state"]["state"] == "insufficient"
        _fluctuating_turns(coordinator)
        second = coordinator.live_engagement_snapshot()
        assert second["engagement_state"]["state"] == "fluctuating"
        assert second["evidence"]["turn_count"] > first["evidence"]["turn_count"]

    def test_live_matches_post_lock_semantics_except_kind(self):
        coordinator = _live()
        _fluctuating_turns(coordinator)
        live = coordinator.live_engagement_snapshot()
        coordinator.lock()
        post = coordinator.synthesize_engagement()
        assert live["engagement_state"] == post["engagement_state"]
        assert live["behavioural_eligibility"] == post["behavioural_eligibility"]
        assert live["evidence"] == post["evidence"]
        assert live["observation_kind"] == "live_engagement_snapshot"
        assert post["observation_kind"] == "engagement_trajectory"

    def test_rejects_before_live_conversation(self):
        coordinator = SessionCoordinator()
        coordinator.start()
        with pytest.raises(ValueError, match="LIVE_CONVERSATION"):
            coordinator.live_engagement_snapshot()

    def test_rejects_after_lock(self):
        coordinator = _live()
        coordinator.record_parrot_turn("hello", "Reply.")
        coordinator.lock()
        with pytest.raises(ValueError, match="before session lock"):
            coordinator.live_engagement_snapshot()


class TestEngagementLabelsAndEligibility:
    @pytest.mark.parametrize(
        ("state", "fracture", "band", "recovery"),
        [
            ("insufficient", "ineligible", "none", "ineligible"),
            ("emerging", "ineligible", "none", "ineligible"),
            ("fluctuating", "ineligible", "none", "eligible"),
            ("declining", "ineligible", "none", "eligible"),
            ("sustained", "eligible", "low", "eligible"),
            ("high", "eligible", "moderate", "eligible"),
        ],
    )
    def test_derive_behavioural_eligibility_unchanged(
        self, state, fracture, band, recovery
    ):
        eligibility = derive_behavioural_eligibility(state)
        assert eligibility["fracture_eligibility"] == fracture
        assert eligibility["fracture_intensity_band"] == band
        assert eligibility["recovery_eligibility"] == recovery

    def test_insufficient_live_snapshot_fracture_ineligible(self):
        coordinator = _live()
        coordinator.record_parrot_turn("only one", "Reply.")
        eligibility = coordinator.live_engagement_snapshot()["behavioural_eligibility"]
        assert coordinator.live_engagement_snapshot()["engagement_state"]["state"] == "insufficient"
        assert eligibility["fracture_eligibility"] == "ineligible"

    def test_sustained_live_snapshot_fracture_eligible(self):
        coordinator = _live()
        coordinator.record_parrot_turn("I am staying with this conversation.", "Reply.")
        coordinator.record_parrot_turn("I want to understand what you mean.", "Reply.")
        coordinator.record_parrot_turn("I am still here and I want to keep talking.", "Reply.")
        snapshot = coordinator.live_engagement_snapshot()
        assert snapshot["engagement_state"]["state"] in {"sustained", "high"}
        assert snapshot["behavioural_eligibility"]["fracture_eligibility"] == "eligible"

    def test_current_turn_relationship_signal_is_private(self):
        coordinator = _live()
        snapshot = coordinator.live_engagement_snapshot(
            current_turn_text="Why did you say that? I am still trying to understand you."
        )
        assert snapshot["relationship"]["parrot_directed"] is True
        assert snapshot["relationship"]["disengagement"] is False
        assert snapshot["relationship"]["trust_delta"] > 0

    def test_emerging_live_snapshot_fracture_ineligible(self):
        coordinator = _live()
        coordinator.record_parrot_turn("first line", "Reply.")
        coordinator.record_parrot_turn("second line", "Reply.")
        snapshot = coordinator.live_engagement_snapshot()
        assert snapshot["engagement_state"]["state"] == "emerging"
        assert snapshot["behavioural_eligibility"]["fracture_eligibility"] == "ineligible"


class TestPrivacyAndIsolation:
    def test_snapshot_not_in_parrot_context(self):
        coordinator = _live()
        coordinator.record_parrot_turn("hello", "Reply.")
        coordinator.live_engagement_snapshot()
        ctx = coordinator.build_parrot_context("hello", 1, _CLEAN_NAVARASA)
        for forbidden in _PARROT_FORBIDDEN_KEYS:
            assert forbidden not in ctx
            assert forbidden not in ctx["parrot_session"]

    def test_snapshot_does_not_write_events(self):
        coordinator = _live()
        _fluctuating_turns(coordinator)
        before = len(coordinator.store.all_events())
        coordinator.live_engagement_snapshot()
        assert len(coordinator.store.all_events()) == before

    def test_no_new_event_types_introduced(self):
        before = {member.value for member in EventType}
        coordinator = _live()
        coordinator.record_parrot_turn("hello", "Reply.")
        coordinator.live_engagement_snapshot()
        after = {member.value for member in EventType}
        assert after == before

    def test_no_evidence_bundle_or_profile_fields(self):
        coordinator = _live()
        coordinator.record_parrot_turn("hello", "Reply.")
        coordinator.store.append(
            InteractionEvent(
                session_id=coordinator.session_id,
                event_type=EventType.CARDS_GENERATED,
                provenance_level=ProvenanceLevel.INFERRED,
                payload={
                    "reading_profile": {"secret": True},
                    "hidden_provenance": {"inference_ids": ["x"]},
                },
            )
        )
        snapshot = coordinator.live_engagement_snapshot()
        blob = str(snapshot)
        assert "reading_profile" not in blob
        assert "hidden_provenance" not in blob
        assert "evidence_bundle" not in blob
        assert "candidate_inference" not in blob

    def test_no_cross_session_leakage(self):
        a = _live()
        b = _live()
        _fluctuating_turns(a)
        b.record_parrot_turn("solo", "Reply.")
        assert a.live_engagement_snapshot()["engagement_state"]["state"] == "fluctuating"
        assert b.live_engagement_snapshot()["engagement_state"]["state"] == "insufficient"
        assert a.session_id != b.session_id

    def test_purge_discards_coordinator_snapshot_access(self):
        coordinator = _live()
        coordinator.record_parrot_turn("hello", "Reply.")
        coordinator.live_engagement_snapshot()
        coordinator._on_state_change(
            SessionState.OUTPUT_GENERATION,
            SessionState.PURGE_AND_RESET,
        )
        fresh = _live()
        assert fresh.live_engagement_snapshot()["engagement_state"]["state"] == "insufficient"


class TestApiNotExposed:
    def test_chat_response_has_no_engagement_fields(self, monkeypatch, tmp_path):
        import interface_server as server

        monkeypatch.setattr(server, "DB_FILE", tmp_path / "chat.sqlite3")
        client = server.app.test_client()
        session_id = client.post("/api/session/start").get_json()["session_id"]
        client.post(
            "/api/input/text",
            json={"session_id": session_id, "text": "Initial offering."},
        )
        client.post(
            "/api/session-lifecycle",
            json={"session_id": session_id, "action": "input_complete"},
        )
        result = client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "I feel uncertain."},
        ).get_json()
        forbidden = (
            "engagement_state",
            "engagement_score",
            "behavioural_eligibility",
            "live_engagement_snapshot",
        )
        for key in forbidden:
            assert key not in result
