"""
FREEING THE PARROT
OCR SEMANTIC CORRECTOR

Purpose:
    Clean OCR output before it reaches the Navarasa engine.

Design principles:
    1. Be conservative.
    2. Never blindly replace normal English words.
    3. Prefer phrase/context correction over isolated correction.
    4. Preserve already-correct emotional words.
    5. Produce an audit trail of every correction.
    6. Use only standard Python libraries.

This module does NOT perform emotional analysis.
That remains the responsibility of navarasa_engine.py.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple


# ============================================================
# CONFIGURATION
# ============================================================

# Words that are important enough that we should protect them
# from accidental OCR "correction".
#
# This is intentionally small.
# The Navarasa engine remains the authority on emotion words.
PROTECTED_WORDS = {
    "love",
    "beautiful",
    "wonder",
    "amazed",
    "amazing",
    "incredible",
    "terrified",
    "fear",
    "furious",
    "frustrated",
    "angry",
    "alone",
    "heartbroken",
    "determined",
    "calm",
    "peace",
    "laugh",
    "laughing",
    "joke",
    "disgusting",
}


# ============================================================
# 1. HIGH-CONFIDENCE OCR REPLACEMENTS
# ============================================================
#
# These are deliberately conservative.
#
# They are not "emotion corrections".
# They are OCR corrections.
#
# Example:
#     "meekn" -> "meeting"
#
# Only apply when the malformed form is actually present.

EXACT_REPLACEMENTS: Dict[str, str] = {

    # Common OCR corruption observed in the project
    "meekn": "meeting",
    "meekng": "meeting",
    "meetng": "meeting",

    "Yew people": "new people",
    "yew people": "new people",
    "Nevo people": "new people",
    "Nevo": "new",
    "Nrevo": "new",

    "wo od er": "wonder",
    "wo od er": "wonder",
    "yonder at": "wonder at",

    "albout": "about",
    "Shout": "about",

    # Common corruption seen in the supplied handwriting
    "absolutelu": "absolutely",
    "absolute": "absolutely",
    "ly love": "love",

    # OCR punctuation substitutions
    "\\ absolute": "absolutely",
    "+o": "to",

    # Very obvious fragments
    "v LI travel": "when I travel",
    "LI travel": "I travel",
}


# ============================================================
# 2. PHRASE-LEVEL RECONSTRUCTION
# ============================================================
#
# Phrase corrections happen BEFORE individual-word correction.
#
# This is important because:
#
#     "Yew people"
#
# gives us much more information than:
#
#     "Yew"
#
# by itself.
#
# Context wins.

PHRASE_CORRECTIONS: List[Tuple[str, str]] = [

    # Exact phrases seen in OCR output
    (r"\bYew\s+people\b", "new people"),
    (r"\byew\s+people\b", "new people"),
    (r"\bNevo\s+people\b", "new people"),
    (r"\bNrevo\s+people\b", "new people"),

    # Broken "wonder"
    (r"\bwo\s+od\s+er\b", "wonder"),
    (r"\bwo\s+od\s+er\s+at\b", "wonder at"),
    (r"\byonder\s+at\b", "wonder at"),

    # Broken "meeting"
    (r"\blove\s+meekn\b", "love meeting"),
    (r"\blove\s+meekng\b", "love meeting"),
    (r"\blove\s+meetng\b", "love meeting"),

    # Broken "about"
    (r"\bstories\s+Shout\b", "stories about"),
    (r"\bstories\s+albout\b", "stories about"),

    # Broken sentence ending seen repeatedly
    (r"\bvnen\s+LI\s+travel\b", "when I travel"),
    (r"\bv\s+LI\s+travel\b", "when I travel"),
]


# ============================================================
# 3. CONSERVATIVE FUZZY CORRECTION DICTIONARY
# ============================================================
#
# IMPORTANT:
#
# We do NOT fuzzy-match against the entire English dictionary.
#
# Doing that would be dangerous.
#
# Instead, this list contains only words that have repeatedly
# appeared as OCR failures in this project.
#
# This prevents:
#
#     generic word -> random dictionary word
#
# from happening.

FUZZY_CANDIDATES = {
    "meeting",
    "beautiful",
    "absolutely",
    "travel",
    "people",
    "places",
    "wonder",
    "stories",
    "about",
    "learn",
    "when",
}


# Minimum similarity required for an isolated fuzzy correction.
FUZZY_THRESHOLD = 0.86


# ============================================================
# 4. TOKENIZATION
# ============================================================

TOKEN_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+|[^\w\s]")


def tokenize(text: str) -> List[str]:
    """
    Tokenize text while preserving punctuation.
    """
    return TOKEN_PATTERN.findall(text)


# ============================================================
# 5. NORMALIZATION
# ============================================================

def normalize_whitespace(text: str) -> str:
    """
    Normalize repeated whitespace without destroying line meaning.
    """
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ============================================================
# 6. PHRASE CORRECTION
# ============================================================

def apply_phrase_corrections(
    text: str,
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Apply high-confidence phrase-level OCR corrections.

    Returns:
        corrected_text
        correction_log
    """

    correction_log: List[Dict[str, str]] = []

    corrected = text

    for pattern, replacement in PHRASE_CORRECTIONS:
        new_text, count = re.subn(
            pattern,
            replacement,
            corrected,
            flags=re.IGNORECASE,
        )

        if count > 0:
            correction_log.append(
                {
                    "type": "phrase",
                    "original_pattern": pattern,
                    "replacement": replacement,
                    "occurrences": str(count),
                }
            )

            corrected = new_text

    return corrected, correction_log


