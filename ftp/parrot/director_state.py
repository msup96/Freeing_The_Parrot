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

    # Hidden relationship state used only by the Behaviour Director. These
    # values are derived from live interactional signals; they never enter
    # Parrot context or participant-facing output.
    engagement_momentum: float = 0.0
    trust_score: float = 0.0
    irritation: float = 0.0
    suspicion: float = 0.0
    tolerated_ruptures: int = 0
    risk_level: float = 0.0

    def randomize_temperament(self, rng: random.Random | None = None) -> None:
        """Give this session its own trust-window length and instability curve."""
        roll = rng or random.SystemRandom()
        self.trust_turns = roll.choice((2, 3, 3, 4))
        self.instability_base = roll.uniform(0.14, 0.26)
        self.instability_ramp = roll.uniform(0.02, 0.055)
        self.instability_cap = roll.uniform(0.42, 0.58)
        self.instability_jitter = roll.uniform(0.04, 0.12)
        self.early_slip_chance = roll.uniform(0.0, 0.08)

    def observe_relationship(self, signals: dict, *, turn_index: int) -> None:
        """Update the hidden relationship state from one live interaction."""
        clamp = lambda value: max(0.0, min(1.0, float(value)))

        delta = float(signals.get("engagement_delta") or 0.0)
        trust_delta = float(signals.get("trust_delta") or 0.0)
        disengagement = bool(signals.get("disengagement"))
        irritation = bool(signals.get("irritation"))
        continued = bool(signals.get("continued_after_fracture"))

        if disengagement:
            self.engagement_momentum = clamp(self.engagement_momentum * 0.55 + delta)
            self.trust_score = clamp(self.trust_score * 0.72 + trust_delta)
            self.risk_level = clamp(self.risk_level * 0.55)
        else:
            self.engagement_momentum = clamp(self.engagement_momentum + delta)
            self.trust_score = clamp(self.trust_score + trust_delta)

        if irritation and not disengagement:
            self.irritation = clamp(self.irritation + 0.12)
        else:
            self.irritation = clamp(self.irritation * 0.94)

        if continued:
            self.tolerated_ruptures += 1
            self.suspicion = clamp(self.suspicion + 0.10)

        # Suspicion grows when the participant notices oddness, but never
        # becomes a reason to force another oddity.
        if bool(signals.get("parrot_directed")) and bool(signals.get("previous_fracture")):
            self.suspicion = clamp(self.suspicion + 0.08)

        # Risk is a consequence of trust that has survived disruption.
        rupture_bonus = min(0.30, self.tolerated_ruptures * 0.075)
        irritation_bonus = min(0.15, self.irritation * 0.20)
        self.risk_level = clamp(
            max(self.risk_level, (self.trust_score * 0.70) + rupture_bonus + irritation_bonus)
        )
        self.last_risk_turn = turn_index

    def glitch_probability(self) -> float:
        """Probability that an eligible turn may contain one behavioural risk."""
        if self.trust_score < 0.62:
            return 0.0
        pressure = max(0.0, self.trust_score - 0.62)
        probability = 0.06 + (pressure * 1.10)
        probability += min(0.18, self.tolerated_ruptures * 0.045)
        probability += min(0.10, self.irritation * 0.10)
        return max(0.0, min(0.68, probability))

    def glitch_intensity(self) -> str:
        """Translate relationship pressure into a bounded behavioural band."""
        if self.trust_score >= 0.90 and (
            self.tolerated_ruptures >= 2 or self.irritation >= 0.25
        ):
            return "high"
        if self.trust_score >= 0.78 or self.tolerated_ruptures >= 1:
            return "moderate"
        return "low"

    def clear(self) -> None:
        self.understanding_turns = 0
        self.chaos_count = 0
        self.last_behaviour = None
        self.behaviour_history.clear()
        # Per-session temperament and relationship state return to neutral.
        self.engagement_momentum = 0.0
        self.trust_score = 0.0
        self.irritation = 0.0
        self.suspicion = 0.0
        self.tolerated_ruptures = 0
        self.risk_level = 0.0
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
