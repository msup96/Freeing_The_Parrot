"""Small Neon persistence adapter for FTP2.0 session events.

The adapter is deliberately behind the existing EventStore callback boundary so
unit tests and local runs remain independent of the database.
"""
from __future__ import annotations

import json
import os
from typing import Any

import psycopg

from ftp.events.model import InteractionEvent


class NeonSessionPersistence:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or os.environ.get("DATABASE_URL")
        if not self._database_url:
            raise RuntimeError("DATABASE_URL is required for Neon persistence")

    def create_session(self, session_id: str, expires_at: str) -> None:
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO ftp_sessions (session_id, expires_at)
                VALUES (%s, %s)
                ON CONFLICT (session_id) DO NOTHING
                """,
                (session_id, expires_at),
            )

    def append_event(self, event: InteractionEvent) -> None:
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO ftp_session_events
                    (session_id, sequence_num, event_id, event_type,
                     provenance_level, payload, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (session_id, event_id) DO NOTHING
                """,
                (
                    event.session_id,
                    event.sequence_num,
                    event.event_id,
                    event.event_type.value,
                    event.provenance_level.value,
                    json.dumps(event.payload),
                    event.timestamp,
                ),
            )

    def update_session_state(self, session_id: str, state: dict[str, Any]) -> None:
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                "UPDATE ftp_sessions SET state = %s::jsonb WHERE session_id = %s",
                (json.dumps(state), session_id),
            )


def build_neon_persistence() -> NeonSessionPersistence | None:
    """Return persistence only when explicitly enabled.

    This preserves local/test behavior and avoids making a database call for
    deployments that have not opted into durable FTP sessions yet.
    """
    if os.environ.get("FTP_DURABLE_SESSIONS", "0") != "1":
        return None
    return NeonSessionPersistence()

