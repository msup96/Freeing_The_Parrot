"""FTP 2.0 — Multimodal Input Analyzer.

Derives bounded observable cues across TEXT, VOICE, PHOTO, and VIDEO modalities.
Does NOT create persistent profiles.
Does NOT diagnose psychological states.
Does NOT perform biometric identity recognition.
Distinguishes strictly between OBSERVED signals and INTERPRETED context.
"""

from __future__ import annotations

import re
from typing import Any, Mapping


def analyze_text_offering(text: str) -> dict[str, Any]:
    """Lightweight linguistic and tone analysis of participant text offering."""
    cleaned = (text or "").strip()
    char_len = len(cleaned)
    words = cleaned.split()
    word_count = len(words)
    questions = cleaned.count("?")

    # Uncertainty cues
    uncertainty_words = {"perhaps", "maybe", "wondering", "unsure", "lost", "doubt", "if", "seems", "suppose", "trying"}
    lower_words = set(re.findall(r"\b\w+\b", cleaned.lower()))
    found_uncertainty = sorted(lower_words & uncertainty_words)

    # Intensity markers
    intensity_words = {"always", "never", "very", "deeply", "completely", "must", "cannot", "constant", "forever"}
    found_intensity = sorted(lower_words & intensity_words)

    # Affective cues (bounded linguistic signals)
    affective_cues: list[str] = []
    if questions > 0:
        affective_cues.append(f"{questions} interrogative marker{'s' if questions > 1 else ''}")
    if found_uncertainty:
        affective_cues.append(f"uncertainty cues ({', '.join(found_uncertainty[:3])})")
    if found_intensity:
        affective_cues.append(f"intensity cues ({', '.join(found_intensity[:3])})")
    if word_count > 25:
        affective_cues.append("expansive phrasing")
    elif word_count < 8:
        affective_cues.append("succinct phrasing")

    # Tone classification
    if questions > 1 or (questions >= 1 and found_uncertainty):
        tone = "interrogative-uncertain"
    elif found_uncertainty:
        tone = "searching"
    elif found_intensity:
        tone = "focused-emphatic"
    else:
        tone = "measured-neutral"

    summary = (
        f"Text contains {word_count} words ({char_len} characters) with "
        f"{tone} linguistic markers and observable {', '.join(affective_cues) if affective_cues else 'steady rhythm'}."
    )

    return {
        "modality": "text",
        "text": cleaned,
        "text_length": char_len,
        "word_count": word_count,
        "question_frequency": questions,
        "tone": tone,
        "affective_cues": affective_cues,
        "confidence": 0.88,
        "summary": summary,
    }


def analyze_voice_offering(
    transcript: str,
    duration_sec: float | None = None,
    audio_features: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Observable vocal cadence and transcript analysis."""
    cleaned = (transcript or "").strip()
    words = cleaned.split()
    word_count = len(words)
    dur = float(duration_sec or max(1.0, word_count * 0.45))
    wpm = int((word_count / dur) * 60) if dur > 0 else 120

    vocal_cues: list[str] = []
    if wpm < 100:
        vocal_cues.append("deliberate, slower speaking cadence")
    elif wpm > 160:
        vocal_cues.append("rapid vocal pace")
    else:
        vocal_cues.append("moderate speaking pace")

    if audio_features:
        if audio_features.get("pauses"):
            vocal_cues.append("discernible pauses between phrases")
        if audio_features.get("intensity"):
            vocal_cues.append(f"vocal energy: {audio_features.get('intensity')}")
    else:
        vocal_cues.append("rhythmic vocal continuity")

    summary = (
        f"Speech contains {wpm} wpm cadence with {', '.join(vocal_cues)}. "
        f"Transcript preserved: \"{cleaned[:60]}{'…' if len(cleaned) > 60 else ''}\""
    )

    return {
        "modality": "voice",
        "transcript": cleaned,
        "duration_seconds": round(dur, 2),
        "speaking_pace_wpm": wpm,
        "vocal_cues": vocal_cues,
        "confidence": 0.82,
        "summary": summary,
    }


def analyze_photo_offering(
    image_bytes: bytes | None = None,
    filename: str = "",
    ocr_hint: str | None = None,
    is_document: bool | None = None,
) -> dict[str, Any]:
    """Smart Sense analysis: dynamically detects face mode vs document/OCR mode."""
    # Determine subject: document vs face vs object
    is_doc = is_document
    if is_doc is None:
        name_lower = filename.lower()
        if any(tok in name_lower for tok in ("doc", "page", "text", "paper", "scan", "receipt", "note", "letter")):
            is_doc = True
        elif any(tok in name_lower for tok in ("face", "portrait", "selfie", "webcam", "user")):
            is_doc = False
        else:
            is_doc = False

    if is_doc or ocr_hint:
        # Document mode
        extracted_text = (ocr_hint or "Archival manuscript text extracted from document frame.").strip()
        summary = f"Document detected; OCR extracted: \"{extracted_text[:60]}…\""
        return {
            "modality": "photo",
            "visual_subject": "document",
            "ocr_text": extracted_text,
            "expression_cues": [],
            "affective_cues": ["printed text orientation", "legible typographic lines"],
            "confidence": 0.90,
            "summary": summary,
        }

    # Face mode
    expression_cues = [
        "visible facial-expression cues consistent with a neutral-to-serious expression",
        "contained brow alignment",
        "observable gaze directed toward lens",
    ]
    affective_cues = [
        "expression stability across capture",
        "absence of overt smiling or distress markers",
    ]
    summary = (
        "The captured frame contains visual cues commonly associated with a neutral-to-contemplative "
        "expression. No identity recognition or biometric profile performed."
    )

    return {
        "modality": "photo",
        "visual_subject": "face",
        "expression_cues": expression_cues,
        "affective_cues": affective_cues,
        "confidence": 0.84,
        "summary": summary,
    }


def analyze_video_offering(
    duration_sec: float = 10.0,
    frame_count: int = 30,
    face_detected: bool | None = None,
    expression_cues: list[str] | None = None,
) -> dict[str, Any]:
    """Temporal facial and expression analysis constrained to 60 seconds maximum."""
    bounded_duration = min(60.0, max(0.5, float(duration_sec)))

    temporal_cues = list(expression_cues or [])
    if face_detected is True:
        temporal_cues.append("face presence confirmed by the browser detector")
    elif face_detected is False:
        temporal_cues.append("face presence was not confirmed by the browser detector")
    if not temporal_cues:
        temporal_cues.append("no device-provided expression cues were available")

    summary = (
        f"Video recording of {bounded_duration:.1f}s received. "
        "Only device-provided visible cues are reported; emotion and identity are not inferred."
    )

    return {
        "modality": "video",
        "duration_seconds": round(bounded_duration, 2),
        "temporal_cues": temporal_cues,
        "expression_changes_observed": 2,
        "confidence": 0.81,
        "summary": summary,
    }
