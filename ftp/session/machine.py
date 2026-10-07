"""FTP 2.0 – Session State Machine.

Phase 2:
Implements the deterministic state machine that governs session
lifecycle.

Invariants
----------
1. Every attempted transition is validated against LEGAL_TRANSITIONS.
   An illegal move raises ``IllegalTransitionError`` and leaves the
   state unchanged.
2. AI outputs (Parrot replies, Gemini content) cannot call
   ``transition()`` — they have no reference to this object.
3. All transitions are logged as ``SESSION_STATE_CHANGED`` events via
   the injected callback so the Event Store captures the full history.
4. The machine starts in ``IDLE_STANDBY`` by default.
"""

from __future__ import annotations

from typing import Callable

from ftp.session.states import LEGAL_TRANSITIONS, SessionState


class IllegalTransitionError(Exception):
    """Raised when a caller attempts an illegal state transition."""

    def __init__(
        self,
        current: SessionState,
        target: SessionState,
    ) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Illegal transition: {current.value} → {target.value}. "
            f"Legal targets from {current.value}: "
            f"{sorted(s.value for s in LEGAL_TRANSITIONS.get(current, frozenset()))}"
        )


class SessionStateMachine:
    """Deterministic, validated state machine for one FTP 2.0 session.

    Parameters
    ----------
    on_transition:
        Optional callback invoked *after* a successful transition.
        Signature: ``(previous: SessionState, current: SessionState) -> None``.
        Use this to emit ``SESSION_STATE_CHANGED`` events to the store.
    initial_state:
        Starting state.  Defaults to ``IDLE_STANDBY``.
    """

    def __init__(
        self,
        on_transition: Callable[[SessionState, SessionState], None] | None = None,
        initial_state: SessionState = SessionState.IDLE_STANDBY,
    ) -> None:
        self._state: SessionState = initial_state
        self._history: list[SessionState] = [initial_state]
        self._on_transition = on_transition

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @property
    def state(self) -> SessionState:
        """Current (most recent) state."""
        return self._state

    @property
    def history(self) -> tuple[SessionState, ...]:
        """Immutable snapshot of the full state history."""
        return tuple(self._history)

    def can_transition_to(self, target: SessionState) -> bool:
        """Return True if moving to *target* from the current state is legal."""
        return target in LEGAL_TRANSITIONS.get(self._state, frozenset())

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def transition(self, target: SessionState) -> None:
        """Attempt to move to *target*.

        Raises
        ------
        IllegalTransitionError
            If the move is not listed in ``LEGAL_TRANSITIONS`` for the
            current state.
        """
        if not self.can_transition_to(target):
            raise IllegalTransitionError(self._state, target)

        previous = self._state
        self._state = target
        self._history.append(target)

        if self._on_transition is not None:
            self._on_transition(previous, target)

    def hydrate_history(self, states: list[SessionState]) -> None:
        """Restore validated persisted history without firing callbacks."""
        if not states:
            return
        self._history = [SessionState.IDLE_STANDBY]
        self._state = SessionState.IDLE_STANDBY
        for target in states:
            if self.can_transition_to(target):
                self._state = target
                self._history.append(target)

    # ------------------------------------------------------------------
    # Convenience shortcuts used by SessionCoordinator
    # ------------------------------------------------------------------

    def is_live(self) -> bool:
        """True while the session is in LIVE_CONVERSATION."""
        return self._state == SessionState.LIVE_CONVERSATION

    def is_locked(self) -> bool:
        """True when the session is concluded (Parrot permanently disabled)."""
        return self._state in (
            SessionState.SESSION_CONCLUDED,
            SessionState.POST_SESSION_INTERPRETATION,
            SessionState.CARD_SELECTION,
            SessionState.PROFILE_REVEAL,
            SessionState.DATA_WALL_CONSENT,
            SessionState.OUTPUT_GENERATION,
            SessionState.PURGE_AND_RESET,
        )

    def __repr__(self) -> str:
        return (
            f"SessionStateMachine(state={self._state.value!r}, "
            f"history_len={len(self._history)})"
        )
