"""FTP 2.0 – Session State Definitions.

Phase 2:
Defines the canonical session states and the legal transition table
drawn from STATE_MACHINE.md.

Design invariants
-----------------
1. The transition table is the *single source of truth* for what
   moves are legal.  SessionStateMachine consults it; it does not
   encode logic itself.
2. AI model outputs (Parrot replies, Gemini cards) are NEVER valid
   transition triggers.  Transitions are driven exclusively by
   deterministic user actions and system guards.
3. The table is expressed as a plain Python dict so it can be
   serialised, diffed, and asserted against in tests.
"""

from __future__ import annotations

import enum


class SessionState(str, enum.Enum):
    """Canonical session states.  Values match the spec identifiers."""
    IDLE_STANDBY               = "IDLE_STANDBY"
    INPUT_INGESTION            = "INPUT_INGESTION"
    LIVE_CONVERSATION          = "LIVE_CONVERSATION"
    BEHAVIORAL_INTERVENTION    = "BEHAVIORAL_INTERVENTION"
    SESSION_CONCLUDED          = "SESSION_CONCLUDED"
    POST_SESSION_INTERPRETATION = "POST_SESSION_INTERPRETATION"
    CARD_SELECTION             = "CARD_SELECTION"
    PROFILE_REVEAL             = "PROFILE_REVEAL"
    DATA_WALL_CONSENT          = "DATA_WALL_CONSENT"
    OUTPUT_GENERATION          = "OUTPUT_GENERATION"
    PURGE_AND_RESET            = "PURGE_AND_RESET"


# ─────────────────────────────────────────────────────────────────────────────
# Legal transition table
# ─────────────────────────────────────────────────────────────────────────────
#
# Maps each source state to the set of target states that are
# explicitly permitted by the spec (STATE_MACHINE.md §4).
#
# Reading: LEGAL_TRANSITIONS[source] = frozenset of legal targets.
#
# Important: LIVE_CONVERSATION → LIVE_CONVERSATION is legal because
# each participant turn stays within that state; only the intervention
# triggers or "I AM DONE!" move it out.
#
# IDLE_STANDBY ← PURGE_AND_RESET is the reset path.
# IDLE_STANDBY ← INPUT_INGESTION (timeout) is also legal.
# ─────────────────────────────────────────────────────────────────────────────

LEGAL_TRANSITIONS: dict[SessionState, frozenset[SessionState]] = {
    SessionState.IDLE_STANDBY: frozenset({
        SessionState.INPUT_INGESTION,
    }),
    SessionState.INPUT_INGESTION: frozenset({
        SessionState.LIVE_CONVERSATION,
        SessionState.IDLE_STANDBY,        # EVT_TIMEOUT_IDLE
    }),
    SessionState.LIVE_CONVERSATION: frozenset({
        SessionState.LIVE_CONVERSATION,   # each participant turn
        SessionState.BEHAVIORAL_INTERVENTION,
        SessionState.SESSION_CONCLUDED,
    }),
    SessionState.BEHAVIORAL_INTERVENTION: frozenset({
        SessionState.SESSION_CONCLUDED,
    }),
    SessionState.SESSION_CONCLUDED: frozenset({
        SessionState.POST_SESSION_INTERPRETATION,
    }),
    SessionState.POST_SESSION_INTERPRETATION: frozenset({
        SessionState.CARD_SELECTION,
    }),
    SessionState.CARD_SELECTION: frozenset({
        SessionState.PROFILE_REVEAL,
    }),
    SessionState.PROFILE_REVEAL: frozenset({
        SessionState.DATA_WALL_CONSENT,
    }),
    SessionState.DATA_WALL_CONSENT: frozenset({
        SessionState.OUTPUT_GENERATION,
    }),
    SessionState.OUTPUT_GENERATION: frozenset({
        SessionState.PURGE_AND_RESET,
    }),
    SessionState.PURGE_AND_RESET: frozenset({
        SessionState.IDLE_STANDBY,
    }),
}
