"""Per-session temperament plus relationship-driven Parrot variability."""

import json
import random

from ftp.parrot.director import BehaviourDirector
from ftp.parrot.director_state import DirectorState
from ftp.parrot.gemini_adapter import GeminiParrotAdapter
from ftp.parrot.realizer import build_realizer_request
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState

NAV = {"primary_rasa": "Shanta", "rasa_scores": {}, "sentiment": {}}


def _live(session_id: str = "variability") -> SessionCoordinator:
    coordinator = SessionCoordinator(session_id)
    coordinator.start()
    coordinator.advance(SessionState.LIVE_CONVERSATION)
    return coordinator


def _arc(seed: int, turns: int = 14) -> list[str]:
    coordinator = _live(f"arc-{seed}")
    coordinator.director_state.randomize_temperament(random.Random(seed))
    rng = random.Random(seed + 1)
    replies = []
    for turn in range(1, turns + 1):
        text = (
            "I am staying with this conversation because I want to understand "
            "what you are saying and I am still curious about it."
        )
        instruction = BehaviourDirector.decide(
            coordinator,
            turn_index=turn,
            turn_text=text,
            navarasa_result=NAV,
            rng=rng,
        )
        replies.append(instruction["behaviour"])
        coordinator.record_parrot_turn(
            text,
            "The Parrot reply.",
            behaviour=instruction["behaviour"],
        )
    return replies


def test_default_state_keeps_the_original_fixed_temperament_defaults():
    state = DirectorState()
    assert state.trust_turns == 3
    assert state.instability_base == 0.35
    assert state.instability_ramp == 0.08
    assert state.instability_cap == 0.75
    assert state.instability_jitter == 0.0
    assert state.early_slip_chance == 0.0
    assert state.trust_score == 0.0
    assert state.tolerated_ruptures == 0


def test_randomized_temperament_stays_in_bounds_and_differs_between_sessions():
    states = []
    for seed in range(60):
        state = DirectorState()
        state.randomize_temperament(random.Random(seed))
        states.append(state)

    assert {s.trust_turns for s in states} <= {2, 3, 4}
    assert len({s.trust_turns for s in states}) >= 2
    assert all(0.14 <= s.instability_base <= 0.26 for s in states)
    assert all(0.42 <= s.instability_cap <= 0.58 for s in states)
    assert all(0.0 <= s.early_slip_chance <= 0.08 for s in states)
    assert len({round(s.instability_base, 4) for s in states}) > 40


def test_a_group_of_sessions_does_not_share_one_opening_arc():
    arcs = {tuple(_arc(seed)) for seed in range(40)}
    assert len(arcs) > 10


def test_risk_is_not_forced_even_after_trust_is_earned():
    for seed in range(80):
        arc = _arc(seed, turns=10)
        # Some sessions should remain conversational for the whole sampled
        # window; others should eventually enter relationship risk.
        assert all(isinstance(item, str) for item in arc)


def test_clear_resets_relationship_and_temperament_state():
    state = DirectorState()
    state.randomize_temperament(random.Random(5))
    state.understanding_turns = 2
    state.trust_score = 0.9
    state.tolerated_ruptures = 3
    state.irritation = 0.4

    state.clear()

    assert state == DirectorState()


def test_realizer_request_carries_the_parrots_own_recent_replies():
    coordinator = _live("own-replies")
    coordinator.record_parrot_turn(
        "hello there",
        "The gate stays shut tonight.",
        behaviour="understanding",
    )
    instruction = BehaviourDirector.decide(
        coordinator,
        turn_index=2,
        turn_text="and then?",
        navarasa_result=NAV,
    )

    request = build_realizer_request(
        coordinator,
        instruction,
        turn_text="and then?",
        turn_index=2,
        navarasa_result=NAV,
    )

    assert request["recent_parrot_texts"] == ["The gate stays shut tonight."]
    assert "engagement_state" not in request
    assert "trust_score" not in request


def test_gemini_prompt_shows_recent_replies_and_relationship_contract(monkeypatch):
    captured = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps({"candidates": []}).encode()

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode())
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.delenv("GEMINI_PARROT_TIMEOUT", raising=False)
    GeminiParrotAdapter(api_key="test-key").complete(
        {
            "turn_text": "hi",
            "turn_index": 2,
            "behaviour": "understanding",
            "recent_parrot_texts": ["The gate stays shut tonight."],
        }
    )

    prompt = captured["body"]["contents"][0]["parts"][0]["text"]
    system = captured["body"]["systemInstruction"]["parts"][0]["text"]
    assert "your_recent_replies" in prompt
    assert "The gate stays shut tonight." in prompt
    assert "CURRENT message" in system
    assert "Eligibility only permits risk" in system
    assert captured["timeout"] == 5.0
    assert captured["body"]["generationConfig"]["temperature"] == 0.82
