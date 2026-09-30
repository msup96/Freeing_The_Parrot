"""Runtime paths and ports for local dev and cloud deployment."""

from __future__ import annotations

import os
from pathlib import Path

# Preserves existing Windows installation layout when DATA_DIR is unset.
DEFAULT_DATA_DIR = r"C:\freeing_the_parrot"

WINDOWS_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def get_data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", DEFAULT_DATA_DIR))


def get_port() -> int:
    return int(os.environ.get("PORT", "5000"))


def resolve_tesseract_cmd() -> str | None:
    """Executable path for Tesseract, or None to use PATH."""
    explicit = os.environ.get("TESSERACT_CMD", "").strip()
    if explicit:
        return explicit
    if os.path.exists(WINDOWS_TESSERACT_PATH):
        return WINDOWS_TESSERACT_PATH
    return None
