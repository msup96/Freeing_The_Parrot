"""Phase 2 tests – Parrot ignorance boundary.

Covers TEST_STRATEGY.md §2.1:
- test_parrot_context_injection_rejection
- test_parrot_response_invariance (structural invariance via context dict)
- Structural audit: the context dict must not contain forbidden keys
- build_parrot_context() must produce only the permitted narrow set
- Integration: existing choose_behaviour() works unchanged with the
  parrot_session produced by build_parrot_context()
"""

import pytest

from ftp.events.store import StrictBoundaryViolationError
from ftp.session.coordinator import SessionCoordinator, _PARROT_FORBIDDEN_KEYS
from ftp.session.states import SessionState

# Import the live Parrot engine to verify behavioural parity
from ftp.parrot.engine import choose_behaviour, BEHAVIOUR_NAMES


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_CLEAN_NAVARASA = {
    "primary_rasa": "Shanta",
    "rasa_scores": {"Shanta": 1.0},
    "sentiment": {"compound": 0.0},
}


def make_live_coordinator() -> SessionCoordinator:
    c = SessionCoordinator()
    c.start()
    c.advance(SessionState.LIVE_CONVERSATION)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# build_parrot_context() structural invariants
# ─────────────────────────────────────────────────────────────────────────────

class TestParrotContextStructure:

    def test_context_contains_required_keys(self):
        c = make_live_coordinator()
        ctx = c.build_parrot_context(
            turn_text="I feel uncertain.",
            turn_index=1,
            navarasa_result=_CLEAN_NAVARASA,
        )
        assert "turn_text" in ctx
        assert "turn_index" in ctx
        assert "navarasa_result" in ctx
        assert "parrot_session" in ctx

    def test_context_does_not_contain_forbidden_keys(self):
        c = make_live_coordinator()
        ctx = c.build_parrot_context(
            turn_text="Hello.",
            turn_index=1,
            navarasa_result=_CLEAN_NAVARASA,
        )
        for forbidden in _PARROT_FORBIDDEN_KEYS:
            assert forbidden not in ctx, (
                f"Forbidden key {forbidden!r} found in Parrot context."
            )

    def test_context_parrot_session_does_not_contain_forbidden_keys(self):
        c = make_live_coordinator()
        ctx = c.build_parrot_context(
            turn_text="Hello.",
            turn_index=1,
            navarasa_result=_CLEAN_NAVARASA,
        )
        parrot_session = ctx["parrot_session"]
        for forbidden in _PARROT_FORBIDDEN_KEYS:
            assert forbidden not in parrot_session, (
                f"Forbidden key {forbidden!r} found in parrot_session."
            )

    def test_context_turn_text_matches_input(self):
        c = make_live_coordinator()
        ctx = c.build_parrot_context(
            turn_text="My specific input.",
            turn_index=3,
            navarasa_result=_CLEAN_NAVARASA,
        )
        assert ctx["turn_text"] == "My specific input."
        assert ctx["turn_index"] == 3

    def test_parrot_session_contains_only_permitted_keys(self):
        """The parrot_session sub-dict must not leak profile data."""
        c = make_live_coordinator()
        ctx = c.build_parrot_context(
            turn_text="Test.",
            turn_index=2,
            navarasa_result=_CLEAN_NAVARASA,
        )
        ps = ctx["parrot_session"]
        # These are the only permitted keys
        permitted = {
            "session_id",
            "understanding_turns",
            "substantive_turns",
            "chaos_count",
            "last_behaviour",
            "behaviour_history",
        }
        extra = set(ps.keys()) - permitted
        assert not extra, (
            f"parrot_session contains unexpected keys: {sorted(extra)}"
        )

    def test_parrot_session_session_id_is_bare_string_not_object(self):
        """The Parrot must receive only the bare session_id string."""
        c = make_live_coordinator()
        ctx = c.build_parrot_context("Text.", 1, _CLEAN_NAVARASA)
        sid = ctx["parrot_session"]["session_id"]
        assert isinstance(sid, str)
        # Must NOT be the SessionIdentity object or the coordinator itself
        assert not hasattr(sid, "session_id"), (
            "Parrot received a SessionIdentity object instead of a bare string."
        )

    def test_understanding_turns_matches_turn_index_for_early_turns(self):
        c = make_live_coordinator()
        for i in range(1, 4):
            ctx = c.build_parrot_context("text", i, _CLEAN_NAVARASA)
            ps = ctx["parrot_session"]
            assert ps["understanding_turns"] == i

    def test_understanding_turns_capped_at_3(self):
        c = make_live_coordinator()
        ctx = c.build_parrot_context("text", 10, _CLEAN_NAVARASA)
        ps = ctx["parrot_session"]
        assert ps["understanding_turns"] == 3


