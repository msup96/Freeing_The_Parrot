"""FTP 2.0 – Session Coordinator.

Phase 2:
The Session Coordinator is the single orchestration point for one
participant session.  It owns:

  - SessionIdentity  (who this session is)
  - EventStore       (all events that happened)
  - SessionStateMachine (current lifecycle state)

And enforces:

  - The strict Parrot ignorance boundary via ``build_parrot_context()``.
  - All event recording flows through ``record()``.
  - All state transitions flow through ``advance()``.

The Parrot engine receives only what ``build_parrot_context()``
returns.  It is given no reference to the coordinator, the store, or
any profile data.  This makes accidental leakage into the Parrot
testable: a test can inspect the dict returned by
``build_parrot_context()`` and assert forbidden keys are absent.

Architecture notes
------------------
- SessionCoordinator does NOT call the Parrot engine itself.  That
  call is made by the HTTP handler (interface_server.py).  The
  coordinator hands the handler a context dict; the handler calls the
  Parrot; the handler records the result event back through the
  coordinator.
- This keeps the coordinator free of I/O and fully unit-testable.
- Phase 3 (Silent Reader, Gemini) will add read-only observers that
  watch ``all_events()`` without going through ``build_parrot_context()``.
"""

from __future__ import annotations

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel
from ftp.events.store import EventStore, StrictBoundaryViolationError
from ftp.session.identity import SessionIdentity
from ftp.session.machine import IllegalTransitionError, SessionStateMachine
from ftp.session.states import SessionState
from ftp.parrot.director_state import DirectorState
from ftp.silent_reader.observer import (
    SilentReaderObserver,
    build_telemetry_payload,
)


class SessionLockedError(Exception):
    """Raised when a Parrot turn is recorded after the session is locked."""


# Keys that must NEVER appear in the Parrot context dict.
# This list is the enforcement complement to EventStore.assert_no_forbidden_payload().
_PARROT_FORBIDDEN_KEYS: tuple[str, ...] = (
    "silent_reader_telemetry",
    "gemini_inferences",
    "profile_data",
    "card_selections",
    "participant_profile",
    "gender_inference",
    "identity_inference",
    "long_term_history",
    "accumulated_rasa_history",
    "cross_session_data",
    "engagement_evidence",
    "engagement_state",
    "engagement_score",
    "behavioural_eligibility",
    "fracture_eligibility",
    "evidence_bundle",
    "evidence_items",
    "candidate_inference",
    "inferred_claim",
    "alternatives",
    "contradictions",
    "confidence",
    "interpretation",
    "deep_reader",
    "reading_profile",
    "hidden_provenance",
    "qualitative_reading",
    "director_state",
)


