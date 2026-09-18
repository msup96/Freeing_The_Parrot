"""
FREEING THE PARROT
OCR REPAIR LAYER

Purpose:
    Repair common OCR character substitutions WITHOUT inventing text.

Design principle:
    OCR repair must be conservative.

    We only replace highly probable character-level errors.
    We do NOT use sentiment, Navarasa, or semantic inference here.

Pipeline:

    IMAGE
      ↓
    TESSERACT OCR
      ↓
    BASIC OCR CLEANUP
      ↓
    THIS MODULE
      ↓
    REPAIRED TEXT
      ↓
    NAVARASA ENGINE
"""

import re


# ------------------------------------------------------------
# HIGH-CONFIDENCE CHARACTER SUBSTITUTIONS
# ------------------------------------------------------------

CHARACTER_REPLACEMENTS = {
    # Common lowercase handwriting/OCR confusions
    "0": "o",
    "1": "l",
    "5": "s",

    # These are deliberately NOT globally mapped:
    #
    # "f" ↔ "t"
    # "r" ↔ "v"
    # "n" ↔ "u"
    #
    # because doing that globally can corrupt legitimate words.
}


# ------------------------------------------------------------
# WORD-LEVEL OCR CORRECTIONS
# ------------------------------------------------------------
#
# These are only corrections that have been observed in
# handwritten scans from this installation.
#
# IMPORTANT:
# We keep this list explicit and auditable.
# No generative guessing.
#

KNOWN_OCR_CORRECTIONS = {

    # "people" → "feople"
    "feople": "people",

    # "tell" → "fell"
    "fell": "tell",

    # "know" → "knoewo"
    "knoewo": "know",

    # "hard" → "havd"
    "havd": "hard",

    # "perhaps" → "fechaps"
    "fechaps": "perhaps",

    # "miracle" → "mivace"
    "mivace": "miracle",

    # "persistent" → "persis ent"
    "persisent": "persistent",

    # common OCR corruption
    "coould": "could",

    # "easier" → "easieY"
    "easiey": "easier",

    # "continue" → "antiue"
    "antiue": "continue",

    # Common OCR errors observed earlier
    "albout": "about",
    "alout": "about",
    "meekn": "meeting",
    "yew": "new",
    "nevo": "new",
    "frevo": "new",
    "laces": "places",
    "onder": "wonder",
    "yonder": "wonder",
    "ovo": "how",
}


# ------------------------------------------------------------
# NORMALISE TOKEN
# ------------------------------------------------------------

def normalise_token(token):
    """
    Normalise a single OCR token while preserving punctuation.
    """

    if not token:
        return token

    # Separate leading/trailing punctuation.
    match = re.match(r"^([^A-Za-z0-9]*)(.*?)([^A-Za-z0-9]*)$", token)

    if not match:
        return token

    prefix = match.group(1)
    core = match.group(2)
    suffix = match.group(3)

    if not core:
        return token

    # Normalise for lookup only.
    lookup = core.lower()

    # Known whole-word correction.
    if lookup in KNOWN_OCR_CORRECTIONS:
        replacement = KNOWN_OCR_CORRECTIONS[lookup]

        # Preserve original capitalisation pattern.
        if core.isupper():
            replacement = replacement.upper()
        elif core[:1].isupper():
            replacement = replacement.capitalize()

        return prefix + replacement + suffix

    # Conservative character replacements.
    corrected = core

    for old, new in CHARACTER_REPLACEMENTS.items():
        corrected = corrected.replace(old, new)

    return prefix + corrected + suffix


# ------------------------------------------------------------
# REPAIR SPLIT WORDS
# ------------------------------------------------------------

SPLIT_WORD_CORRECTIONS = {
    "persis ent": "persistent",
    "anti ue": "continue",
    "co uld": "could",
}


def repair_split_words(text):
    """
    Repair a small set of known OCR cases where a word has
    been split by an erroneous whitespace character.
    """

    repaired = text

    for bad, good in SPLIT_WORD_CORRECTIONS.items():
        repaired = re.sub(
            rf"\b{re.escape(bad)}\b",
            good,
            repaired,
            flags=re.IGNORECASE,
        )

    return repaired


# ------------------------------------------------------------
# MAIN OCR REPAIR FUNCTION
# ------------------------------------------------------------

def repair_ocr_text(text):
    """
    Apply conservative OCR repair.

    This function MUST NOT:
        - classify emotion
        - assign rasa
        - use sentiment
        - invent missing sentences
        - rewrite grammar
        - paraphrase the user's writing

    It only repairs known OCR corruption.
    """

    if not text:
        return text

    repaired = text

    # First repair multi-token OCR errors.
    repaired = repair_split_words(repaired)

    # Then repair individual tokens.
    tokens = repaired.split()

    repaired_tokens = [
        normalise_token(token)
        for token in tokens
    ]

    repaired = " ".join(repaired_tokens)

    # Normalise repeated whitespace.
    repaired = re.sub(r"\s+", " ", repaired).strip()

    return repaired


# ------------------------------------------------------------
# DEBUG / SELF TEST
# ------------------------------------------------------------

def run_self_test():
    tests = [
        ("feople", "people"),
        ("fell", "tell"),
        ("knoewo", "know"),
        ("havd", "hard"),
        ("fechaps", "perhaps"),
        ("mivace", "miracle"),
        ("coould", "could"),
        ("easieY", "easier"),
        ("antiue", "continue"),
        ("albout", "about"),
        ("yew", "new"),
        ("laces", "places"),
        ("yonder", "wonder"),
    ]

    passed = 0

    print("=" * 60)
    print("FREEING THE PARROT")
    print("OCR REPAIR SELF TEST")
    print("=" * 60)

    for index, (bad, expected) in enumerate(tests, start=1):

        actual = repair_ocr_text(bad)

        if actual.lower() == expected.lower():
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"

        print(
            f"[TEST {index:02d}] {status} | "
            f"{bad!r} → {actual!r} | "
            f"expected={expected!r}"
        )

    print("=" * 60)
    print(
        f"OCR REPAIR SELF TEST: "
        f"{passed}/{len(tests)} passed"
    )
    print("=" * 60)

    return passed == len(tests)


if __name__ == "__main__":
    run_self_test()