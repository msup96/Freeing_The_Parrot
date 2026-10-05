"""Phase 4B — Deep Reader gloss layer tests."""

from __future__ import annotations

import json

import pytest

from ftp.events.store import StrictBoundaryViolationError
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState
from ftp.silent_reader.deep_reader.adapter import GeminiUnavailable, READER_INSTRUCTION
from ftp.silent_reader.deep_reader.packet import assert_narrow_reader_input, build_reader_input
from ftp.silent_reader.deep_reader.parse import ReaderParseError, parse_reader_response
from ftp.silent_reader.deep_reader.read import read_session_interpretations
from ftp.silent_reader.deep_reader.validate import validate_interpretation
from ftp.silent_reader.inference import build_deep_reader_packet


_CLEAN_NAVARASA = {
    "primary_rasa": "Shanta",
    "rasa_scores": {"Shanta": 1.0},
    "sentiment": {"compound": 0.0},
}


class FakeAdapter:
    def __init__(self, response: str | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls = 0

    def complete(self, reader_input: dict) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        assert "eligible_inferences" not in reader_input
        assert "packet_consistent" in reader_input
        return self.response or ""


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


def _length_gloss() -> str:
    return (
        "In this session your responses became longer and appeared willing "
        "to elaborate rather than keeping brief."
    )


def _engagement_gloss(state: str) -> str:
    return f"Interaction evidence in this session is classified as {state}."


def _rasa_gloss() -> str:
    return (
        "In this session the first and last detected Rasa labels differed "
        "from Shanta to Raudra."
    )


def _json_response(records: list[dict]) -> str:
    return json.dumps({"interpretations": records})


def _eligible_records(coordinator: SessionCoordinator) -> list[dict]:
    evaluation = coordinator.evaluate_session_inferences()
    return [record for record in evaluation["records"] if record["eligibility"] == "eligible"]


def _response_for(coordinator: SessionCoordinator, texts: dict[str, str]) -> str:
    items = []
    for record in _eligible_records(coordinator):
        text = texts.get(record["inference_id"], _default_gloss(record))
        items.append({
            "inference_id": record["inference_id"],
            "cited_evidence_ids": list(record["evidence_refs"]),
            "text": text,
        })
    return _json_response(items)


def _default_gloss(record: dict) -> str:
    if record["inference_id"] == "inf_message_length_shift":
        return _length_gloss()
    if record["inference_id"] == "inf_engagement_label":
        state = record["claim"].split("'")[1]
        return _engagement_gloss(state)
    if record["inference_id"] == "inf_detected_rasa_change":
        return _rasa_gloss()
    raise KeyError(record["inference_id"])


class TestDeepReaderOrchestration:
    def test_zero_eligible_records_skips_adapter(self):
        adapter = FakeAdapter()
        coordinator = _locked("only")
        result = coordinator.read_session(adapter=adapter)
        assert result["status"] == "insufficient_evidence"
        assert adapter.calls == 0
        assert result["gemini_called"] is False

    def test_unlocked_session_raises(self):
        coordinator = _live()
        coordinator.record_parrot_turn("live", "ok")
        with pytest.raises(ValueError, match="locked"):
            coordinator.read_session(adapter=FakeAdapter())

    def test_reader_input_only_cited_evidence(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        reader_input = build_reader_input(
            bundle=bundle,
            evaluation=evaluation,
            instruction=READER_INSTRUCTION,
        )
        cited = {item["evidence_id"] for item in reader_input["evidence_items"]}
        assert cited <= {"ev_message_length", "ev_engagement_state", "ev_repetition"}
        assert reader_input["packet_consistent"] is True

    def test_reader_input_excludes_forbidden_fields(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        reader_input = build_reader_input(
            bundle=bundle,
            evaluation=evaluation,
            instruction=READER_INSTRUCTION,
        )
        blob = json.dumps(reader_input)
        assert '"source_event_ids"' not in blob
        assert '"basis"' not in blob
        assert '"behavioural_eligibility"' not in blob
        assert '"confidence":' not in blob
        assert '"user_text"' not in blob

    def test_legal_length_gloss_accepted(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": _length_gloss(),
            "inf_engagement_label": _engagement_gloss("sustained"),
        }))
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        assert match["interpretation"]["status"] == "accepted"
        assert match["interpretation"]["author"] == "gemini"

    def test_emotionally_invested_rejected(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": (
                "In this session you became emotionally invested and longer."
            ),
            "inf_engagement_label": _engagement_gloss("sustained"),
        }))
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        assert match["interpretation"]["status"] == "rejected"
        assert "banned_token" in match["interpretation"]["rejection_reasons"]

    def test_trust_rejected(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": "In this session you began to trust and elaborate.",
            "inf_engagement_label": _engagement_gloss("sustained"),
        }))
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        assert "banned_token" in match["interpretation"]["rejection_reasons"]

    def test_felt_rejected_on_rasa(self):
        coordinator = _locked("I feel calm.", "hello", "I am angry and furious.")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_detected_rasa_change": (
                "In this session you felt a shift from Shanta to Raudra."
            ),
        }))
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_detected_rasa_change"
        )
        assert match["interpretation"]["status"] == "rejected"

    def test_valid_rasa_gloss_accepted(self):
        coordinator = _locked("I feel calm.", "hello", "I am angry and furious.")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_detected_rasa_change": _rasa_gloss(),
        }))
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_detected_rasa_change"
        )
        assert match["interpretation"]["status"] == "accepted"

    def test_reversed_direction_rejected(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": "In this session your responses became shorter toward the end.",
            "inf_engagement_label": _engagement_gloss("sustained"),
        }))
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        assert "direction_reversed" in match["interpretation"]["rejection_reasons"]

    def test_new_integer_rejected(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": (
                "In this session your responses became longer toward 999 end."
            ),
            "inf_engagement_label": _engagement_gloss("sustained"),
        }))
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        assert "number_not_in_evidence" in match["interpretation"]["rejection_reasons"]

    def test_fabricated_evidence_id_rejected(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        records = _eligible_records(coordinator)
        payload = []
        for record in records:
            payload.append({
                "inference_id": record["inference_id"],
                "cited_evidence_ids": list(record["evidence_refs"]),
                "text": (
                    _length_gloss()
                    if record["inference_id"] == "inf_message_length_shift"
                    else _engagement_gloss("sustained")
                ),
            })
        payload[0]["text"] = "In this session ev_fake made your responses longer."
        adapter = FakeAdapter(_json_response(payload))
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        assert "fabricated_id" in match["interpretation"]["rejection_reasons"]

    def test_wrong_cited_evidence_refs_rejected(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        records = _eligible_records(coordinator)
        payload = []
        for record in records:
            refs = list(record["evidence_refs"])
            if record["inference_id"] == "inf_message_length_shift":
                refs = ["ev_repetition"]
            payload.append({
                "inference_id": record["inference_id"],
                "cited_evidence_ids": refs,
                "text": (
                    _length_gloss()
                    if record["inference_id"] == "inf_message_length_shift"
                    else _engagement_gloss("sustained")
                ),
            })
        adapter = FakeAdapter(_json_response(payload))
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        assert "evidence_refs_mismatch" in match["interpretation"]["rejection_reasons"]

    def test_engagement_gloss_with_you_rejected(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": _length_gloss(),
            "inf_engagement_label": "In this session you are classified as sustained.",
        }))
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_engagement_label"
        )
        assert match["interpretation"]["status"] == "rejected"

    def test_contradictions_and_confidence_copied(self):
        coordinator = _locked("a", "bbbbbbbbbbbb", "cccccccc")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": _length_gloss(),
            "inf_engagement_label": _engagement_gloss("fluctuating"),
        }))
        evaluation = coordinator.evaluate_session_inferences()
        source = next(
            record for record in evaluation["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        result = coordinator.read_session(adapter=adapter)
        match = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        assert match["contradictions"] == source["contradictions"]
        assert match["confidence"] == source["confidence"]

    def test_event_count_unchanged(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        before = len(coordinator.store.all_events())
        coordinator.read_session(adapter=FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": _length_gloss(),
            "inf_engagement_label": _engagement_gloss("sustained"),
        })))
        assert len(coordinator.store.all_events()) == before

    def test_parrot_context_unchanged(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        coordinator.read_session(adapter=FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": _length_gloss(),
            "inf_engagement_label": _engagement_gloss("sustained"),
        })))
        ctx = coordinator.build_parrot_context("hello", 1, _CLEAN_NAVARASA)
        for key in (
            "interpretation",
            "deep_reader",
            "gemini_inferences",
            "evidence_bundle",
            "candidate_inference",
        ):
            assert key not in ctx
            assert key not in ctx["parrot_session"]

    def test_defaulted_shanta_session_has_no_rasa_inference(self):
        coordinator = _locked("hello", "there")
        evaluation = coordinator.evaluate_session_inferences()
        eligible_ids = {
            record["inference_id"]
            for record in evaluation["records"]
            if record["eligibility"] == "eligible"
        }
        assert "inf_detected_rasa_change" not in eligible_ids
        bundle = coordinator.build_evidence_bundle()
        reader_input = build_reader_input(
            bundle=bundle,
            evaluation=evaluation,
            instruction=READER_INSTRUCTION,
        )
        assert all(
            item["inference_id"] != "inf_detected_rasa_change"
            for item in reader_input["inferences"]
        )

    def test_partial_result_preserves_sibling(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": _length_gloss(),
            "inf_engagement_label": "In this session you trust the interaction evidence.",
        }))
        result = coordinator.read_session(adapter=adapter)
        assert result["status"] == "partial"
        length = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        engagement = next(
            record for record in result["records"]
            if record["inference_id"] == "inf_engagement_label"
        )
        assert length["interpretation"]["status"] == "accepted"
        assert engagement["interpretation"]["status"] == "rejected"

    def test_all_records_rejected_falls_back(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        adapter = FakeAdapter(_response_for(coordinator, {
            "inf_message_length_shift": "In this session you trust longer responses.",
            "inf_engagement_label": "In this session you trust the interaction evidence.",
        }))
        result = coordinator.read_session(adapter=adapter)
        assert result["status"] == "fallback"
        assert all(
            record["interpretation"]["author"] == "deterministic"
            for record in result["records"]
        )

    def test_gemini_exception_falls_back(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        result = coordinator.read_session(adapter=FakeAdapter(error=GeminiUnavailable("down")))
        assert result["status"] == "fallback"
        assert result["gemini_called"] is True
        assert result["records"][0]["interpretation"]["fallback_text"] == result["records"][0]["claim"]

    def test_timeout_error_falls_back(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        result = coordinator.read_session(adapter=FakeAdapter(error=GeminiUnavailable("timeout")))
        assert result["status"] == "fallback"

    def test_wide_packet_rejected_by_adapter_guard(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        wide = build_deep_reader_packet(bundle, evaluation)
        with pytest.raises(TypeError):
            assert_narrow_reader_input(wide)


class TestDeepReaderParser:
    def test_unknown_inference_id_whole_fallback(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        adapter = FakeAdapter(_json_response([{
            "inference_id": "inf_unknown",
            "cited_evidence_ids": ["ev_message_length"],
            "text": _length_gloss(),
        }]))
        result = read_session_interpretations(bundle, evaluation, adapter)
        assert result["status"] == "fallback"

    def test_duplicate_inference_id_whole_fallback(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        duplicate = _json_response([
            {
                "inference_id": "inf_message_length_shift",
                "cited_evidence_ids": ["ev_message_length"],
                "text": _length_gloss(),
            },
            {
                "inference_id": "inf_message_length_shift",
                "cited_evidence_ids": ["ev_message_length"],
                "text": _length_gloss(),
            },
        ])
        result = read_session_interpretations(bundle, evaluation, FakeAdapter(duplicate))
        assert result["status"] == "fallback"

    def test_missing_inference_id_whole_fallback(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        missing = _json_response([{
            "inference_id": "inf_message_length_shift",
            "cited_evidence_ids": ["ev_message_length"],
            "text": _length_gloss(),
        }])
        result = read_session_interpretations(bundle, evaluation, FakeAdapter(missing))
        assert result["status"] == "fallback"

    def test_extra_json_property_whole_fallback(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        extra_root = json.dumps({
            "interpretations": [],
            "extra": True,
        })
        with pytest.raises(ReaderParseError):
            parse_reader_response(extra_root, ["inf_message_length_shift"])
        result = read_session_interpretations(bundle, evaluation, FakeAdapter(extra_root))
        assert result["status"] == "fallback"

    def test_markdown_fence_whole_fallback(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        fenced = "```json\n" + _response_for(coordinator, {
            "inf_message_length_shift": _length_gloss(),
            "inf_engagement_label": _engagement_gloss("sustained"),
        }) + "\n```"
        result = read_session_interpretations(bundle, evaluation, FakeAdapter(fenced))
        assert result["status"] == "fallback"

    def test_malformed_json_whole_fallback(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        bundle = coordinator.build_evidence_bundle()
        evaluation = coordinator.evaluate_session_inferences()
        result = read_session_interpretations(bundle, evaluation, FakeAdapter("{not-json"))
        assert result["status"] == "fallback"


class TestDeepReaderValidatorUnit:
    def test_validate_interception_rejects_extra_property_payload(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        record = next(
            record for record in coordinator.evaluate_session_inferences()["records"]
            if record["inference_id"] == "inf_message_length_shift"
        )
        reasons = validate_interpretation(
            {
                "inference_id": record["inference_id"],
                "cited_evidence_ids": record["evidence_refs"],
                "text": "In this session you trust longer responses.",
            },
            record,
            {"ev_message_length": {"evidence_id": "ev_message_length", "value": {}}},
        )
        assert "banned_token" in reasons

    def test_parrot_context_rejects_deep_reader_material(self):
        coordinator = _locked("aa", "bbbb", "cccccccc")
        with pytest.raises(StrictBoundaryViolationError):
            coordinator.build_parrot_context(
                "hello",
                1,
                {"primary_rasa": "Shanta", "deep_reader": {}},
            )
