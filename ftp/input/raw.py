"""FTP 2.0 — RAW multimodal ingest helpers (no OCR/ASR)."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_raw_ingest_payload(
    modality: str,
    source_channel: str,
    *,
    byte_size: int,
    content_sha256: str,
    storage_ref: str,
    media_format: str | None = None,
    duration_ms: int | None = None,
) -> dict:
    """Build INPUT_RAW_INGESTED payload (metadata only; bytes on disk)."""
    payload: dict = {
        "modality": modality,
        "source_channel": source_channel,
        "byte_size": byte_size,
        "sha256": content_sha256,
        "storage_ref": storage_ref,
        "ingest_id": str(uuid.uuid4()),
    }
    if media_format is not None:
        payload["media_format"] = media_format
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    return payload


def save_session_media(
    base_dir: Path,
    session_id: str,
    extension: str,
    data: bytes,
) -> tuple[Path, str]:
    """Write bytes under base_dir/session_id/; return path and storage_ref string."""
    session_dir = base_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{extension}"
    path = session_dir / name
    path.write_bytes(data)
    return path, str(path)