# ============================================================
# 7. EXACT OCR CORRECTION
# ============================================================

def apply_exact_replacements(
    text: str,
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Apply exact high-confidence OCR replacements.
    """

    correction_log: List[Dict[str, str]] = []

    corrected = text

    # Longer replacements first.
    replacements = sorted(
        EXACT_REPLACEMENTS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for original, replacement in replacements:

        if original not in corrected:
            continue

        count = corrected.count(original)

        corrected = corrected.replace(
            original,
            replacement,
        )

        correction_log.append(
            {
                "type": "exact",
                "original": original,
                "replacement": replacement,
                "occurrences": str(count),
            }
        )

    return corrected, correction_log


# ============================================================
# 8. FUZZY MATCHING
# ============================================================

def similarity(a: str, b: str) -> float:
    """
    Return normalized string similarity.
    """

    return SequenceMatcher(
        None,
        a.lower(),
        b.lower(),
    ).ratio()


def best_fuzzy_candidate(
    token: str,
) -> Tuple[str | None, float]:
    """
    Find the strongest candidate from our LIMITED OCR candidate
    vocabulary.

    This is intentionally not a general English spellchecker.
    """

    token_lower = token.lower()

    if len(token_lower) < 4:
        return None, 0.0

    best_word = None
    best_score = 0.0

    for candidate in FUZZY_CANDIDATES:

        score = similarity(
            token_lower,
            candidate,
        )

        if score > best_score:
            best_score = score
            best_word = candidate

    if best_score >= FUZZY_THRESHOLD:
        return best_word, best_score

    return None, best_score


# ============================================================
# 9. SAFE FUZZY CORRECTION
# ============================================================

def apply_safe_fuzzy_corrections(
    text: str,
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Correct only highly likely OCR mistakes.

    Rules:
        - never modify protected emotional words
        - never modify very short words
        - only use our restricted candidate vocabulary
        - require high similarity
        - do not modify a word if it is already a valid candidate
    """

    tokens = tokenize(text)

    correction_log: List[Dict[str, str]] = []

    corrected_tokens: List[str] = []

    for token in tokens:

        lower = token.lower()

        # Preserve punctuation.
        if not re.fullmatch(r"[A-Za-z]+(?:'[A-Za-z]+)?", token):
            corrected_tokens.append(token)
            continue

        # Preserve known emotional words.
        if lower in PROTECTED_WORDS:
            corrected_tokens.append(token)
            continue

        # Preserve already-valid candidates.
        if lower in FUZZY_CANDIDATES:
            corrected_tokens.append(token)
            continue

        # Don't fuzzy-correct tiny words.
        if len(lower) < 4:
            corrected_tokens.append(token)
            continue

        candidate, score = best_fuzzy_candidate(token)

        if candidate is None:
            corrected_tokens.append(token)
            continue

        # Additional safety:
        #
        # The candidate should not differ wildly in length.
        if abs(len(candidate) - len(token)) > 3:
            corrected_tokens.append(token)
            continue

        corrected_tokens.append(candidate)

        correction_log.append(
            {
                "type": "fuzzy",
                "original": token,
                "replacement": candidate,
                "confidence": f"{score:.3f}",
                "reason": "restricted_ocr_candidate",
            }
        )

    # Reconstruct text.
    result = ""

    for token in corrected_tokens:

        if not result:
            result = token
            continue

        # No space before punctuation.
        if re.fullmatch(r"[,.!?;:%)\]}]", token):
            result += token

        # No space after opening punctuation.
        elif result.endswith(("(", "[", "{")):
            result += token

        else:
            result += " " + token

    return result, correction_log


# ============================================================
# 10. CONTEXTUAL EMOTIONAL VALIDATION
# ============================================================

def contextual_validation(
    text: str,
) -> List[Dict[str, str]]:
    """
    Identify words that became meaningful because of their context.

    IMPORTANT:
        This function does NOT assign a Navarasa.

    navarasa_engine.py remains responsible for that.

    This function simply records useful contextual phrases so that
    downstream analysis has cleaner evidence.
    """

    observations: List[Dict[str, str]] = []

    lowered = text.lower()

    contextual_patterns = [
        (
            r"\bnew\s+people\b",
            "new people",
            "contextual_phrase",
        ),
        (
            r"\bwonder\s+at\b",
            "wonder at",
            "contextual_phrase",
        ),
        (
            r"\blove\s+meeting\b",
            "love meeting",
            "contextual_phrase",
        ),
        (
            r"\bbeautiful\s+(?:places|people|things|views)\b",
            "beautiful + noun",
            "contextual_phrase",
        ),
        (
            r"\bat\s+peace\b",
            "at peace",
            "contextual_phrase",
        ),
        (
            r"\bface\s+my\s+fear\b",
            "face my fear",
            "contextual_phrase",
        ),
        (
            r"\bkeep\s+going\b",
            "keep going",
            "contextual_phrase",
        ),
    ]

    for pattern, phrase, reason in contextual_patterns:

        matches = re.findall(
            pattern,
            lowered,
        )

        if matches:
            observations.append(
                {
                    "phrase": phrase,
                    "reason": reason,
                    "occurrences": str(len(matches)),
                }
            )

    return observations


# ============================================================
# 11. MAIN CORRECTION FUNCTION
# ============================================================

def correct_ocr_text(
    text: str,
) -> Dict:
    """
    Main public API.

    Input:
        raw OCR text

    Output:
        {
            "raw_text": ...,
            "corrected_text": ...,
            "corrections": [...],
            "context": [...]
        }
    """

    if not isinstance(text, str):
        raise TypeError("OCR text must be a string.")

    raw_text = text

    # Step 1: whitespace normalization
    corrected = normalize_whitespace(raw_text)

    # Step 2: phrase corrections
    corrected, phrase_log = apply_phrase_corrections(
        corrected
    )

    # Step 3: exact corrections
    corrected, exact_log = apply_exact_replacements(
        corrected
    )

    # Step 4: conservative fuzzy correction
    corrected, fuzzy_log = apply_safe_fuzzy_corrections(
        corrected
    )

    # Step 5: final whitespace normalization
    corrected = normalize_whitespace(corrected)

    # Step 6: contextual observations
    context = contextual_validation(corrected)

    corrections = (
        phrase_log
        + exact_log
        + fuzzy_log
    )

    return {
        "raw_text": raw_text,
        "corrected_text": corrected,
        "corrections": corrections,
        "context": context,
        "correction_count": len(corrections),
    }


# ============================================================
# 12. DEBUG / SELF TEST
# ============================================================

def run_self_test() -> bool:
    """
    Test the corrector independently from the rest of the system.
    """

    test_text = (
        "Because love meekn Yew people "
        "and wo od er at how beautiful "
        "they look and learn stories albout them."
    )

    result = correct_ocr_text(test_text)

    corrected = result["corrected_text"].lower()

    required = [
        "love",
        "meeting",
        "new people",
        "wonder",
        "beautiful",
        "about",
    ]

    passed = all(
        item in corrected
        for item in required
    )

    print()
    print("=" * 60)
    print("FREEING THE PARROT")
    print("OCR SEMANTIC CORRECTOR SELF TEST")
    print("=" * 60)

    print()
    print("[RAW]")
    print(test_text)

    print()
    print("[CORRECTED]")
    print(result["corrected_text"])

    print()
    print("[CORRECTIONS]")
    for correction in result["corrections"]:
        print(" •", correction)

    print()
    print("[CONTEXT]")
    for observation in result["context"]:
        print(" •", observation)

    print()

    if passed:
        print("[SELF TEST] PASS")
    else:
        print("[SELF TEST] FAIL")

    print("=" * 60)

    return passed


# ============================================================
# 13. DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":
    run_self_test()