"""Post-timeline Silent Reader pass (observation only)."""

from __future__ import annotations

import logging
from typing import Any

from ftp.session.coordinator import SessionCoordinator

logger = logging.getLogger(__name__)


def run_silent_reader_pass(
    coordinator: SessionCoordinator | None,
    *,
    user_message: str = "",
    chat_result: dict[str, Any] | None = None,
    composer_telemetry: dict[str, Any] | None = None,
) -> None:
    if coordinator is None:
        return
    try:
        if (
            composer_telemetry
            and user_message.strip()
            and chat_result
            and not chat_result.get("error")
        ):
            turn_index = int(chat_result.get("turn", 0))
            if turn_index <= 0:
                turn_index = max(coordinator.turn_count, 1)
            coordinator.silent_reader.record_turn(
                turn_index=turn_index,
                typing_duration_ms=float(
                    composer_telemetry.get("typing_duration_ms", 0)
                ),
                pause_before_submit_ms=float(
                    composer_telemetry.get("pause_before_submit_ms", 0)
                ),
                message_length=int(
                    composer_telemetry.get(
                        "message_length",
                        len(user_message.strip()),
                    )
                ),
            )
        coordinator.silent_reader.analyze_pending()
    except Exception as exc:
        logger.warning("Silent Reader pass skipped: %s", exc)
