"""Session-local Parrot behaviour director state (Pass 1 foundation).

Mutable counters and history for the legacy ``choose_behaviour()`` session
dict. Lives on ``SessionCoordinator`` only; never crosses sessions or enters
engagement / Silent Reader payloads.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class DirectorState:
    """Minimal behaviour-engine session state for one live conversation."""

    understanding_turns: int = 0
    chaos_count: int = 0
    last_behaviour: str | None = None
    behaviour_history: list[str] = field(default_factory=list)

    # Session "temperament". The defaults reproduce the original fixed behaviour exactly;
    # ``randomize_temperament`` gives each live session its own arc so a group of testers
    # cannot learn one shared pattern. Session-local, never crosses sessions.
    trust_turns: int = 3
    instability_base: float = 0.35
    instability_ramp: float = 0.08
    instability_cap: float = 0.75
    instability_jitter: float = 0.0
    early_slip_chance: float = 0.0

    def randomize_temperament(self, rng: random.Random | None = None) -> None:
        """Give this session its own trust-window length and instability curve."""
        roll = rng or random.SystemRandom()
        self.trust_turns = roll.choice((2, 3, 3, 4))
        self.instability_base = roll.uniform(0.25, 0.5)
        self.instability_ramp = roll.uniform(0.03, 0.11)
        self.instability_cap = roll.uniform(0.55, 0.8)
        self.instability_jitter = roll.uniform(0.1, 0.25)
        self.early_slip_chance = roll.uniform(0.0, 0.2)

    def clear(self) -> None:
        self.understanding_turns = 0
        self.chaos_count = 0
        self.last_behaviour = None
        self.behaviour_history.clear()
        # Per-session temperament also returns to the neutral defaults.
        neutral = DirectorState()
        for name in (
            "trust_turns",
            "instability_base",
            "instability_ramp",
            "instability_cap",
            "instability_jitter",
            "early_slip_chance",
        ):
            setattr(self, name, getattr(neutral, name))

    def parrot_session_view(
        self,
        *,
        session_id: str,
        substantive_turns: int,
    ) -> dict:
        """Build the behaviour slice of ``parrot_session`` for one turn."""
        # Floor aligns turn_index with the legacy trust window until the
        # handler syncs engine mutations each turn (Pass 1).
        effective_understanding = max(
            self.understanding_turns,
            min(substantive_turns, self.trust_turns),
        )
        return {
            "session_id": session_id,
            "understanding_turns": effective_understanding,
            "substantive_turns": substantive_turns,
            "chaos_count": self.chaos_count,
            "last_behaviour": self.last_behaviour,
            "behaviour_history": list(self.behaviour_history[-12:]),
        }

    def absorb_parrot_session(self, parrot_session: dict) -> None:
        """Persist in-place mutations from ``choose_behaviour()``."""
        self.understanding_turns = int(
            parrot_session.get("understanding_turns", self.understanding_turns)
        )
        self.chaos_count = int(
            parrot_session.get("chaos_count", self.chaos_count)
        )
        last = parrot_session.get("last_behaviour")
        self.last_behaviour = None if last is None else str(last)
        history = parrot_session.get("behaviour_history")
        if isinstance(history, list):
            self.behaviour_history = [str(item) for item in history[-12:]]
