-- FTP 2.0 durable session persistence schema.
-- Apply to a dedicated Neon database before enabling FTP_DURABLE_SESSIONS.
-- Expired/reset sessions are removed from ftp_sessions; FK cascades remove
-- associated events and consent records.
BEGIN;

CREATE TABLE IF NOT EXISTS public.ftp_sessions (
    session_id TEXT PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL,
    offerings JSONB,
    multimodal_context JSONB,
    decks JSONB,
    selected JSONB,
    reveals JSONB,
    state JSONB
);

CREATE TABLE IF NOT EXISTS public.ftp_session_events (
    session_id TEXT NOT NULL REFERENCES public.ftp_sessions(session_id) ON DELETE CASCADE,
    sequence_num INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    provenance_level TEXT NOT NULL,
    payload JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    UNIQUE (session_id, event_id),
    UNIQUE (session_id, sequence_num)
);

CREATE INDEX IF NOT EXISTS idx_ftp_session_events_timestamp
    ON public.ftp_session_events (timestamp);

CREATE TABLE IF NOT EXISTS public.ftp_session_consents (
    session_id TEXT NOT NULL REFERENCES public.ftp_sessions(session_id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL,
    consent_key TEXT NOT NULL,
    UNIQUE (session_id, consent_key)
);

COMMIT;
