"""Phase 2 — temporal trajectory synthesis (Deep Reader foundation)."""

import pytest

from ftp.events.model import EventType, ProvenanceLevel
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState
from ftp.timeline.wiring import record_chat_timeline_events


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


def _locked_with_turns(*messages: str) -> SessionCoordinator:
    coordinator = _live()
    for message in messages:
        coordinator.record_parrot_turn(message, "Reply.")
    coordinator.lock()
    return coordinator


class TestTemporalTrajectoryBasics:
    def test_identical_events_produce_identical_trajectories(self):
        coordinator = _locked_with_turns(
            "short",
            "a somewhat longer line",
            "short",
        )
        first = coordinator.synthesize_temporal_trajectories()
        second = coordinator.synthesize_temporal_trajectories()
        assert first == second

    def test_turn_sequence_preserves_order_and_event_ids(self):
        coordinator = _live()
        first = coordinator.record_parrot_turn("one", "a")
        second = coordinator.record_parrot_turn("two words", "b")
        third = coordinator.record_parrot_turn("three word line", "c")
        coordinator.lock()

        trajectory = coordinator.synthesize_temporal_trajectories()
        sequence = trajectory["turn_sequence"]
        assert [turn["turn_index"] for turn in sequence] == [1, 2, 3]
        assert [turn["event_id"] for turn in sequence] == [
            first.event_id,
            second.event_id,
            third.event_id,
        ]
        assert [turn["message_length"] for turn in sequence] == [3, 9, 15]
        assert all(turn["timestamp"] for turn in sequence)
        assert first.event_id in sequence[0]["source_event_ids"]

    def test_refuses_synthesis_before_lock(self):
        coordinator = _live()
        coordinator.record_parrot_turn("still live", "ok")
        try:
            coordinator.synthesize_temporal_trajectories()
        except ValueError as exc:
            assert "locked" in str(exc)
        else:
            raise AssertionError("expected lock guard")


class TestMessageLengthTrajectory:
    def test_first_final_mean_and_direction(self):
        coordinator = _locked_with_turns("aa", "bbbb", "cccccccc")
        length = coordinator.synthesize_temporal_trajectories()[
            "message_length_trajectory"
        ]
        assert length["provenance_level"] == ProvenanceLevel.OBSERVED.value
        assert length["per_turn"] == [2, 4, 8]
        assert length["first"] == 2
        assert length["final"] == 8
        assert length["minimum"] == 2
        assert length["maximum"] == 8
        assert length["mean"] == 4.667
        assert length["change"]["absolute"] == 6
        assert length["change"]["direction"] == "increased"
        assert length["source_event_ids"]


class TestBeginningVsEnding:
    def test_compares_first_and_last_message_length(self):
        coordinator = _locked_with_turns("tiny", "middle length", "end")
        comparison = coordinator.synthesize_temporal_trajectories()[
            "beginning_vs_ending"
        ]
        assert comparison["sufficient"] is True
        assert comparison["beginning"]["message_length"] == 4
        assert comparison["ending"]["message_length"] == 3
        assert comparison["message_length_change"]["direction"] == "decreased"
        assert comparison["beginning"]["event_id"]
        assert comparison["ending"]["event_id"]


class TestLatencyAndGap:
    def test_latency_and_gap_from_timeline_and_derived_telemetry(self):
        coordinator = _live()
        record_chat_timeline_events(
            coordinator,
            "hello there",
            {"turn": 1, "response": "One.", "gate": {}, "closed": False},
        )
        record_chat_timeline_events(
            coordinator,
            "a second message arrives later",
            {"turn": 2, "response": "Two.", "gate": {}, "closed": False},
        )
        coordinator.silent_reader.analyze_pending()
        coordinator.lock()

        trajectory = coordinator.synthesize_temporal_trajectories()
        sequence = trajectory["turn_sequence"]
        assert len(sequence) == 2
        assert sequence[0]["response_latency"] is not None
        assert sequence[0]["inter_turn_gap"] is None
        assert sequence[1]["inter_turn_gap"] is not None
        assert sequence[1]["response_latency"] is not None

        latency = trajectory["response_latency_trajectory"]
        assert latency["status"] == "ok"
        assert latency["first"] == sequence[0]["response_latency"]
        assert latency["final"] == sequence[1]["response_latency"]
        assert latency["source_event_ids"]

        gaps = trajectory["inter_turn_gap_trajectory"]
        assert gaps["per_turn"][0] is None
        assert gaps["per_turn"][1] == sequence[1]["inter_turn_gap"]
        assert gaps["first"] == sequence[1]["inter_turn_gap"]
        assert gaps["final"] == sequence[1]["inter_turn_gap"]

    def test_missing_latency_stays_missing_without_raw_ingest(self):
        coordinator = _locked_with_turns("no raw ingest beside this turn")
        trajectory = coordinator.synthesize_temporal_trajectories()
        assert trajectory["turn_sequence"][0]["response_latency"] is None
        latency = trajectory["response_latency_trajectory"]
        assert latency["status"] == "missing"
        assert latency["first"] is None
        comparison = trajectory["beginning_vs_ending"]
        assert comparison["latency_change"]["status"] == "insufficient"


