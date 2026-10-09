"""Pass 5 — Language Realizer."""

import json
from unittest.mock import patch

import pytest

from ftp.parrot.director import BehaviourDirector
from ftp.parrot.realizer import (
    MAX_REALIZER_TEXT_CHARS,
    LanguageRealizer,
    build_realizer_request,
    validate_realizer_output,
)
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState

_NAV = {"primary_rasa": "Shanta", "rasa_scores": {}, "sentiment": {}}
_INSTRUCTION = {
    "behaviour": "understanding",
    "behaviour_family": "understanding",
    "behaviour_intensity": "steady",
    "directive": None,
    "directive_basis": [],
}


def _live() -> SessionCoordinator:
    c = SessionCoordinator()
    c.start()
    c.advance(SessionState.LIVE_CONVERSATION)
    return c


def _session():
    return {
        "understanding_turns": 3,
        "chaos_count": 0,
        "last_behaviour": None,
        "behaviour_history": [],
        "recent_absurdities": [],
        "recent_memory_glitches": [],
        "recent_system_glitches": [],
        "recent_help_lines": [],
    }


def _request(**overrides):
    payload = {
        "turn_text": "I keep thinking about the orchard gate.",
        "turn_index": 4,
        "navarasa_result": _NAV,
        "recent_turn_texts": ["The orchard gate stays closed."],
        **_INSTRUCTION,
    }
    payload.update(overrides)
    return payload


class TestDeterministicRealizer:
    def setup_method(self):
        LanguageRealizer.configure_adapter(None)

    def test_selected_glitch_line_is_preserved_alongside_conversation(self):
        with patch("interface_server.apply_behaviour", return_value="BANANA PROTOCOL // CONTEXT DISAGREEMENT."):
            text = LanguageRealizer.realize(
                _request(behaviour="banana", behaviour_family="banana", conversation_move="reflect"),
                session=_session(),
                roast="",
                analysis=_NAV,
            )
        assert "BANANA PROTOCOL" in text

    def test_returns_non_empty_text(self):
        text = LanguageRealizer.realize(
            _request(),
            session=_session(),
            roast="",
            analysis=_NAV,
        )
        assert isinstance(text, str)
        assert text.strip()

    def test_empty_output_rejected_by_validator(self):
        assert not validate_realizer_output("", _INSTRUCTION)
        assert not validate_realizer_output("   ", _INSTRUCTION)

    def test_oversized_output_rejected(self):
        assert not validate_realizer_output("x" * (MAX_REALIZER_TEXT_CHARS + 1), _INSTRUCTION)

    def test_no_directive_uses_base_behaviour(self):
        with patch("interface_server.apply_behaviour", return_value="BASE LINE") as mocked:
            text = LanguageRealizer.realize(
                _request(directive=None),
                session=_session(),
                roast="",
                analysis=_NAV,
            )
        assert text == "BASE LINE"
        mocked.assert_called_once()
        assert mocked.call_args.args[0] == "understanding"

    def test_familiarity_can_use_literal_reference(self):
        text = LanguageRealizer.realize(
            _request(
                directive="familiarity",
                directive_basis=[
                    {
                        "turn_index": 1,
                        "role": "user",
                        "excerpt": "orchard gate",
                    }
                ],
            ),
            session=_session(),
            roast="",
            analysis=_NAV,
        )
        assert "orchard gate" in text

    def test_reciprocity_echoes_participant_wording(self):
        text = LanguageRealizer.realize(
            _request(
                turn_text='It is a "mess" today.',
                directive="reciprocity",
                directive_basis=[
                    {"turn_index": 1, "role": "user", "excerpt": "mess"},
                ],
            ),
            session=_session(),
            roast="",
            analysis=_NAV,
        )
        assert "mess" in text

    def test_curiosity_uses_mentioned_topic(self):
        text = LanguageRealizer.realize(
            _request(
                directive="curiosity",
                directive_basis=[
                    {"turn_index": 1, "role": "user", "excerpt": "orchard gate"},
                ],
            ),
            session=_session(),
            roast="",
            analysis=_NAV,
        )
        assert "orchard gate" in text

    def test_expectation_open_thread(self):
        text = LanguageRealizer.realize(
            _request(
                turn_text="Still thinking.",
                recent_turn_texts=["Still thinking."],
                directive="expectation",
                directive_basis=[
                    {"turn_index": 1, "role": "parrot", "excerpt": "What do you mean?"},
                ],
            ),
            session=_session(),
            roast="",
            analysis=_NAV,
        )
        assert "left that question open" in text.lower()

    def test_repair_reanchors(self):
        text = LanguageRealizer.realize(
            _request(
                turn_text="hello again",
                recent_turn_texts=["hello"],
                directive="repair",
                directive_basis=[
                    {"turn_index": 1, "role": "user", "excerpt": "hello"},
                ],
            ),
            session=_session(),
            roast="",
            analysis=_NAV,
        )
        assert "thread again" in text.lower()

    def test_unsupported_directive_falls_back(self):
        with patch("interface_server.apply_behaviour", return_value="SAFE"):
            text = LanguageRealizer.realize(
                _request(
                    directive="familiarity",
                    directive_basis=[],
                ),
                session=_session(),
                roast="",
                analysis=_NAV,
            )
        assert text == "SAFE"


