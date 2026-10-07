"""FTP 2.0 – In-Memory Append-Only Event Store.

Phase 2:
A session-scoped, append-only event store that guarantees:

1. Monotonic, gapless sequence numbering starting from 1.
2. Immutability of already-appended events (the internal list is
   never mutated after append).
3. Strict session isolation: the store only accepts events whose
   session_id matches the session it was created for.
4. A dedicated Parrot-safe read path that returns ONLY events
   permitted under the ignorance boundary.

Architectural notes
-------------------
This is an *in-memory* store for Phase 2.  A durable backend (SQLite
/ PostgreSQL append-only table) can be swapped in later by replacing
``_events`` with a database-backed sequence without changing any
callers.

Thread safety: ``_lock`` makes append + sequence assignment atomic so
that rapid concurrent appends (e.g. from Silent Reader) cannot create
duplicate or out-of-order sequence numbers.
"""

from __future__ import annotations

import threading
from typing import Callable

from ftp.events.model import EventType, InteractionEvent


class StrictBoundaryViolationError(Exception):
    """Raised when a caller attempts to pass a forbidden event type
    to the Parrot context view."""


class EventStore:
    """Session-scoped, append-only, monotonically-sequenced event store.

    Parameters
    ----------
    session_id:
        The UUIDv4 string identifying the session this store belongs to.
    """

    def __init__(self, session_id: str, on_append: Callable[[InteractionEvent], None] | None = None) -> None:
        self._session_id: str = session_id
        self._events: list[InteractionEvent] = []
        self._on_append = on_append
        self._lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def append(self, event: InteractionEvent) -> InteractionEvent:
        """Append an event and return it with the assigned sequence_num.

        The returned object is a new frozen copy with ``sequence_num``
        stamped in.  The original object passed in is NOT mutated.

        Raises
        ------
        ValueError
            If ``event.session_id`` does not match this store's session.
        """
        if event.session_id != self._session_id:
            raise ValueError(
                f"Event session_id {event.session_id!r} does not match "
                f"store session_id {self._session_id!r}."
            )

        with self._lock:
            seq = len(self._events) + 1
            # Frozen dataclass: use object.__setattr__ to stamp sequence.
            # We create a new instance rather than mutate to preserve the
            # immutability contract of the *returned* event object.
            stamped = _stamp_sequence(event, seq)
            if self._on_append is not None:
                self._on_append(stamped)
            self._events.append(stamped)
            return stamped

    # ------------------------------------------------------------------
    # Read paths
    # ------------------------------------------------------------------

    def all_events(self) -> tuple[InteractionEvent, ...]:
        """Return an immutable snapshot of every event in the store."""
        with self._lock:
            return tuple(self._events)

    def events_of_type(
        self, *event_types: EventType
    ) -> tuple[InteractionEvent, ...]:
        """Return all events whose event_type is in ``event_types``."""
        with self._lock:
            return tuple(
                e for e in self._events
                if e.event_type in event_types
            )

    def parrot_context(self) -> tuple[InteractionEvent, ...]:
        """Return ONLY events the live Parrot is permitted to see.

        This is the ignorance boundary read path.  It calls
        ``InteractionEvent.is_live_parrot_eligible()`` and returns
        only events that pass.  Background telemetry, Gemini
        inferences, card data, Silent Reader observations, consent
        records, and session-lifecycle events are ALL excluded.

        Callers that need the full history must use ``all_events()``
        and must be outside the Parrot subsystem.
        """
        with self._lock:
            return tuple(
                e for e in self._events
                if e.is_live_parrot_eligible()
            )

    def assert_no_forbidden_payload(
        self,
        event: InteractionEvent,
        forbidden_keys: tuple[str, ...] = (
            "silent_reader_telemetry",
            "gemini_inferences",
            "profile_data",
            "card_selections",
            "participant_profile",
            "gender_inference",
            "identity_inference",
            "long_term_history",
        ),
    ) -> None:
        """Validate that an event payload does not contain forbidden keys.

        This is called by SessionCoordinator before building the
        Parrot context dict, providing a testable enforcement point
        for the ignorance boundary invariant.

        Raises
        ------
        StrictBoundaryViolationError
            If any forbidden key is present in ``event.payload``.
        """
        violations = [k for k in forbidden_keys if k in event.payload]
        if violations:
            raise StrictBoundaryViolationError(
                f"Parrot boundary violation: event {event.event_id!r} "
                f"contains forbidden payload keys: {violations!r}. "
                f"The Parrot must remain ignorant of profiling data."
            )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _stamp_sequence(
    event: InteractionEvent, seq: int
) -> InteractionEvent:
    """Return a new InteractionEvent with sequence_num set to *seq*.

    We reconstruct the frozen dataclass using its own field values so
    that the caller's original object is not mutated.
    """
    import dataclasses
    return dataclasses.replace(event, sequence_num=seq)