class TestRepetition:
    def test_repeated_message_is_counted_with_event_refs(self):
        coordinator = _locked_with_turns(
            "I keep asking",
            "something else",
            "I keep asking",
        )
        repetition = coordinator.synthesize_temporal_trajectories()["repetition"]
        assert repetition["repetition_count"] == 1
        assert repetition["repeated_turns"][0]["turn_index"] == 3
        assert repetition["repeated_turns"][0]["event_id"]
        assert repetition["source_event_ids"]
        assert sum(repetition["phases"].values()) == 1


class TestInsufficientData:
    def test_empty_session_marks_trajectories_insufficient(self):
        coordinator = _live()
        coordinator.lock()
        trajectory = coordinator.synthesize_temporal_trajectories()
        assert trajectory["turn_sequence"] == []
        assert trajectory["message_length_trajectory"]["status"] == "insufficient"
        assert trajectory["beginning_vs_ending"]["sufficient"] is False
        assert trajectory["volatility"]["message_length"]["status"] == "insufficient"

    def test_two_turns_are_insufficient_for_volatility(self):
        coordinator = _locked_with_turns("one", "two two")
        volatility = coordinator.synthesize_temporal_trajectories()["volatility"]
        assert volatility["message_length"]["sufficient"] is False
        assert volatility["message_length"]["transition_count"] is None

    def test_three_turns_report_descriptive_volatility(self):
        coordinator = _locked_with_turns("aa", "bbbb", "aa")
        length_vol = coordinator.synthesize_temporal_trajectories()["volatility"][
            "message_length"
        ]
        assert length_vol["sufficient"] is True
        assert length_vol["transition_count"] == 2
        assert length_vol["consecutive_repeat_count"] == 0
        assert length_vol["range"] == 2
        assert isinstance(length_vol["normalized_variation"], float)


class TestIsolation:
    def test_sessions_do_not_share_trajectory_events(self):
        first = _locked_with_turns("alpha only")
        second = _locked_with_turns("beta message", "beta message")
        a = first.synthesize_temporal_trajectories()
        b = second.synthesize_temporal_trajectories()
        assert a["session_id"] == first.session_id
        assert b["session_id"] == second.session_id
        assert a["session_id"] != b["session_id"]
        assert a["turn_sequence"][0]["event_id"] != b["turn_sequence"][0]["event_id"]
        assert b["repetition"]["repetition_count"] == 1
        assert a["repetition"]["repetition_count"] == 0

    def test_trajectory_is_absent_from_live_parrot_context(self):
        coordinator = _live()
        coordinator.record_parrot_turn("visible to parrot as a turn", "ok")
        coordinator.lock()
        trajectory = coordinator.synthesize_temporal_trajectories()
        assert trajectory["observation_kind"] == "temporal_trajectory"

        ctx = coordinator.build_parrot_context(
            turn_text="later live would be blocked",
            turn_index=1,
            navarasa_result=_CLEAN_NAVARASA,
        )
        assert "temporal_trajectory" not in ctx
        assert "observation_kind" not in ctx
        assert "message_length_trajectory" not in ctx
        assert "beginning_vs_ending" not in ctx
        parrot_session = ctx["parrot_session"]
        assert "temporal_trajectory" not in parrot_session
        for event in coordinator.store.parrot_context():
            payload = event.payload
            assert payload.get("observation_kind") != "temporal_trajectory"
            assert "message_length_trajectory" not in payload
            assert "beginning_vs_ending" not in payload