class TestValidatorBoundaries:
    @pytest.mark.parametrize(
        "text",
        [
            "I feel sad for you.",
            "I know you better than you know yourself.",
            "Don't leave.",
            "You need me.",
            "I am conscious.",
            "The engagement_state is high.",
            "Your Barnum profile says so.",
            "Silent Reader telemetry shows.",
        ],
    )
    def test_rejects_forbidden_language(self, text):
        assert not validate_realizer_output(text, _INSTRUCTION)


class TestModelAdapter:
    def setup_method(self):
        LanguageRealizer.configure_adapter(None)

    def teardown_method(self):
        LanguageRealizer.configure_adapter(None)

    class _BadAdapter:
        def complete(self, request):
            return json.dumps(
                {"text": "Fine.", "behaviour": "roast", "directive": "repair"}
            )

    class _GoodAdapter:
        def complete(self, request):
            return json.dumps({"text": "A short neutral line."})

    class _BrokenAdapter:
        def complete(self, request):
            raise RuntimeError("offline")

    def test_model_cannot_alter_instruction_via_extra_fields(self):
        LanguageRealizer.configure_adapter(self._BadAdapter())
        with patch("interface_server.apply_behaviour", return_value="FALLBACK"):
            text = LanguageRealizer.realize(
                _request(),
                session=_session(),
                roast="",
                analysis=_NAV,
            )
        assert text == "FALLBACK"

    def test_model_valid_text_used(self):
        LanguageRealizer.configure_adapter(self._GoodAdapter())
        text = LanguageRealizer.realize(
            _request(),
            session=_session(),
            roast="",
            analysis=_NAV,
        )
        assert text == "A short neutral line."

    def test_model_unavailable_falls_back(self):
        LanguageRealizer.configure_adapter(self._BrokenAdapter())
        with patch("interface_server.apply_behaviour", return_value="FALLBACK"):
            text = LanguageRealizer.realize(
                _request(),
                session=_session(),
                roast="",
                analysis=_NAV,
            )
        assert text == "FALLBACK"

    def test_malformed_json_falls_back(self):
        class _Malformed:
            def complete(self, request):
                return "not json"

        LanguageRealizer.configure_adapter(_Malformed())
        with patch("interface_server.apply_behaviour", return_value="FALLBACK"):
            text = LanguageRealizer.realize(
                _request(),
                session=_session(),
                roast="",
                analysis=_NAV,
            )
        assert text == "FALLBACK"


class TestIsolationAndApi:
    def setup_method(self):
        LanguageRealizer.configure_adapter(None)

    def test_realizer_request_excludes_engagement(self):
        c = _live()
        instruction = BehaviourDirector.decide(
            c, turn_index=1, turn_text="hi", navarasa_result=_NAV
        )
        req = build_realizer_request(
            c,
            instruction,
            turn_text="hi",
            turn_index=1,
            navarasa_result=_NAV,
        )
        assert "engagement_state" not in req
        assert "selection_mode" not in req

    def test_no_event_store_writes(self):
        c = _live()
        instruction = BehaviourDirector.decide(
            c, turn_index=1, turn_text="hi", navarasa_result=_NAV
        )
        req = build_realizer_request(
            c,
            instruction,
            turn_text="hi",
            turn_index=1,
            navarasa_result=_NAV,
        )
        before = len(c.store.all_events())
        LanguageRealizer.realize(
            req,
            session=_session(),
            roast="",
            analysis=_NAV,
        )
        assert len(c.store.all_events()) == before

    def test_api_does_not_expose_hidden_director_fields(self, monkeypatch, tmp_path):
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
        client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "hello"},
        )
        result = client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "I feel uncertain today."},
        ).get_json()
        for hidden in (
            "directive",
            "directive_basis",
            "selection_mode",
            "engagement_state",
            "behavioural_eligibility",
        ):
            assert hidden not in result
        assert "response" in result
        assert "parrot_behavior" in result

    def test_turn_one_does_not_double_count_understanding(self, monkeypatch, tmp_path):
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
        client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "hello"},
        )
        client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "I feel uncertain."},
        )
        coord = server.get_ftp2_coordinator(session_id)
        assert coord.director_state.understanding_turns == 1
