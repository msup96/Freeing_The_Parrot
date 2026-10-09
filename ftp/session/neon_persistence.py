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

    def purge_expired_sessions(self) -> list[str]:
        """Delete expired durable sessions and cascade their child records."""
        with psycopg.connect(self._database_url) as connection:
            rows = connection.execute(
                """
                DELETE FROM ftp_sessions
                WHERE expires_at <= CURRENT_TIMESTAMP
                RETURNING session_id
                """
            ).fetchall()
        return [str(row[0]) for row in rows]

    def delete_session(self, session_id: str) -> bool:
        """Delete one durable session; child records are removed by FK cascade."""
        with psycopg.connect(self._database_url) as connection:
            cursor = connection.execute(
                "DELETE FROM ftp_sessions WHERE session_id = %s RETURNING session_id",
                (session_id,),
            )
            return cursor.fetchone() is not None

    def persist_approved_archive(
        self,
        session_id: str,
        expires_at: str,
        events: list[InteractionEvent],
        artifacts: dict[str, Any],
        consent_type: str = "SHARE",
    ) -> None:
        """Atomically archive a session only after explicit participant consent."""
        normalized_type = consent_type.strip().upper()
        if normalized_type not in {"SHARE", "MEMORY_CHEST"}:
            raise ValueError("Only an explicit SHARE consent can create an archive")

        artifact_columns = {
            "offerings": artifacts.get("offerings"),
            "multimodal_context": artifacts.get("multimodal_context"),
            "decks": artifacts.get("decks"),
            "selected": artifacts.get("selected"),
            "reveals": artifacts.get("reveals"),
            "state": artifacts.get("state"),
        }
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO ftp_sessions
                    (session_id, expires_at, offerings, multimodal_context,
                     decks, selected, reveals, state)
                VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb,
                        %s::jsonb, %s::jsonb, %s::jsonb)
                ON CONFLICT (session_id) DO UPDATE SET
                    expires_at = EXCLUDED.expires_at,
                    offerings = EXCLUDED.offerings,
                    multimodal_context = EXCLUDED.multimodal_context,
                    decks = EXCLUDED.decks,
                    selected = EXCLUDED.selected,
                    reveals = EXCLUDED.reveals,
                    state = EXCLUDED.state
                """,
                (
                    session_id,
                    expires_at,
                    json.dumps(artifact_columns["offerings"]),
                    json.dumps(artifact_columns["multimodal_context"]),
                    json.dumps(artifact_columns["decks"]),
                    json.dumps(artifact_columns["selected"]),
                    json.dumps(artifact_columns["reveals"]),
                    json.dumps(artifact_columns["state"]),
                ),
            )
            # Archive only the provenance needed to interpret the Data Showdown.
            # Raw turn transcripts, original multimodal inputs, and OCR/ASR payloads
            # are deliberately excluded from the durable event archive.
            archive_event_types = {
                EventType.SESSION_STARTED,
                EventType.SESSION_STATE_CHANGED,
                EventType.SESSION_LOCKED,
                EventType.TELEMETRY_RECORDED,
                EventType.NAVARASA_CLASSIFIED,
                EventType.CARDS_GENERATED,
                EventType.CARD_RESONANCE_MARKED,
                EventType.PROFILE_REVEAL_VIEWED,
                EventType.CONSENT_RECORDED,
                EventType.RECEIPT_PRINTED,
            }
            for event in events:
                if event.event_type not in archive_event_types:
                    continue
                connection.execute(
                    """
                    INSERT INTO ftp_session_events
                        (session_id, sequence_num, event_id, event_type,
                         provenance_level, payload, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT DO NOTHING
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
            connection.execute(
                """
                INSERT INTO ftp_session_consents (session_id, consent_type, consent_key)
                VALUES (%s, %s, 'FINALIZE:SHARE')
                ON CONFLICT (session_id, consent_key) DO NOTHING
                """,
                (session_id, normalized_type),
            )

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
        """Persist only approved provenance events, never raw dialogue/input."""
        archive_event_types = {
            EventType.SESSION_STARTED,
            EventType.SESSION_STATE_CHANGED,
            EventType.SESSION_LOCKED,
            EventType.TELEMETRY_RECORDED,
            EventType.NAVARASA_CLASSIFIED,
            EventType.CARDS_GENERATED,
            EventType.CARD_RESONANCE_MARKED,
            EventType.PROFILE_REVEAL_VIEWED,
            EventType.CONSENT_RECORDED,
            EventType.RECEIPT_PRINTED,
        }
        if event.event_type not in archive_event_types:
            return
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

    def record_consent(self, session_id: str, consent_type: str, *, finalization: bool = False) -> bool:
        """Atomically claim a consent/finalization operation exactly once."""
        normalized_type = consent_type.strip().upper()
        consent_key = f"FINALIZE:{normalized_type}" if finalization else normalized_type
        with psycopg.connect(self._database_url) as connection:
            cursor = connection.execute(
                """
                INSERT INTO ftp_session_consents (session_id, consent_type, consent_key)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id, consent_key) DO NOTHING
                RETURNING consent_key
                """,
                (session_id, normalized_type, consent_key),
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

    def update_artifact(self, session_id: str, artifact: str, value: Any) -> None:
        allowed = {"offerings", "multimodal_context", "decks", "selected", "reveals"}
        if artifact not in allowed:
            raise ValueError(f"Unsupported FTP session artifact: {artifact}")
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                f"UPDATE ftp_sessions SET {artifact} = %s::jsonb WHERE session_id = %s",
                (json.dumps(value), session_id),
            )

    def load_artifacts(self, session_id: str) -> dict[str, Any] | None:
        with psycopg.connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT offerings, multimodal_context, decks, selected, reveals
                FROM ftp_sessions WHERE session_id = %s
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return dict(zip(("offerings", "multimodal_context", "decks", "selected", "reveals"), row))

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

