"""Deterministic post-session insight deck for FTP 2.0.

Legacy entry point. Phase 4C composition lives in ``ftp.silent_reader.reading``.
The Parrot never reads from this module or any generated card data.
"""

from __future__ import annotations

from typing import Any

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel
from ftp.silent_reader.reading.compose import DeterministicFallbackAdapter, compose_reading_deck


class PostSessionInterpreter:
    """Deterministic, non-Parrot-visible post-session interpretation layer."""

    def __init__(self, coordinator: Any) -> None:
        self._coordinator = coordinator

    @property
    def coordinator(self) -> Any:
        return self._coordinator

    def generate_deck(self) -> dict:
        """Construct a validated 27-card deck from Phase 4B reader output."""
        return compose_reading_deck(
            self.coordinator,
            adapter=DeterministicFallbackAdapter(),
        )

    def record_cards(self) -> InteractionEvent:
        """Write the deck as a single inferred event on the coordinator."""
        deck = self.generate_deck()
        event = self.coordinator.record(
            EventType.CARDS_GENERATED,
            ProvenanceLevel.INFERRED,
            {
                "session_id": self.coordinator.session_id,
                "card_count": deck["total_cards"],
                "source": deck.get("source", "phase_4c_reading_composer"),
                "cards": deck["cards"],
            },
        )
        return event
