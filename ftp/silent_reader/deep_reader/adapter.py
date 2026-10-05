"""Production Gemini adapter. Only this module may import the Gemini SDK."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from ftp.silent_reader.deep_reader.packet import assert_narrow_reader_input

READER_INSTRUCTION = (
    "For each inference, write one sentence grounded in that claim. "
    "Use only words allowed for that inference_id. "
    "Echo cited_evidence_ids exactly. "
    "Add no measurement, trait, cause, or evidence id."
)

GEMINI_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "interpretations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "inference_id": {"type": "string"},
                    "cited_evidence_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "text": {"type": "string"},
                },
                "required": ["inference_id", "cited_evidence_ids", "text"],
            },
        },
    },
    "required": ["interpretations"],
}


class GeminiUnavailable(Exception):
    """Gemini could not be called or returned no usable body."""


class ReaderAdapter(Protocol):
    def complete(self, reader_input: dict[str, Any]) -> str:
        """Return raw JSON text from the model."""


class GeminiReaderAdapter:
    """One-shot structured Gemini call for session glosses."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        timeout_ms: int = 8000,
    ) -> None:
        self._model = (model or os.environ.get("FTP_DEEP_READER_MODEL", "")).strip()
        api_key = api_key or os.environ.get("FTP_DEEP_READER_API_KEY", "")
        api_key = api_key.strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
        self._api_key = api_key
        self._timeout_ms = timeout_ms

    def complete(self, reader_input: dict[str, Any]) -> str:
        assert_narrow_reader_input(reader_input)
        if not reader_input.get("packet_consistent", True):
            raise GeminiUnavailable("reader input is inconsistent")
        if not self._model or not self._api_key:
            raise GeminiUnavailable("FTP_DEEP_READER_MODEL or API key is not configured")

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise GeminiUnavailable("google-genai SDK is not installed") from exc

        client = genai.Client(api_key=self._api_key)
        payload = {
            "session_id": reader_input["session_id"],
            "instruction": READER_INSTRUCTION,
            "evidence_items": reader_input["evidence_items"],
            "inferences": reader_input["inferences"],
        }
        try:
            response = client.models.generate_content(
                model=self._model,
                contents=json.dumps(payload, ensure_ascii=True),
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=GEMINI_OUTPUT_SCHEMA,
                    http_options=types.HttpOptions(timeout=self._timeout_ms),
                ),
            )
        except Exception as exc:
            raise GeminiUnavailable(str(exc)) from exc

        text = getattr(response, "text", None) or ""
        if not text.strip():
            raise GeminiUnavailable("empty Gemini response")
        return text
