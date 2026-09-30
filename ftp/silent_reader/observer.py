"""FTP 2.0 – Silent Reader observation layer.

Phase 3A:
Passive telemetry capture during LIVE_CONVERSATION.  All writes go
through SessionCoordinator.record(); this module never touches EventStore.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ftp.events.model import InteractionEvent
from ftp.silent_reader.analyzer import TimelineAnalyzer
from ftp.silent_reader.features import build_composer_telemetry_payload

if TYPE_CHECKING:
    from ftp.session.coordinator import SessionCoordinator


def build_telemetry_payload(
    turn_index: int,
    typing_duration_ms: float,
    pause_before_submit_ms: float,
    message_length: int,
) -> dict:
    """Build a TELEMETRY_RECORDED payload (Phase 3A composer signals)."""
    return build_composer_telemetry_payload(
        turn_index,
        typing_duration_ms,
        pause_before_submit_ms,
        message_length,
    )


class SilentReaderObserver:
    """Records interaction telemetry without influencing the Parrot."""

    def __init__(self, coordinator: SessionCoordinator) -> None:
        self._coordinator = coordinator
        self._analyzer = TimelineAnalyzer(coordinator)

    def record_turn(
        self,
        *,
        turn_index: int,
        typing_duration_ms: float,
        pause_before_submit_ms: float,
        message_length: int,
    ):
        """Append one TELEMETRY_RECORDED composer event via the coordinator."""
        return self._coordinator.record_silent_reader_observation(
            build_composer_telemetry_payload(
                turn_index,
                typing_duration_ms,
                pause_before_submit_ms,
                message_length,
            )
        )

    def analyze_pending(self) -> list[InteractionEvent]:
        """Derive OBSERVED features from new timeline events."""
        return self._analyzer.analyze_pending()