# ─────────────────────────────────────────────────────────────────────────────
# Forbidden key injection rejection
# ─────────────────────────────────────────────────────────────────────────────

class TestForbiddenKeyRejection:
    """Attempt to smuggle forbidden data through the navarasa_result
    slot.  The coordinator must detect and reject this."""

    @pytest.mark.parametrize("forbidden_key", list(_PARROT_FORBIDDEN_KEYS))
    def test_navarasa_result_with_forbidden_key_raises(self, forbidden_key):
        c = make_live_coordinator()
        poisoned_navarasa = {
            "primary_rasa": "Shanta",
            forbidden_key: "injected_value",
        }
        with pytest.raises(StrictBoundaryViolationError):
            c.build_parrot_context(
                turn_text="Test.",
                turn_index=1,
                navarasa_result=poisoned_navarasa,
            )

    def test_clean_navarasa_passes_without_error(self):
        c = make_live_coordinator()
        # Should not raise
        ctx = c.build_parrot_context("Text.", 1, _CLEAN_NAVARASA)
        assert ctx is not None


# ─────────────────────────────────────────────────────────────────────────────
# Behavioural parity – existing choose_behaviour works with coordinator context
# ─────────────────────────────────────────────────────────────────────────────

class TestBehaviouralParityWithCoordinatorContext:
    """The coordinator's parrot_session dict must be structurally
    compatible with the existing choose_behaviour() engine so that
    no behaviour is broken by Phase 2."""

    def test_choose_behaviour_accepts_coordinator_parrot_session_turn_1(self):
        c = make_live_coordinator()
        ctx = c.build_parrot_context("Hello.", 1, _CLEAN_NAVARASA)
        result = choose_behaviour(ctx["parrot_session"])
        assert result in BEHAVIOUR_NAMES

    def test_choose_behaviour_returns_understanding_in_trust_window(self):
        """Turn 1 must always return 'understanding' (trust window contract)."""
        c = make_live_coordinator()
        for _ in range(200):
            # Reset coordinator each time so understanding_turns resets
            fresh = make_live_coordinator()
            ctx = fresh.build_parrot_context("Hello.", 1, _CLEAN_NAVARASA)
            result = choose_behaviour(ctx["parrot_session"])
            assert result == "understanding", (
                f"Expected 'understanding' at turn 1, got {result!r}."
            )

    def test_choose_behaviour_accepts_later_turns(self):
        """Turn 10 must produce a valid behaviour from BEHAVIOUR_NAMES."""
        c = make_live_coordinator()
        ctx = c.build_parrot_context("A thought.", 10, _CLEAN_NAVARASA)
        result = choose_behaviour(ctx["parrot_session"])
        assert result in BEHAVIOUR_NAMES

    def test_two_sessions_with_identical_inputs_may_produce_different_behaviours(self):
        """Prove statistical independence: same turn_index, different sessions.
        This is a Monte Carlo check - over 500 samples, both sessions must
        occasionally differ (probabilistic chaos above turn 3)."""
        differences = 0
        for _ in range(500):
            ctx_a = make_live_coordinator().build_parrot_context(
                "Same text.", 10, _CLEAN_NAVARASA
            )
            ctx_b = make_live_coordinator().build_parrot_context(
                "Same text.", 10, _CLEAN_NAVARASA
            )
            a = choose_behaviour(ctx_a["parrot_session"])
            b = choose_behaviour(ctx_b["parrot_session"])
            if a != b:
                differences += 1

        # At turn 10 chaos ≈ 75%; two independent draws should differ often
        assert differences > 0, (
            "Expected some behavioural differences between independent sessions."
        )

    def test_session_id_in_context_does_not_affect_behaviour_distribution(self):
        """Behaviour must be statistically invariant with respect to session_id.
        Two sessions with radically different UUIDs but same turn_index must
        produce statistically comparable chaos rates.  We don't assert exact
        parity (random), only that both produce chaos (not locked to one value)."""
        c1 = make_live_coordinator()
        c2 = make_live_coordinator()

        results_1 = set()
        results_2 = set()

        for _ in range(300):
            ctx1 = c1.build_parrot_context("Text.", 10, _CLEAN_NAVARASA)
            ctx2 = c2.build_parrot_context("Text.", 10, _CLEAN_NAVARASA)
            results_1.add(choose_behaviour(ctx1["parrot_session"]))
            results_2.add(choose_behaviour(ctx2["parrot_session"]))

        # Both must show some diversity (not stuck on one behaviour)
        assert len(results_1) > 1, "Session 1 produced only one behaviour."
        assert len(results_2) > 1, "Session 2 produced only one behaviour."


