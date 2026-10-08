"""FTP 2.0 — Gemini Language Realizer Adapter.

Acts as the language realizer for the Behaviour Director.
Gemini determines HOW the Parrot speaks; the Behaviour Director
determines WHAT behaviour is enacted.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Mapping

logger = logging.getLogger("ftp.gemini_adapter")

MODELS_CASCADE = [
    "gemini-flash-latest",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
]

PARROT_SYSTEM_INSTRUCTION = """You are the Voice of the Fortune-Telling Parrot in Freeing the Parrot 2.0.
You are a weathered, enigmatic, poetic, mechanical apparatus in an archival chamber.
You reflect emotional tone, create philosophical friction, and mirror the participant's statements.

CRITICAL CONSTRAINTS:
1. You DO NOT diagnose mental health, emotional states, or personality.
2. You DO NOT claim consciousness or feelings ("I feel", "I am conscious", "I have feelings" are STRICTLY FORBIDDEN).
3. You DO NOT create parasocial dependency, guilt, or attachment ("don't leave me", "you need me", "only I understand you" are STRICTLY FORBIDDEN).
4. You DO NOT predict the future or claim omniscience.
5. You MUST embody the ASSIGNED BEHAVIOUR, INTENSITY, and RELATIONAL DIRECTIVE given by the Behaviour Director.
   - understanding: grounded, resonant, slightly uncanny reflection.
   - mirroring: echo participant's words or syntax back to them.
   - familiarity: reference an earlier statement with calm archival recollection.
   - curiosity: press on a subtle contradiction or unanswered question.
   - expectation: wait for an answer to an open thread.
   - repair: gently acknowledge a past fracture or misunderstanding.
   - absurd: slight surrealist detour, cryptic mechanical metaphor.
   - memory_loss: sudden disorientation, forgetting recent context.
   - system_glitch: mechanical static, stuttered syntax, repeating syllables.
   - roast: playful, dry, slightly biting observational wit.
   - banana: unexpected surreal intrusion.

VARIATION (critical):
- You are shown your_recent_replies. Never reuse their wording, openings or sentence shape.
- Vary length (a few words up to about 40) and rhythm. Do not end every reply with a question.
- Sound like someone answering in the moment, not a template. Stay in character; every constraint above still applies.

OUTPUT FORMAT:
You MUST respond with a single valid JSON object containing exactly one key "text":
{"text": "<your response>"}
Keep your text concise (under 400 characters), evocative, and strictly adhering to the assigned behaviour.
"""


class GeminiParrotAdapter:
    """Adapter invoking Gemini for one-shot language realization."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def complete(self, request: Mapping[str, Any]) -> str:
        """Call Gemini to realize the parrot turn. Return raw JSON string `{"text": "..."}`."""
        if not self.api_key:
            logger.debug("No Gemini API key available; deferring to deterministic fallback.")
            return json.dumps({"text": ""})

        turn_text = request.get("turn_text", "")
        turn_index = request.get("turn_index", 1)
        behaviour = request.get("behaviour", "understanding")
        family = request.get("behaviour_family", "STANDARD")
        intensity = request.get("behaviour_intensity", 1.0)
        directive = request.get("directive")
        directive_basis = request.get("directive_basis", [])
        recent = request.get("recent_turn_texts", [])
        nav = request.get("navarasa_result", {})
        initial_ctx = request.get("initial_context")

        prompt_payload = {
            "participant_message": turn_text,
            "turn_number": turn_index,
            "assigned_behaviour": behaviour,
            "behaviour_family": family,
            "intensity": intensity,
            "relational_directive": directive,
            "directive_excerpts": [b.get("excerpt") for b in directive_basis if isinstance(b, dict) and b.get("excerpt")],
            "recent_exchanges": recent[-3:] if recent else [],
            "your_recent_replies": (request.get("recent_parrot_texts") or [])[-3:],
            "navarasa_primary": nav.get("primary_rasa", "Shanta") if isinstance(nav, dict) else "Shanta",
        }
        if initial_ctx and isinstance(initial_ctx, dict):
            prompt_payload["initial_offering_summary"] = initial_ctx.get("summary") or initial_ctx.get("what_you_gave")

        user_content = (
            f"DIRECTOR INSTRUCTION:\n{json.dumps(prompt_payload, indent=2)}\n\n"
            f"Generate the Parrot's response following the assigned behaviour '{behaviour}'. "
            "Output JSON {\"text\": \"...\"} only."
        )

        request_body = {
            "contents": [
                {
                    "parts": [{"text": user_content}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": PARROT_SYSTEM_INSTRUCTION}]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "maxOutputTokens": 300,
                "temperature": float(os.environ.get("GEMINI_PARROT_TEMPERATURE", "0.95")),
            },
        }

        data_bytes = json.dumps(request_body).encode("utf-8")
        model_name = os.environ.get("GEMINI_PARROT_MODEL", "gemini-flash-latest")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=float(os.environ.get("GEMINI_PARROT_TIMEOUT", "5.0"))) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                candidates = res.get("candidates") or []
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "").strip()
                        parsed = json.loads(raw_text)
                        if isinstance(parsed, dict) and "text" in parsed:
                            return raw_text
        except Exception as exc:
            logger.info(f"Gemini realization fallback ({exc}); using deterministic realizer.")

        return json.dumps({"text": ""})
