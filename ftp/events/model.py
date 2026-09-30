"""FTP 2.0 – Canonical Event Model.

Phase 2:
Defines the canonical InteractionEvent dataclass and associated
enum vocabulary used throughout the Event Store and Session
Coordinator.  No external dependencies beyond the standard library.

Design decisions:
- Frozen dataclass: events are immutable once created.
- sequence_num is assigned by the store, not the caller.
- payload is typed as dict[str, object] so schema validation can
  be layered on top without changing this module.
- ProvenanceLevel mirrors the five-tier hierarchy in ARCHITECTURE.md.
"""

from __future__ import annotations

import datetime
import enum
import uuid
from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Provenance tiers (DATA_MODEL.md §1)
# ─────────────────────────────────────────────────────────────────────────────

class ProvenanceLevel(str, enum.Enum):
    """Five-tier data provenance hierarchy."""
    RAW = "RAW"
    OBSERVED = "OBSERVED"
    INTERPRETED = "INTERPRETED"
    INFERRED = "INFERRED"
    VALIDATED = "VALIDATED"


# ─────────────────────────────────────────────────────────────────────────────
# Event type vocabulary (DATA_MODEL.md §2.2)
# ─────────────────────────────────────────────────────────────────────────────

class EventType(str, enum.Enum):
    """All legal event types that can appear in the Event Store."""

    # --- Input pipeline ---
    INPUT_RAW_INGESTED       = "INPUT_RAW_INGESTED"
    OCR_TEXT_EXTRACTED       = "OCR_TEXT_EXTRACTED"
    AUDIO_ASR_TRANSCRIBED    = "AUDIO_ASR_TRANSCRIBED"
    TELEMETRY_RECORDED       = "TELEMETRY_RECORDED"

    # --- Live-session events ---
    NAVARASA_CLASSIFIED      = "NAVARASA_CLASSIFIED"
    PARROT_TURN_GENERATED    = "PARROT_TURN_GENERATED"
    INTERVENTION_TRIGGERED   = "INTERVENTION_TRIGGERED"

    # --- Session lifecycle ---
    SESSION_STARTED          = "SESSION_STARTED"
    SESSION_STATE_CHANGED    = "SESSION_STATE_CHANGED"
    SESSION_LOCKED           = "SESSION_LOCKED"

    # --- Post-session ---
    CARDS_GENERATED          = "CARDS_GENERATED"
    CARD_RESONANCE_MARKED    = "CARD_RESONANCE_MARKED"
    PROFILE_REVEAL_VIEWED    = "PROFILE_REVEAL_VIEWED"
    CONSENT_RECORDED         = "CONSENT_RECORDED"
    RECEIPT_PRINTED          = "RECEIPT_PRINTED"
    SESSION_PURGED           = "SESSION_PURGED"


# ─────────────────────────────────────────────────────────────────────────────
# The canonical event record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class InteractionEvent:
    """Immutable, microsecond-timestamped interaction event.

    ``sequence_num`` is monotonically increasing within a session and
    assigned by the EventStore.  Callers must NOT set it directly; the
    constructor default of 0 is a sentinel that the store overwrites.

    ``event_id`` defaults to a new UUIDv4 so callers don't need to
    generate one explicitly.
    """

    session_id:      str
    event_type:      EventType
    provenance_level: ProvenanceLevel
    payload:         dict

    # Assigned by EventStore.append() – sentinel default allows the
    # frozen dataclass to receive the real value via object.__setattr__
    # in the store's append path.
    sequence_num: int = field(default=0, compare=False)

    event_id:    str = field(
        default_factory=lambda: str(uuid.uuid4()),
        compare=False,
    )
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(
            tz=datetime.timezone.utc
        ).isoformat(timespec="microseconds"),
        compare=False,
    )

    # ------------------------------------------------------------------
    # Convenience predicates
    # ------------------------------------------------------------------

    def is_live_parrot_eligible(self) -> bool:
        """True when this event type is permitted in the Parrot context.

        The Parrot may only see events it generated itself (its own
        turns) or the turn-level Navarasa classification for the
        *current* turn.  All other event types are invisible to the
        Parrot (ARCHITECTURE.md §3.4).
        """
        return self.event_type in (
            EventType.PARROT_TURN_GENERATED,
            EventType.NAVARASA_CLASSIFIED,
        )
