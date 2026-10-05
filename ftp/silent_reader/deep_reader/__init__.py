"""Phase 4B — Gemini gloss layer over eligible Phase 4A inferences."""

from ftp.silent_reader.deep_reader.adapter import GeminiReaderAdapter, GeminiUnavailable, READER_INSTRUCTION
from ftp.silent_reader.deep_reader.packet import ReaderInput, build_reader_input
from ftp.silent_reader.deep_reader.read import read_session_interpretations

__all__ = (
    "GeminiReaderAdapter",
    "GeminiUnavailable",
    "READER_INSTRUCTION",
    "ReaderInput",
    "build_reader_input",
    "read_session_interpretations",
)
