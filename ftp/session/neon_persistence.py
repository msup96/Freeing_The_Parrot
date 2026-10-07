"""Small Neon persistence adapter for FTP2.0 session events.

The adapter is deliberately behind the existing EventStore callback boundary so
unit tests and local runs remain independent of the database.
"""
from __future__ import annotations

import json
import os
from typing import Any

import psycopg

from ftp.events.model import EventType, InteractionEvent, ProvenanceLevel


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

    def record_consent(self, session_id: str, consent_type: str) -> bool:
        """Record consent once; repeated submissions are successful no-ops."""
        consent_key = consent_type.strip().upper()
        with psycopg.connect(self._database_url) as connection:
            cursor = connection.execute(
                """
                INSERT INTO ftp_session_consents (session_id, consent_type, consent_key)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id, consent_key) DO NOTHING
                RETURNING consent_key
                """,
                (session_id, consent_key, consent_key),
            )
            return cursor.fetchone() is not None

    def load_events(self, session_id: str) -> list[dict[str, Any]]:
        with psycopg.connect(self._database_url) as connection:
            rows = connection.execute(
                """
                SELECT sequence_num, event_id, event_type, provenance_level, payload, timestamp
                FROM ftp_session_events
                WHERE session_id = %s
                ORDER BY sequence_num ASC
                """,
                (session_id,),
            ).fetchall()
        return [
            {
                "sequence_num": row[0],
                "event_id": row[1],
                "event_type": row[2],
                "provenance_level": row[3],
                "payload": row[4],
                "timestamp": row[5],
            }
            for row in rows
        ]

    def load_interaction_events(self, session_id: str) -> list[InteractionEvent]:
        """Rebuild immutable events without invoking persistence callbacks."""
        return [
            InteractionEvent(
                session_id=session_id,
                event_type=EventType(row["event_type"]),
                provenance_level=ProvenanceLevel(row["provenance_level"]),
                payload=dict(row["payload"] or {}),
                sequence_num=int(row["sequence_num"]),
                event_id=row["event_id"],
                timestamp=row["timestamp"].isoformat()
                if hasattr(row["timestamp"], "isoformat")
                else str(row["timestamp"]),
            )
            for row in self.load_events(session_id)
        ]

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