class SessionCoordinator:
    """Orchestrator for one FTP 2.0 participant session.

    Parameters
    ----------
    session_id:
        Optional pre-existing UUIDv4 string.  If *None*, a new UUID
        is generated.

    Usage
    -----
    ::

        coordinator = SessionCoordinator()
        coordinator.start()                    # IDLE → INPUT_INGESTION

        # ... input handling ...

        coordinator.advance(SessionState.LIVE_CONVERSATION)

        for user_turn in turns:
            ctx = coordinator.build_parrot_context(
                turn_text=user_turn,
                turn_index=coordinator.turn_count,
                navarasa_result={...},
            )
            reply = parrot_engine.choose_behaviour(ctx["parrot_session"])
            coordinator.record_parrot_turn(turn_text=user_turn, reply=reply)
    """

    def __init__(self, session_id: str | None = None, persistence=None) -> None:
        self._identity = SessionIdentity(session_id=session_id)
        self._persistence = persistence
        self._store = EventStore(
            session_id=self._identity.session_id,
            on_append=(persistence.append_event if persistence is not None else None),
        )
        self._machine = SessionStateMachine(
            on_transition=self._on_state_change,
        )
        self._turn_count: int = 0
        self._analysis_ready: bool = False
        self._silent_reader = SilentReaderObserver(self)
        self._director_state = DirectorState()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._identity.session_id

    @property
    def state(self) -> SessionState:
        return self._machine.state

    @property
    def turn_count(self) -> int:
        return self._turn_count

    @property
    def analysis_ready(self) -> bool:
        """Whether the initial hidden analysis has completed."""
        return self._analysis_ready

    @property
    def store(self) -> EventStore:
        """Read-only reference to the event store (for observers)."""
        return self._store

    @property
    def machine(self) -> SessionStateMachine:
        """Read-only reference to the state machine (for inspectors)."""
        return self._machine

    @property
    def silent_reader(self) -> SilentReaderObserver:
        """Passive telemetry observer for this session."""
        return self._silent_reader

    @property
    def director_state(self) -> DirectorState:
        """Session-local Parrot behaviour state (not for Parrot context export)."""
        return self._director_state

    def reset_director_state(self) -> None:
        """Clear behaviour counters/history for this session."""
        self._director_state.clear()

    def apply_parrot_session_state(self, parrot_session: dict) -> None:
        """Persist legacy engine mutations after ``choose_behaviour()``."""
        self._director_state.absorb_parrot_session(parrot_session)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Transition IDLE_STANDBY → INPUT_INGESTION and log SESSION_STARTED."""
        self.advance(SessionState.INPUT_INGESTION)
        self.record(
            event_type=EventType.SESSION_STARTED,
            provenance_level=ProvenanceLevel.OBSERVED,
            payload=self._identity.to_dict(),
        )

    def advance(self, target: SessionState) -> None:
        """Attempt a validated state transition.

        Delegates to ``SessionStateMachine.transition()``.

        Raises
        ------
        IllegalTransitionError
            If the transition is not listed in LEGAL_TRANSITIONS.
        """
        self._machine.transition(target)

    # ------------------------------------------------------------------
    # Event recording
    # ------------------------------------------------------------------

    def record(
        self,
        event_type: EventType,
        provenance_level: ProvenanceLevel,
        payload: dict,
    ) -> InteractionEvent:
        """Create and append an event, returning the stamped copy."""
        event = InteractionEvent(
            session_id=self._identity.session_id,
            event_type=event_type,
            provenance_level=provenance_level,
            payload=payload,
        )
        return self._store.append(event)

    def record_raw_input(self, payload: dict) -> InteractionEvent:
        """Record multimodal RAW ingest (observation only; Parrot must not see it)."""
        if self._machine.is_locked():
            raise SessionLockedError(
                "Cannot record raw input after the session is locked."
            )
        if self._machine.state not in (
            SessionState.INPUT_INGESTION,
            SessionState.LIVE_CONVERSATION,
        ):
            raise ValueError(
                "Raw input may only be recorded during INPUT_INGESTION "
                "or LIVE_CONVERSATION."
            )
        return self.record(
            event_type=EventType.INPUT_RAW_INGESTED,
            provenance_level=ProvenanceLevel.RAW,
            payload=payload,
        )

    def mark_analysis_ready(self, analysis: dict) -> InteractionEvent:
        """Record hidden initial analysis without exposing it to the Parrot."""
        if self._machine.state != SessionState.INPUT_INGESTION:
            raise ValueError(
                "Initial analysis may only complete during INPUT_INGESTION."
            )
        event = self.record(
            event_type=EventType.NAVARASA_CLASSIFIED,
            provenance_level=ProvenanceLevel.INTERPRETED,
            payload=analysis,
        )
        self._analysis_ready = True
        return event

    def mark_raw_offering_ready(self) -> None:
        """Mark intake complete after a raw media offering is stored.

        The current architecture records the file and its metadata only.
        This does not invent OCR, ASR, or a Navarasa classification.
        """
        if self._machine.state != SessionState.INPUT_INGESTION:
            raise ValueError(
                "Raw offering readiness may only complete during INPUT_INGESTION."
            )
        self._analysis_ready = True

    def record_silent_reader_observation(self, payload: dict) -> InteractionEvent:
        """Record a Silent Reader OBSERVED payload (never visible to Parrot)."""
        if self._machine.is_locked():
            raise SessionLockedError(
                "Cannot record Silent Reader observations after lock."
            )
        if self._machine.state != SessionState.LIVE_CONVERSATION:
            raise ValueError(
                "Observations may only be recorded during LIVE_CONVERSATION."
            )
        return self.record(
            event_type=EventType.TELEMETRY_RECORDED,
            provenance_level=ProvenanceLevel.OBSERVED,
            payload=payload,
        )

    def record_turn_telemetry(
        self,
        *,
        turn_index: int,
        typing_duration_ms: float,
        pause_before_submit_ms: float,
        message_length: int,
    ) -> InteractionEvent:
        """Record Silent Reader composer telemetry (Phase 3A API)."""
        return self.record_silent_reader_observation(
            build_telemetry_payload(
                turn_index,
                typing_duration_ms,
                pause_before_submit_ms,
                message_length,
            )
        )

    def record_turn_analysis(
        self,
        *,
        turn_index: int,
        analysis: dict,
    ) -> InteractionEvent:
        """Record the sanitized, immutable analysis snapshot for one turn."""
        if self._machine.is_locked():
            raise SessionLockedError("Cannot record analysis after the session is locked.")
        return self.record(
            event_type=EventType.NAVARASA_CLASSIFIED,
            provenance_level=ProvenanceLevel.INTERPRETED,
            payload={
                "turn_index": turn_index,
                "lineage_id": f"{self.session_id}:turn:{turn_index}",
                "analysis": dict(analysis),
            },
        )

    def record_observed_parrot_turn(
        self,
        *,
        turn_index: int,
        turn_text: str,
        reply: str,
        behaviour: str = "",
        gate: str = "",
        analysis_snapshot: dict | None = None,
        decision_metadata: dict | None = None,
    ) -> InteractionEvent:
        """Record a Parrot turn at a fixed index without incrementing turn_count."""
        if self._machine.is_locked():
            raise SessionLockedError(
                "Cannot record Parrot turns after the session is locked."
            )
        return self.record(
            event_type=EventType.PARROT_TURN_GENERATED,
            provenance_level=ProvenanceLevel.OBSERVED,
            payload={
                "turn_index": turn_index,
                "user_text": turn_text,
                "parrot_reply": reply,
            "behaviour": behaviour,
            "gate": gate,
            "lineage_id": f"{self.session_id}:turn:{turn_index}",
            "analysis_snapshot": dict(analysis_snapshot or {}),
            "decision_metadata": dict(decision_metadata or {}),
        },
    )

    def record_parrot_turn(
        self,
        turn_text: str,
        reply: str,
        behaviour: str = "",
        gate: str = "",
        analysis_snapshot: dict | None = None,
        decision_metadata: dict | None = None,
    ) -> InteractionEvent:
        """Record one completed Parrot turn and increment the turn counter."""
        if self._machine.is_locked():
            raise SessionLockedError(
                "Cannot record Parrot turns after the session is locked."
            )
        self._turn_count += 1
        return self.record(
            event_type=EventType.PARROT_TURN_GENERATED,
            provenance_level=ProvenanceLevel.OBSERVED,
            payload={
                "turn_index": self._turn_count,
                "user_text": turn_text,
                "parrot_reply": reply,
            "behaviour": behaviour,
            "gate": gate,
            "lineage_id": f"{self.session_id}:turn:{self._turn_count}",
            "analysis_snapshot": dict(analysis_snapshot or {}),
            "decision_metadata": dict(decision_metadata or {}),
        },
    )

    # ------------------------------------------------------------------
    # Parrot ignorance boundary
    # ------------------------------------------------------------------

    def build_parrot_context(
        self,
        turn_text: str,
        turn_index: int,
        navarasa_result: dict,
    ) -> dict:
        """Build the context dict permitted to flow into the Parrot engine.

        This is the *sole* read path the Parrot should use.  It
        explicitly contains only:

        - ``turn_text``      — the current participant input
        - ``turn_index``     — which turn number this is
        - ``navarasa_result`` — the deterministic single-turn classification
        - ``parrot_session`` — the minimal behaviour-engine session dict
          (mirrors the existing interface_server session dict structure)

        Nothing else.  Background telemetry, card data, Gemini output,
        accumulated Navarasa history, and profile data are structurally
        absent.

        Raises
        ------
        StrictBoundaryViolationError
            If ``navarasa_result`` accidentally contains a forbidden key
            (defence-in-depth check).
        """
        # Defence-in-depth: validate the navarasa_result doesn't smuggle
        # forbidden data through the navarasa slot.
        _check_forbidden_keys(navarasa_result, "navarasa_result")

        # Build the minimal parrot_session dict the existing choose_behaviour()
        # expects.  substantive_turns tracks the live turn index; behaviour
        # counters/history come from session-local DirectorState (not reset
        # each call).
        parrot_session = self._director_state.parrot_session_view(
            session_id=self._identity.session_id,
            substantive_turns=turn_index,
        )
        _check_forbidden_keys(parrot_session, "parrot_session")

        return {
            "turn_text": turn_text,
            "turn_index": turn_index,
            "navarasa_result": navarasa_result,
            "parrot_session": parrot_session,
        }

    # ------------------------------------------------------------------
    # Session lock
    # ------------------------------------------------------------------

    def lock(self) -> None:
        """Transition to SESSION_CONCLUDED and emit SESSION_LOCKED event."""
        self.advance(SessionState.SESSION_CONCLUDED)
        self.record(
            event_type=EventType.SESSION_LOCKED,
            provenance_level=ProvenanceLevel.OBSERVED,
            payload={
                "session_id": self._identity.session_id,
                "final_turn_count": self._turn_count,
            },
        )

    def synthesize_temporal_trajectories(self) -> dict:
        """Build session-level temporal trajectories after lock.

        Available once the session is locked. Output stays out of
        ``build_parrot_context()``.
        """
        if not self._machine.is_locked():
            raise ValueError(
                "Temporal trajectories may only be synthesized after "
                "the session is locked."
            )
        from ftp.silent_reader.trajectories import TemporalTrajectorySynthesizer

        return TemporalTrajectorySynthesizer(self).synthesize()

    def synthesize_linguistic_trajectories(self) -> dict:
        """Build session-level linguistic trajectories after lock."""
        if not self._machine.is_locked():
            raise ValueError(
                "Linguistic trajectories may only be synthesized after "
                "the session is locked."
            )
        from ftp.silent_reader.linguistic import LinguisticTrajectorySynthesizer

        return LinguisticTrajectorySynthesizer(self).synthesize()

    def synthesize_navarasa_trajectories(self) -> dict:
        """Build post-session Navarasa trajectories after lock."""
        if not self._machine.is_locked():
            raise ValueError(
                "Navarasa trajectories may only be synthesized after "
                "the session is locked."
            )
        from ftp.silent_reader.navarasa_trajectory import NavarasaTrajectorySynthesizer

        return NavarasaTrajectorySynthesizer(self).synthesize()

    def synthesize_engagement(self) -> dict:
        """Build post-lock engagement evidence and interaction state.

        The result stays in memory and out of ``build_parrot_context()``.
        """
        if not self._machine.is_locked():
            raise ValueError(
                "Engagement synthesis may only run after the session is locked."
            )
        from ftp.silent_reader.engagement import EngagementSynthesizer

        return EngagementSynthesizer(self).synthesize()

    def live_engagement_snapshot(self) -> dict:
        """Build live engagement evidence/state for the Behaviour Director.

        Available only during ``LIVE_CONVERSATION`` before lock. Never flows
        into ``build_parrot_context()`` or the event store.
        """
        from ftp.silent_reader.engagement import build_live_engagement_snapshot

        return build_live_engagement_snapshot(self)

    def build_evidence_bundle(self) -> dict:
        """Curate Phase 3 outputs into an evidence bundle after lock."""
        if not self._machine.is_locked():
            raise ValueError(
                "Evidence bundles may only be built after the session is locked."
            )
        from ftp.silent_reader.evidence import EvidenceBundleBuilder

        return EvidenceBundleBuilder(self).build()

    def evaluate_session_inferences(self) -> dict:
        """Apply the evidence contract to session candidates after lock."""
        if not self._machine.is_locked():
            raise ValueError(
                "Inferences may only be evaluated after the session is locked."
            )
        from ftp.silent_reader.inference import evaluate_bundle

        return evaluate_bundle(self.build_evidence_bundle())

    def read_session(self, adapter=None) -> dict:
        """Apply the Phase 4B gloss layer after lock. Result stays in memory."""
        if not self._machine.is_locked():
            raise ValueError(
                "Session reading may only run after the session is locked."
            )
        from ftp.silent_reader.inference import evaluate_bundle
        from ftp.silent_reader.deep_reader.adapter import GeminiReaderAdapter
        from ftp.silent_reader.deep_reader.read import read_session_interpretations

        bundle = self.build_evidence_bundle()
        evaluation = evaluate_bundle(bundle)
        if adapter is None:
            adapter = GeminiReaderAdapter()
        return read_session_interpretations(bundle, evaluation, adapter)

    def compose_post_session_reading(self, adapter=None) -> dict:
        """Build and validate the 27-card deck from Phase 4B output."""
        if self._machine.state != SessionState.POST_SESSION_INTERPRETATION:
            raise ValueError(
                "Post-session reading may only be composed during "
                "POST_SESSION_INTERPRETATION."
            )
        from ftp.silent_reader.reading.compose import compose_reading_deck

        return compose_reading_deck(self, adapter=adapter)

    def generate_post_session_interpretation(self) -> dict:
        """Create the hidden post-session deck without exposing it to the Parrot."""
        deck = self.compose_post_session_reading()
        self.record(
            event_type=EventType.CARDS_GENERATED,
            provenance_level=ProvenanceLevel.INFERRED,
            payload={
                "session_id": self._identity.session_id,
                "card_count": deck["total_cards"],
                "source": deck.get("source", "phase_4c_reading_composer"),
                "cards": deck["cards"],
            },
        )
        return deck

    def mark_card_resonance(self, *, card_id: str, card_index: int) -> InteractionEvent:
        """Record participant RESONATES. This does not make the reading true."""
        if self._machine.state != SessionState.CARD_SELECTION:
            raise ValueError("Card resonance may only be marked during CARD_SELECTION.")
        events = self._store.events_of_type(EventType.CARDS_GENERATED)
        if not events:
            raise ValueError("No generated deck is available for this session.")
        deck = {
            "cards": events[-1].payload["cards"],
            "total_cards": events[-1].payload.get("card_count", 27),
        }
        from ftp.silent_reader.reading.validate import validate_card_resonance

        payload = validate_card_resonance(deck, card_id=card_id, card_index=card_index)
        return self.record(
            EventType.CARD_RESONANCE_MARKED,
            ProvenanceLevel.VALIDATED,
            payload,
        )

    # ------------------------------------------------------------------
    # Internal callbacks
    # ------------------------------------------------------------------

    def _on_state_change(
        self, previous: SessionState, current: SessionState
    ) -> None:
        """Emit a SESSION_STATE_CHANGED event each time the SM transitions."""
        if current == SessionState.PURGE_AND_RESET:
            self.reset_director_state()

        # Avoid recording state changes before the store is initialised
        # (shouldn't happen in normal usage, but defensive).
        try:
            self._store.append(
                InteractionEvent(
                    session_id=self._identity.session_id,
                    event_type=EventType.SESSION_STATE_CHANGED,
                    provenance_level=ProvenanceLevel.OBSERVED,
                    payload={
                        "previous_state": previous.value,
                        "current_state": current.value,
                    },
                )
            )
        except Exception:
            # Never let event recording crash the state machine.
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _check_forbidden_keys(d: dict, label: str) -> None:
    """Raise StrictBoundaryViolationError if *d* contains any forbidden key."""
    violations = [k for k in _PARROT_FORBIDDEN_KEYS if k in d]
    if violations:
        raise StrictBoundaryViolationError(
            f"Parrot boundary violation in {label!r}: "
            f"forbidden keys present: {violations!r}"
        )