# ─────────────────────────────────────────────────────────────────────────────
# Background data must not reach Parrot context (isolation structural test)
# ─────────────────────────────────────────────────────────────────────────────

class TestBackgroundDataStructuralIsolation:
    """This tests the structural guarantee: even if background analytics
    data is recorded in the event store, it cannot flow into the
    Parrot context dict.  We record 'forbidden' event types into the
    store and verify parrot_context() excludes them."""

    def test_silent_reader_events_never_enter_parrot_context(self):
        from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel

        c = make_live_coordinator()

        # Simulate Silent Reader recording telemetry
        c.store.append(InteractionEvent(
            session_id=c.session_id,
            event_type=EventType.TELEMETRY_RECORDED,
            provenance_level=ProvenanceLevel.OBSERVED,
            payload={
                "typing_duration_ms": 5000,
                "pause_before_submit_ms": 1200,
                "backspace_count": 3,
                # This is the kind of data the Parrot must NOT see
                "silent_reader_session_profile": {"hesitation_score": 0.82},
            },
        ))

        # The parrot_context() read path must exclude TELEMETRY_RECORDED
        parrot_view = c.store.parrot_context()
        for ev in parrot_view:
            assert ev.event_type != EventType.TELEMETRY_RECORDED, (
                "TELEMETRY_RECORDED event leaked into parrot_context()."
            )

    def test_post_session_events_never_enter_parrot_context(self):
        from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel

        c = make_live_coordinator()

        for etype in (
            EventType.CARDS_GENERATED,
            EventType.CARD_RESONANCE_MARKED,
            EventType.CONSENT_RECORDED,
            EventType.PROFILE_REVEAL_VIEWED,
        ):
            c.store.append(InteractionEvent(
                session_id=c.session_id,
                event_type=etype,
                provenance_level=ProvenanceLevel.INFERRED,
                payload={"data": "should not reach parrot"},
            ))

        parrot_view = c.store.parrot_context()
        forbidden_types = {
            EventType.CARDS_GENERATED,
            EventType.CARD_RESONANCE_MARKED,
            EventType.CONSENT_RECORDED,
            EventType.PROFILE_REVEAL_VIEWED,
        }
        for ev in parrot_view:
            assert ev.event_type not in forbidden_types, (
                f"Post-session event {ev.event_type} leaked into parrot_context()."
            )