class TestLinguisticTrajectory:
    def test_deterministic_output(self):
        coordinator = _locked_with_turns("Why me?", "I think I need help.")
        first = coordinator.synthesize_linguistic_trajectories()
        second = coordinator.synthesize_linguistic_trajectories()
        assert first == second

    def test_turn_ordering_matches_temporal_spine(self):
        coordinator = _locked_with_turns("one", "two?", "three three")
        temporal = coordinator.synthesize_temporal_trajectories()["turn_sequence"]
        linguistic = coordinator.synthesize_linguistic_trajectories()["turn_sequence"]
        assert [t["event_id"] for t in temporal] == [
            t["event_id"] for t in linguistic
        ]
        assert [t["turn_index"] for t in linguistic] == [1, 2, 3]

    def test_question_detection_and_rate(self):
        coordinator = _locked_with_turns("hello", "why now?", "still here")
        linguistic = coordinator.synthesize_linguistic_trajectories()
        assert linguistic["turn_sequence"][0]["utterance_is_question"] is False
        assert linguistic["turn_sequence"][1]["utterance_is_question"] is True
        rate = linguistic["question_rate"]
        assert rate["question_turns"] == 1
        assert rate["turn_count"] == 3
        assert rate["value"] == round(1 / 3, 3)

    def test_self_reference_and_trajectory(self):
        coordinator = _locked_with_turns("I am here", "you are there", "my turn")
        linguistic = coordinator.synthesize_linguistic_trajectories()
        assert linguistic["turn_sequence"][0]["self_reference_count"] == 1
        assert linguistic["turn_sequence"][1]["self_reference_count"] == 0
        assert linguistic["turn_sequence"][2]["self_reference_count"] == 1
        traj = linguistic["self_reference_trajectory"]
        assert traj["per_turn"] == [1, 0, 1]
        assert traj["first"] == 1
        assert traj["final"] == 1
        assert traj["change"]["direction"] == "unchanged"

    def test_token_count_and_ttr(self):
        coordinator = _locked_with_turns("one two two", "alpha beta")
        linguistic = coordinator.synthesize_linguistic_trajectories()
        assert linguistic["turn_sequence"][0]["token_count"] == 3
        assert linguistic["turn_sequence"][0]["type_token_ratio"] == round(2 / 3, 3)
        assert linguistic["type_token_ratio_trajectory"]["method"] == "whitespace_ttr"
        assert linguistic["token_count_trajectory"]["first"] == 3

    def test_empty_session(self):
        coordinator = _live()
        coordinator.lock()
        linguistic = coordinator.synthesize_linguistic_trajectories()
        assert linguistic["turn_sequence"] == []
        assert linguistic["question_rate"]["status"] == "insufficient"
        assert linguistic["self_reference_trajectory"]["status"] == "insufficient"

    def test_one_turn_insufficiency_for_change(self):
        coordinator = _locked_with_turns("solo")
        linguistic = coordinator.synthesize_linguistic_trajectories()
        assert linguistic["self_reference_trajectory"]["change"]["status"] == "insufficient"

    def test_source_event_ids(self):
        coordinator = _locked_with_turns("I wonder?")
        event_id = coordinator.store.events_of_type(
            EventType.PARROT_TURN_GENERATED
        )[0].event_id
        linguistic = coordinator.synthesize_linguistic_trajectories()
        assert event_id in linguistic["turn_sequence"][0]["source_event_ids"]
        assert event_id in linguistic["question_rate"]["source_event_ids"]

    def test_session_isolation(self):
        a = _locked_with_turns("I I I")
        b = _locked_with_turns("you you")
        assert a.synthesize_linguistic_trajectories()["session_id"] != (
            b.synthesize_linguistic_trajectories()["session_id"]
        )

    def test_excluded_psychological_fields_absent(self):
        coordinator = _locked_with_turns("I feel uncertain?")
        blob = str(coordinator.synthesize_linguistic_trajectories()).lower()
        for forbidden in (
            "hedge",
            "agency",
            "validation",
            "personality",
            "diagnosis",
        ):
            assert forbidden not in blob

    def test_refuses_synthesis_before_lock(self):
        coordinator = _live()
        coordinator.record_parrot_turn("live", "ok")
        with pytest.raises(ValueError, match="locked"):
            coordinator.synthesize_linguistic_trajectories()


