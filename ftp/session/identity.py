"""FTP 2.0 – Session Identity.

Phase 2:
Encapsulates the immutable identity facts of a single participant
session: its UUID, creation timestamp, and display alias.

This is intentionally minimal.  It is NOT a profile.  It is just the
administrative handle that links every event to the correct store.

The Parrot receives only ``session_id`` (a bare string) from this
object, never the full ``SessionIdentity`` instance.
"""

from __future__ import annotations

import datetime
import uuid


class SessionIdentity:
    """Immutable identity envelope for one installation session.

    Parameters
    ----------
    session_id:
        Pre-existing UUIDv4 string.  If *None*, a new one is generated.
    """

    def __init__(self, session_id: str | None = None) -> None:
        self._session_id: str = (
            session_id if session_id is not None else str(uuid.uuid4())
        )
        self._created_at: str = datetime.datetime.now(
            tz=datetime.timezone.utc
        ).isoformat(timespec="microseconds")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        """UUIDv4 string uniquely identifying this session."""
        return self._session_id

    @property
    def created_at(self) -> str:
        """ISO-8601 UTC timestamp (microseconds) of session creation."""
        return self._created_at

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Minimal JSON-serialisable dict suitable for event payloads."""
        return {
            "session_id": self._session_id,
            "created_at": self._created_at,
        }

    def __repr__(self) -> str:
        return f"SessionIdentity(session_id={self._session_id!r})"
