"""FTP 2.0 — observational chat timeline wiring (no Parrot behaviour changes)."""

from __future__ import annotations

import logging
from typing import Any

from ftp.input.raw import build_raw_ingest_payload, sha256_bytes
from ftp.session.coordinator import SessionCoordinator, SessionLockedError

logger = logging.getLogger(__name__)

TEXT_CANONICAL_STORAGE_REF = "canonical:PARROT_TURN_GENERATED"


def build_text_raw_ingest_payload(text: str) -> dict:
    """RAW TEXT ingest: hash + length; full text lives on PARROT_TURN_GENERATED."""
    encoded = text.encode("utf-8")
    payload = build_raw_ingest_payload(
        "TEXT",
        "WEB_COMPOSER",
        byte_size=len(encoded),
        content_sha256=sha256_bytes(encoded),
        storage_ref=TEXT_CANONICAL_STORAGE_REF,
        media_format="UTF-8",
    )
    payload["character_count"] = len(text)
    return payload


def record_chat_timeline_events(
    coordinator: SessionCoordinator | None,
    user_message: str,
    chat_result: dict[str, Any],
) -> None:
    """Append RAW text + Parrot turn to the coordinator store if possible.

    Failures are logged and swallowed so the live Parrot path is unaffected.
    """
    if coordinator is None:
        return
    if chat_result.get("error"):
        return

    text = (user_message or "").strip()
    if not text:
        return

    response = chat_result.get("response")
    if not response:
        return

    gate_state = chat_result.get("gate") or {}
    gate_name = ""
    if isinstance(gate_state, dict):
        gate_name = str(gate_state.get("gate") or "")

    turn_index = int(chat_result.get("turn", 0))

    try:
        coordinator.record_raw_input(build_text_raw_ingest_payload(text))

        if turn_index == 0:
            coordinator.record_observed_parrot_turn(
                turn_index=turn_index,
                turn_text=text,
                reply=response,
                gate=gate_name,
            )
        else:
            coordinator.record_parrot_turn(
                turn_text=text,
                reply=response,
                gate=gate_name,
            )

        if chat_result.get("closed"):
            if not coordinator.machine.is_locked():
                coordinator.lock()
    except (SessionLockedError, ValueError) as exc:
        logger.warning("FTP2 timeline recording skipped: %s", exc)
    except Exception as exc:
        logger.warning("FTP2 timeline recording failed: %s", exc)