class TestNavarasaTrajectory:
    def test_matches_engine_for_known_sentence(self):
        from navarasa_engine import analyse_text

        text = "I am angry and furious."
        expected = analyse_text(text)
        coordinator = _locked_with_turns(text)
        row = coordinator.synthesize_navarasa_trajectories()["turn_sequence"][0]
        assert row["primary_rasa"] == expected["primary_rasa"]

    def test_sequence_transitions_and_dominance(self):
        coordinator = _locked_with_turns(
            "I feel happy and joyful.",
            "I am angry and furious.",
            "I feel happy and joyful.",
        )
        nav = coordinator.synthesize_navarasa_trajectories()
        assert nav["rasa_sequence"] == ["Hasya", "Raudra", "Hasya"]
        assert nav["transition_count"] == 2
        assert nav["dominant_rasa"]["label"] == "Hasya"
        assert nav["dominant_rasa"]["count"] == 2
        assert nav["persistence"]["run_length"] == 1
        assert nav["switching_rate"]["value"] == 1.0
        assert nav["beginning_rasa"] == "Hasya"
        assert nav["ending_rasa"] == "Hasya"
        assert nav["beginning_end_changed"] is False

    def test_defaulted_shanta_on_neutral_text(self):
        coordinator = _locked_with_turns("hello there")
        row = coordinator.synthesize_navarasa_trajectories()["turn_sequence"][0]
        assert row["primary_rasa"] == "Shanta"
        assert row["defaulted_primary"] is True
        assert row["analysis_quality"] == "no_emotion_detected"

    def test_initial_offering_separate_from_turn_sequence(self):
        coordinator = SessionCoordinator()
        coordinator.start()
        offering = coordinator.mark_analysis_ready(
            {
                "primary_rasa": "Karuna",
                "rasa_scores": {"Karuna": 1.0},
                "analysis_quality": "weak_emotion_signal",
                "text": "I feel sad.",
            }
        )
        coordinator.advance(SessionState.LIVE_CONVERSATION)
        coordinator.record_parrot_turn("I am angry and furious.", "Reply.")
        coordinator.lock()
        nav = coordinator.synthesize_navarasa_trajectories()
        assert nav["turn_sequence"][0]["primary_rasa"] == "Raudra"
        assert nav["initial_offering"]["event_id"] == offering.event_id
        assert nav["initial_offering"]["primary_rasa"] == "Karuna"
        assert nav["rasa_sequence"] == ["Raudra"]

    def test_no_initial_offering_when_absent(self):
        coordinator = _locked_with_turns("plain text")
        assert coordinator.synthesize_navarasa_trajectories()["initial_offering"] is None

    def test_sessions_do_not_cross_read(self):
        a = _locked_with_turns("I am angry and furious.")
        b = _locked_with_turns("I feel happy and joyful.")
        assert a.synthesize_navarasa_trajectories()["rasa_sequence"] == ["Raudra"]
        assert b.synthesize_navarasa_trajectories()["rasa_sequence"] == ["Hasya"]

    def test_does_not_create_navarasa_classified_events(self):
        coordinator = _locked_with_turns("I am afraid and terrified.")
        before = len(coordinator.store.events_of_type(EventType.NAVARASA_CLASSIFIED))
        coordinator.synthesize_navarasa_trajectories()
        after = len(coordinator.store.events_of_type(EventType.NAVARASA_CLASSIFIED))
        assert after == before

    def test_refuses_synthesis_before_lock(self):
        coordinator = _live()
        coordinator.record_parrot_turn("live", "ok")
        with pytest.raises(ValueError, match="locked"):
            coordinator.synthesize_navarasa_trajectories()


class TestPhase3ParrotIsolation:
    _FORBIDDEN_CONTEXT_KEYS = (
        "linguistic_trajectory",
        "navarasa_trajectory",
        "rasa_sequence",
        "self_reference_trajectory",
        "question_rate",
        "token_count",
        "type_token_ratio",
    )

    def test_build_parrot_context_unchanged_after_phase3_synthesis(self):
        coordinator = _live()
        coordinator.record_parrot_turn("I feel happy and joyful.", "ok")
        coordinator.lock()
        coordinator.synthesize_linguistic_trajectories()
        coordinator.synthesize_navarasa_trajectories()

        ctx = coordinator.build_parrot_context(
            turn_text="blocked",
            turn_index=1,
            navarasa_result=_CLEAN_NAVARASA,
        )
        for key in self._FORBIDDEN_CONTEXT_KEYS:
            assert key not in ctx
            assert key not in ctx["parrot_session"]

        for event in coordinator.store.parrot_context():
            payload = event.payload
            blob = str(payload).lower()
            assert payload.get("observation_kind") not in (
                "linguistic_trajectory",
                "navarasa_trajectory",
            )
            assert "rasa_sequence" not in payload
            for forbidden in self._FORBIDDEN_CONTEXT_KEYS:
                assert forbidden not in blob
