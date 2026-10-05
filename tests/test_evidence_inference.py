"""Phase 4A — evidence bundle and inference contract."""

import pytest

from ftp.events.model import EventType, ProvenanceLevel
from ftp.events.store import StrictBoundaryViolationError
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState
from ftp.silent_reader.inference import (
    apply_evidence_contract,
    resonance_marker,
    support_confidence,
    unique_signal_types,
)


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


def _locked(*messages: str) -> SessionCoordinator:
    coordinator = _live()
    for message in messages:
        coordinator.record_parrot_turn(message, "Reply.")
    coordinator.lock()
    return coordinator


class TestEvidenceBundle:
    def test_requires_lock(self):
        coordinator = _live()
        coordinator.record_parrot_turn("still live", "ok")
        with pytest.raises(ValueError, match="locked"):
            coordinator.build_evidence_bundle()

    def test_deterministic_and_isolated(self):
        first = _locked("aa", "bbbb", "aa?")
        second = _locked("hello", "there")
        assert first.build_evidence_bundle() == first.build_evidence_bundle()
        assert first.build_evidence_bundle()["session_id"] != (
            second.build_evidence_bundle()["session_id"]
        )

    def test_preserves_event_ids_and_provenance(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        assert bundle["provenance_level"] == ProvenanceLevel.INTERPRETED.value
        length = next(item for item in bundle["evidence_items"] if item["signal_type"] == "message_length")
        assert length["provenance_level"] == ProvenanceLevel.OBSERVED.value
        assert length["source_event_ids"]
        stored = {event.event_id for event in coordinator.store.events_of_type(EventType.PARROT_TURN_GENERATED)}
        assert set(length["source_event_ids"]) <= stored

    def test_missing_latency_stays_listed_as_unavailable(self):
        bundle = _locked("aa", "bbbb").build_evidence_bundle()
        assert "response_latency_unavailable" in bundle["limitations"]
        assert "user_text" not in str(bundle)

    def test_does_not_mutate_store_or_temporal_output(self):
        coordinator = _locked("aa", "bbbb", "aa")
        before = coordinator.synthesize_temporal_trajectories()
        count = len(coordinator.store.all_events())
        coordinator.build_evidence_bundle()
        coordinator.evaluate_session_inferences()
        assert coordinator.synthesize_temporal_trajectories() == before
        assert len(coordinator.store.all_events()) == count

    def test_empty_session_is_insufficient(self):
        coordinator = _live()
        coordinator.lock()
        bundle = coordinator.build_evidence_bundle()
        assert bundle["status"] == "insufficient"
        assert "fewer_than_two_turns" in bundle["limitations"]


class TestEvidenceContract:
    def test_repeated_signal_counts_once(self):
        items = [
            {"signal_type": "message_length"},
            {"signal_type": "message_length"},
            {"signal_type": "question_rate"},
        ]
        assert unique_signal_types(items) == ["message_length", "question_rate"]

    def test_same_signal_pair_does_not_meet_diversity_of_two(self):
        bundle = {
            "evidence_items": [
                {"evidence_id": "ev_a", "signal_type": "message_length", "value": {"direction": "increased"}},
                {"evidence_id": "ev_b", "signal_type": "message_length", "value": {"direction": "increased"}},
            ]
        }
        candidate = {
            "inference_id": "inf_dup",
            "claim": "Length changed.",
            "category": "interaction_pattern",
            "scope": "session_specific",
            "evidence_refs": ["ev_a", "ev_b"],
            "alternative_interpretations": ["Could be the last turn only."],
            "contradictions": [],
            "limitations": [],
            "minimum_signal_types": 2,
            "requires_temporal_change": False,
        }
        reviewed = apply_evidence_contract(candidate, bundle)
        assert reviewed["eligibility"] == "insufficient_evidence"
        assert "signal_diversity_too_low" in reviewed["limitations"]

    def test_two_signal_types_can_pass(self):
        bundle = {
            "evidence_items": [
                {"evidence_id": "ev_question_rate", "signal_type": "question_rate", "value": {}},
                {"evidence_id": "ev_repetition", "signal_type": "repetition", "value": {}},
            ]
        }
        candidate = {
            "inference_id": "inf_q",
            "claim": "Questions and repetition co-occur in this session.",
            "category": "interaction_pattern",
            "scope": "session_specific",
            "evidence_refs": ["ev_question_rate", "ev_repetition"],
            "alternative_interpretations": ["They may have retried the prompt."],
            "contradictions": [],
            "limitations": [],
            "minimum_signal_types": 2,
            "requires_temporal_change": False,
        }
        reviewed = apply_evidence_contract(candidate, bundle)
        assert reviewed["eligibility"] == "eligible"
        assert reviewed["provenance_level"] == ProvenanceLevel.INFERRED.value
        assert reviewed["alternative_interpretations"]
        assert _CONFIDENCE_FLOOR <= reviewed["confidence"] <= 0.75

    def test_blocking_contradiction_stops_eligibility(self):
        bundle = {
            "evidence_items": [
                {"evidence_id": "ev_message_length", "signal_type": "message_length", "value": {"direction": "increased"}},
            ]
        }
        candidate = {
            "inference_id": "inf_block",
            "claim": "Length only increased.",
            "category": "interaction_pattern",
            "scope": "session_specific",
            "evidence_refs": ["ev_message_length"],
            "alternative_interpretations": ["Maybe not."],
            "contradictions": [{
                "contradiction_id": "cx",
                "evidence_refs": ["ev_message_length"],
                "description": "A later measurement points the other way.",
                "effect_on_confidence": "block",
            }],
            "limitations": [],
            "minimum_signal_types": 1,
            "requires_temporal_change": True,
        }
        reviewed = apply_evidence_contract(candidate, bundle)
        assert reviewed["eligibility"] == "contradicted"
        assert reviewed["provenance_level"] is None
        assert reviewed["contradictions"][0]["description"]

    def test_prohibited_category_and_scope(self):
        bundle = {"evidence_items": [{"evidence_id": "ev_x", "signal_type": "message_length", "value": {}}]}
        prohibited = apply_evidence_contract({
            "category": "mental_health_diagnosis",
            "scope": "session_specific",
            "evidence_refs": ["ev_x"],
            "alternative_interpretations": [],
            "contradictions": [],
            "limitations": [],
        }, bundle)
        assert prohibited["eligibility"] == "prohibited"
        biographical = apply_evidence_contract({
            "category": "interaction_pattern",
            "scope": "biographical",
            "evidence_refs": ["ev_x"],
            "alternative_interpretations": [],
            "contradictions": [],
            "limitations": [],
        }, bundle)
        assert biographical["eligibility"] == "prohibited"

    def test_missing_evidence_blocks_the_claim(self):
        reviewed = apply_evidence_contract({
            "category": "interaction_pattern",
            "scope": "session_specific",
            "evidence_refs": ["ev_missing"],
            "alternative_interpretations": [],
            "contradictions": [],
            "limitations": [],
            "minimum_signal_types": 1,
        }, {"evidence_items": []})
        assert reviewed["eligibility"] == "insufficient_evidence"

    def test_confidence_is_bounded_support_not_truth(self):
        score = support_confidence(
            diversity=2,
            contradiction_count=1,
            alternative_count=1,
            temporal_ok=True,
        )
        assert 0.15 <= score <= 0.75


_CONFIDENCE_FLOOR = 0.15


class TestSessionInferences:
    def test_length_shift_is_eligible_without_calling_it_investment(self):
        evaluation = _locked("aa", "bbbb", "cccccccc").evaluate_session_inferences()
        match = next(record for record in evaluation["records"] if record["inference_id"] == "inf_message_length_shift")
        assert match["eligibility"] == "eligible"
        assert match["provenance_level"] == ProvenanceLevel.INFERRED.value
        assert match["scope"] == "session_specific"
        assert "invest" not in match["claim"].lower()
        assert match["alternative_interpretations"]

    def test_question_repetition_keeps_its_alternative(self):
        evaluation = _locked("why?", "other words", "why?").evaluate_session_inferences()
        match = next(record for record in evaluation["records"] if record["inference_id"] == "inf_question_repetition")
        assert match["eligibility"] == "eligible"
        assert len(match["evidence_refs"]) == 2
        assert match["alternative_interpretations"]

    def test_defaulted_shanta_does_not_support_an_emotional_claim(self):
        evaluation = _locked("hello", "there").evaluate_session_inferences()
        bundle = _locked("hello", "there").build_evidence_bundle()
        assert "defaulted_shanta_not_detected_evidence" in bundle["limitations"]
        claims = " ".join(record["claim"] for record in evaluation["records"])
        assert "calm" not in claims.lower()
        assert "inf_detected_rasa_change" not in {record["inference_id"] for record in evaluation["records"]}

    def test_detected_rasa_change_uses_detected_labels_only(self):
        evaluation = _locked(
            "I feel calm.",
            "hello",
            "I am angry and furious.",
        ).evaluate_session_inferences()
        match = next(record for record in evaluation["records"] if record["inference_id"] == "inf_detected_rasa_change")
        assert match["eligibility"] == "eligible"
        assert "Shanta" in match["claim"]
        assert "Raudra" in match["claim"]
        assert "default" not in match["claim"].lower()

    def test_engagement_claim_stays_on_the_interaction(self):
        evaluation = _locked("a", "bbbbbbbbbbbb", "a").evaluate_session_inferences()
        match = next(record for record in evaluation["records"] if record["inference_id"] == "inf_engagement_label")
        assert match["category"] == "interaction_engagement"
        assert "classified as" in match["claim"]
        assert "personality" not in match["claim"].lower()

    def test_one_turn_has_no_eligible_inference(self):
        evaluation = _locked("only").evaluate_session_inferences()
        assert evaluation["status"] == "insufficient_evidence"
        assert all(record["eligibility"] != "eligible" for record in evaluation["records"])

    def test_resonance_does_not_rewrite_the_claim(self):
        evaluation = _locked("aa", "bbbb", "cccccccc").evaluate_session_inferences()
        claim = next(record for record in evaluation["records"] if record["eligibility"] == "eligible")
        marker = resonance_marker(claim["inference_id"])
        assert marker["provenance_level"] == ProvenanceLevel.VALIDATED.value
        assert claim["provenance_level"] == ProvenanceLevel.INFERRED.value
        assert "true" in marker["meaning"]


class TestPhase4Isolation:
    def test_parrot_context_rejects_inference_material(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        coordinator.evaluate_session_inferences()
        with pytest.raises(StrictBoundaryViolationError):
            coordinator.build_parrot_context(
                "hello",
                1,
                {"primary_rasa": "Shanta", "evidence_bundle": {}},
            )
        ctx = coordinator.build_parrot_context("hello", 1, _CLEAN_NAVARASA)
        for key in (
            "evidence_bundle",
            "evidence_items",
            "candidate_inference",
            "inferred_claim",
            "confidence",
            "alternatives",
            "contradictions",
            "engagement_state",
            "engagement_evidence",
        ):
            assert key not in ctx
            assert key not in ctx["parrot_session"]
        for event in coordinator.store.parrot_context():
            assert event.payload.get("observation_kind") != "evidence_bundle"

    def test_deep_reader_packet_has_no_director_or_store(self):
        from ftp.silent_reader.inference import build_deep_reader_packet

        coordinator = _locked("why?", "other words", "why?")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        packet = build_deep_reader_packet(bundle, evaluation)
        blob = str(packet)
        assert "behavioural_eligibility" not in blob
        assert "EventStore" not in blob
        assert packet["eligible_inferences"]
        assert all(item["evidence_refs"] for item in packet["eligible_inferences"])
