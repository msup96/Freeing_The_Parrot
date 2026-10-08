"""Phase 4C — reading profile and 27-card composer."""

import json

import pytest

from ftp.events.model import EventType, ProvenanceLevel
from ftp.events.store import StrictBoundaryViolationError
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState
from ftp.silent_reader.deep_reader.adapter import GeminiUnavailable
from ftp.silent_reader.reading.compose import DeterministicFallbackAdapter, compose_deck, compose_reading_deck
from ftp.silent_reader.reading.profile import build_reading_profile
from ftp.silent_reader.reading.validate import (
    CardResonanceError,
    contains_spoiler,
    validate_card_resonance,
    validate_deck,
)
from tests.test_deep_reader_gloss import FakeAdapter, _engagement_gloss, _length_gloss, _locked, _live, _response_for

_CLEAN_NAVARASA = {
    "primary_rasa": "Shanta",
    "rasa_scores": {"Shanta": 1.0},
    "sentiment": {"compound": 0.0},
}


def _post_session(*messages: str) -> SessionCoordinator:
    coordinator = _locked(*messages) if messages else _live()
    if not messages:
        coordinator.lock()
    coordinator.advance(SessionState.POST_SESSION_INTERPRETATION)
    return coordinator


class TestReadingComposer:
    def test_exactly_27_unique_cards(self):
        deck = _post_session(
            "aa",
            "bbbb",
            "cccccccc",
        ).compose_post_session_reading()
        assert deck["total_cards"] == 27
        assert len(deck["cards"]) == 27
        assert len({card["card_id"] for card in deck["cards"]}) == 27
        assert len({card["qualitative_reading"] for card in deck["cards"]}) == 27

    def test_semantic_anchor_system_is_session_specific(self):
        deck = _post_session(
            "I am carrying too many expectations.",
            "I need clarity and guidance.",
            "The pressure makes it hard to keep going.",
        ).compose_post_session_reading()
        anchors = [card["semantic_anchor"] for card in deck["cards"]]
        assert len(anchors) == 27
        assert len(set(anchors)) == 27
        assert all(anchors)
        assert "EXPECTATIONS" in anchors
        assert any("CLARITY" in anchor for anchor in anchors)
        assert deck["theme"]["source"] == "participant_turns_post_session"
        assert len(deck["theme"]["phrases"]) == 3
        assert len({card["semantic_motif"] for card in deck["cards"]}) == 27
        assert all(card["hidden_provenance"]["semantic_anchor"] == card["semantic_anchor"] for card in deck["cards"])
        assert all(card["hidden_provenance"]["semantic_motif"] == card["semantic_motif"] for card in deck["cards"])

    def test_theme_grounds_reading_without_becoming_evidence(self):
        deck = _post_session(
            "Expectations are becoming heavy.",
            "I want clarity.",
            "I need guidance.",
        ).compose_post_session_reading()
        card = deck["cards"][0]
        assert "EXPECTATIONS" in card["semantic_anchor"]
        assert "EXPECTATIONS" not in card["qualitative_reading"]
        assert "semantic_anchor" not in card["hidden_provenance"]["evidence_ids"]

    def test_different_conversations_produce_different_card_themes(self):
        pressure = _post_session(
            "Expectations are exhausting.",
            "I am carrying pressure from what people expect.",
            "I need room to stop performing.",
        ).compose_post_session_reading()
        transition = _post_session(
            "I am moving into something new.",
            "I do not know what the next chapter looks like.",
            "I am deciding which direction to take.",
        ).compose_post_session_reading()

        assert pressure["theme"]["phrases"] != transition["theme"]["phrases"]
        pressure_titles = {card["title"] for card in pressure["cards"]}
        transition_titles = {card["title"] for card in transition["cards"]}
        assert pressure_titles != transition_titles

    def test_lexical_theme_fallback_filters_participant_spoilers(self):
        deck = _post_session(
            "confidence telemetry gemini",
            "confidence telemetry gemini",
        ).compose_post_session_reading()
        assert all(
            word not in deck["theme"]["phrases"]
            for word in ("CONFIDENCE", "TELEMETRY", "GEMINI")
        )
        for card in deck["cards"]:
            text = f"{card['title']} {card['qualitative_reading']}"
            assert not contains_spoiler(text)

    def test_provenance_integrity(self):
        card = _post_session("aa", "bbbb", "cccccccc").compose_post_session_reading()["cards"][0]
        assert card["provenance_level"] == ProvenanceLevel.INFERRED.value
        hidden = card["hidden_provenance"]
        assert hidden["provenance_level"] == ProvenanceLevel.INFERRED.value
        assert hidden["inference_ids"]
        assert hidden["evidence_ids"]
        assert hidden["barnum_technique"]
        assert hidden["composition_strategy"]

    def test_evidence_traceability(self):
        coordinator = _post_session("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        reader = coordinator.read_session(adapter=DeterministicFallbackAdapter())
        profile = build_reading_profile(bundle=bundle, evaluation=evaluation, reader_result=reader)
        deck = compose_deck(profile)
        validate_deck(deck, profile)
        for card in deck["cards"]:
            assert card["hidden_provenance"]["evidence_ids"]
            assert card["hidden_provenance"]["inference_ids"]

    def test_no_spoilers_in_participant_text(self):
        deck = _post_session(
            "I am angry and furious.",
            "why?",
            "I am angry and furious.",
        ).compose_post_session_reading()
        for card in deck["cards"]:
            text = f"{card['title']} {card['qualitative_reading']}".lower()
            assert "you said" not in text
            assert "navarasa" not in text
            assert "ev_" not in text
            assert "inf_" not in text
            assert not contains_spoiler(text)

    def test_fallback_reader_still_composes(self):
        coordinator = _post_session("aa", "bbbb", "cccccccc")
        deck = coordinator.compose_post_session_reading(adapter=DeterministicFallbackAdapter())
        assert deck["total_cards"] == 27

    def test_insufficient_evidence_still_composes(self):
        coordinator = _post_session("only")
        deck = coordinator.compose_post_session_reading()
        assert deck["total_cards"] == 27

    def test_empty_locked_session_still_composes(self):
        coordinator = _live()
        coordinator.lock()
        coordinator.advance(SessionState.POST_SESSION_INTERPRETATION)
        deck = coordinator.compose_post_session_reading()
        assert deck["total_cards"] == 27

    def test_records_cards_generated_as_inferred(self):
        coordinator = _post_session("aa", "bbbb")
        coordinator.generate_post_session_interpretation()
        events = coordinator.store.events_of_type(EventType.CARDS_GENERATED)
        assert len(events) == 1
        assert events[0].provenance_level == ProvenanceLevel.INFERRED

    def test_compose_requires_post_session_state(self):
        coordinator = _locked("aa", "bbbb")
        with pytest.raises(ValueError, match="POST_SESSION_INTERPRETATION"):
            coordinator.compose_post_session_reading()

    def test_mark_resonance_semantics(self):
        coordinator = _post_session("aa", "bbbb", "cccccccc")
        coordinator.generate_post_session_interpretation()
        coordinator.advance(SessionState.CARD_SELECTION)
        card = coordinator.store.events_of_type(EventType.CARDS_GENERATED)[0].payload["cards"][0]
        event = coordinator.mark_card_resonance(
            card_id=card["card_id"],
            card_index=card["card_index"],
        )
        assert event.provenance_level == ProvenanceLevel.VALIDATED
        assert event.payload["meaning"] == "participant_reported_resonance_not_truth"

    def test_unknown_card_rejected(self):
        coordinator = _post_session("aa", "bbbb")
        coordinator.generate_post_session_interpretation()
        coordinator.advance(SessionState.CARD_SELECTION)
        with pytest.raises(CardResonanceError):
            coordinator.mark_card_resonance(card_id="card_missing", card_index=1)

    def test_duplicate_card_identity_mismatch(self):
        coordinator = _post_session("aa", "bbbb")
        deck = coordinator.generate_post_session_interpretation()
        card = deck["cards"][0]
        other = deck["cards"][1]
        with pytest.raises(CardResonanceError):
            validate_card_resonance(
                deck,
                card_id=card["card_id"],
                card_index=other["card_index"],
            )

    def test_mark_resonance_requires_card_selection(self):
        coordinator = _post_session("aa", "bbbb")
        deck = coordinator.generate_post_session_interpretation()
        card = deck["cards"][0]
        with pytest.raises(ValueError, match="CARD_SELECTION"):
            coordinator.mark_card_resonance(
                card_id=card["card_id"],
                card_index=card["card_index"],
            )

    def test_parrot_isolation(self):
        coordinator = _post_session("aa", "bbbb", "cccccccc")
        coordinator.generate_post_session_interpretation()
        ctx = coordinator.build_parrot_context("hello", 1, _CLEAN_NAVARASA)
        blob = json.dumps(ctx)
        for key in (
            "reading_profile",
            "hidden_provenance",
            "qualitative_reading",
            "interpretation",
            "deep_reader",
            "gemini_inferences",
            "evidence_bundle",
        ):
            assert key not in blob
        with pytest.raises(StrictBoundaryViolationError):
            coordinator.build_parrot_context(
                "hello",
                1,
                {"primary_rasa": "Shanta", "qualitative_reading": "leak"},
            )

    def test_event_store_cards_not_parrot_eligible(self):
        coordinator = _post_session("aa", "bbbb")
        coordinator.generate_post_session_interpretation()
        for event in coordinator.store.parrot_context():
            assert event.event_type != EventType.CARDS_GENERATED

    def test_multiple_inferences_map_to_multiple_cards(self):
        coordinator = _post_session("aa", "bbbb", "cccccccc")
        reader = coordinator.read_session(adapter=FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": _length_gloss(),
            "inf_engagement_label": _engagement_gloss("sustained"),
        })))
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        profile = build_reading_profile(bundle=bundle, evaluation=evaluation, reader_result=reader)
        deck = compose_deck(profile)
        inference_sets = {
            tuple(card["hidden_provenance"]["inference_ids"])
            for card in deck["cards"]
        }
        assert len(inference_sets) > 1

    def test_compose_does_not_advance_state(self):
        coordinator = _post_session("aa", "bbbb")
        before = coordinator.state
        coordinator.compose_post_session_reading()
        assert coordinator.state == before

    def test_accepted_reader_output_seeds_profile(self):
        coordinator = _post_session("aa", "bbbb", "cccccccc")
        reader = coordinator.read_session(adapter=FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": _length_gloss(),
            "inf_engagement_label": _engagement_gloss("sustained"),
        })))
        assert any(
            record["interpretation"]["status"] == "accepted"
            for record in reader["records"]
        )
        deck = coordinator.compose_post_session_reading(adapter=FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": _length_gloss(),
            "inf_engagement_label": _engagement_gloss("sustained"),
        })))
        assert deck["total_cards"] == 27

    def test_gemini_unavailable_adapter_still_composes_via_fallback(self):
        coordinator = _post_session("aa", "bbbb", "cccccccc")

        class ExplodingAdapter:
            def complete(self, reader_input):
                raise GeminiUnavailable("offline")

        deck = coordinator.compose_post_session_reading(adapter=ExplodingAdapter())
        assert deck["total_cards"] == 27

    def test_same_analytical_material_is_independent_of_session_id(self):
        profile = {
            "session_id": "session-a",
            "reader_status": "accepted",
            "evaluation_status": "sufficient",
            "limitations": [],
            "evidence_catalog": {"ev_1": {"signal_type": "length", "observation": "messages lengthened"}},
            "anchors": [{
                "inference_id": "inf_1",
                "category": "temporal_pattern",
                "evidence_refs": ["ev_1"],
                "reading_seed": "The exchange lengthened as the participant stayed with the question.",
            }],
        }
        equivalent = {**profile, "session_id": "session-b"}

        assert compose_deck(profile)["cards"] == compose_deck(equivalent)["cards"]

    def test_different_analytical_material_changes_qualitative_readings(self):
        profile_a = {
            "session_id": "a",
            "reader_status": "accepted",
            "evaluation_status": "sufficient",
            "limitations": [],
            "evidence_catalog": {"ev_1": {"signal_type": "length", "observation": "messages lengthened"}},
            "anchors": [{
                "inference_id": "inf_1",
                "category": "temporal_pattern",
                "evidence_refs": ["ev_1"],
                "reading_seed": "The exchange lengthened as the participant stayed with the question.",
            }],
        }
        profile_b = {**profile_a}
        profile_b["anchors"] = [{
            **profile_a["anchors"][0],
            "reading_seed": "The exchange shortened when the participant approached a boundary.",
        }]

        readings_a = {card["qualitative_reading"] for card in compose_deck(profile_a)["cards"]}
        readings_b = {card["qualitative_reading"] for card in compose_deck(profile_b)["cards"]}
        assert readings_a != readings_b
        assert len(readings_a & readings_b) < 27
