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

    def __init__(self, session_id: str | None = None) -> None:
        self._identity = SessionIdentity(session_id=session_id)
        self._store = EventStore(session_id=self._identity.session_id)
        self._machine = SessionStateMachine(
            on_transition=self._on_state_change,
        )
        self._turn_count: int = 0
        self._analysis_ready: bool = False
        self._silent_reader = SilentReaderObserver(self)

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

    def record_observed_parrot_turn(
        self,
        *,
        turn_index: int,
        turn_text: str,
        reply: str,
        behaviour: str = "",
        gate: str = "",
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
            },
        )

    def record_parrot_turn(
        self,
        turn_text: str,
        reply: str,
        behaviour: str = "",
        gate: str = "",
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
        # expects.  Critically, we derive understanding_turns and
        # substantive_turns ONLY from the turn_index, not from any
        # accumulated profile.
        understanding_turns = min(turn_index, 3)
        substantive_turns = turn_index

        parrot_session: dict = {
            "session_id": self._identity.session_id,   # bare string only
            "understanding_turns": understanding_turns,
            "substantive_turns": substantive_turns,
            "chaos_count": 0,
            "last_behaviour": None,
            "behaviour_history": [],
        }

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

    # ------------------------------------------------------------------
    # Internal callbacks
    # ------------------------------------------------------------------

    def _on_state_change(
        self, previous: SessionState, current: SessionState
    ) -> None:
        """Emit a SESSION_STATE_CHANGED event each time the SM transitions."""
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
