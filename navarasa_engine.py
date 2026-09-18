"""
FREEING THE PARROT
NAVARASA EMOTIONAL INTELLIGENCE ENGINE

Purpose:
    Analyse OCR text and conversational text using the Navarasa framework.

Design principles:
    1. Generic words are NOT automatically treated as emotional.
    2. Explicit emotional words and phrases are mapped to Navarasa buckets.
    3. Phrase matches have higher priority than single-word matches.
    4. Negation is detected.
    5. Intensity modifiers influence emotional strength.
    6. Repeated words are recorded but do not endlessly inflate scores.
    7. Sentiment is supplementary evidence, not the primary classifier.
    8. The engine always returns a predictable JSON-compatible structure.
"""

import json
import re
from collections import defaultdict


# ============================================================
# NAVARASA DEFINITIONS
# ============================================================

RASAS = [
    "Shringara",
    "Hasya",
    "Karuna",
    "Raudra",
    "Veera",
    "Bhayanaka",
    "Bibhatsa",
    "Adbhuta",
    "Shanta",
]


# ============================================================
# EMOTIONAL LEXICON
#
# IMPORTANT:
# These are NOT just random English words.
# They are words/phrases that carry emotional meaning
# strongly enough to be considered evidence.
# ============================================================

EMOTIONAL_LEXICON = {

    "Shringara": {
        "core": {
            "love",
            "loving",
            "loved",
            "affection",
            "affectionate",
            "adore",
            "adored",
            "adoring",
            "attraction",
            "attracted",
            "beautiful",
            "beauty",
            "romantic",
            "romance",
            "passion",
            "passionate",
            "desire",
            "cherish",
            "cherished",
            "intimate",
            "intimacy",
            "tender",
            "tenderness",
            "fond",
            "fondness",
        },

        "phrases": {
            "fall in love",
            "in love",
            "deeply in love",
            "madly in love",
            "love dearly",
            "love very much",
            "feel attracted",
            "feel attraction",
        },
    },


    "Hasya": {
        "core": {
            "laugh",
            "laughed",
            "laughing",
            "laughter",
            "funny",
            "humor",
            "humour",
            "hilarious",
            "amusing",
            "amused",
            "joke",
            "jokes",
            "joking",
            "comic",
            "comedy",
            "giggle",
            "giggles",
            "smile",
            "smiling",
            "joyful",
            "playful",
        },

        "phrases": {
            "made me laugh",
            "couldn't stop laughing",
            "cannot stop laughing",
            "burst out laughing",
            "laugh out loud",
        },
    },


    "Karuna": {
        "core": {
            "sad",
            "sadness",
            "sorrow",
            "sorrowful",
            "grief",
            "grieving",
            "lonely",
            "loneliness",
            "alone",
            "hurt",
            "hurting",
            "heartbroken",
            "heartbreak",
            "pain",
            "painful",
            "cry",
            "crying",
            "tears",
            "regret",
            "regretful",
            "loss",
            "lost",
            "helpless",
            "hopeless",
            "despair",
            "desperate",
            "miserable",
            "misery",
            "mourning",
            "suffering",
        },

        "phrases": {
            "feel alone",
            "feeling alone",
            "feel lonely",
            "feeling lonely",
            "broken heart",
            "brokenhearted",
            "lost someone",
            "miss someone",
            "miss them",
            "in pain",
            "feel helpless",
            "feel hopeless",
        },
    },


    "Raudra": {
        "core": {
            "angry",
            "anger",
            "furious",
            "fury",
            "rage",
            "raging",
            "hate",
            "hatred",
            "frustrated",
            "frustration",
            "annoyed",
            "annoyance",
            "irritated",
            "irritation",
            "resentful",
            "resentment",
            "hostile",
            "hostility",
            "outraged",
            "outrage",
            "enraged",
            "mad",
        },

        "phrases": {
            "so angry",
            "extremely angry",
            "really angry",
            "very angry",
            "fed up",
            "sick of",
            "can't stand",
            "cannot stand",
            "lost my temper",
            "lose my temper",
        },
    },


    "Veera": {
        "core": {
            "brave",
            "bravery",
            "courage",
            "courageous",
            "bold",
            "determined",
            "determination",
            "strong",
            "strength",
            "resilient",
            "resilience",
            "confident",
            "confidence",
            "fearless",
            "persistent",
            "persistence",
            "persevere",
            "perseverance",
            "fight",
            "fighting",
            "overcome",
            "victory",
            "triumph",
            "empowered",
            "empowerment",
        },

        "phrases": {
            "keep going",
            "face my fear",
            "face my fears",
            "stand up for myself",
            "fight back",
            "never give up",
            "won't give up",
            "will not give up",
            "push through",
            "rise above",
        },
    },


    "Bhayanaka": {
        "core": {
            "afraid",
            "fear",
            "fearful",
            "terrified",
            "terror",
            "scared",
            "frightened",
            "fright",
            "anxious",
            "anxiety",
            "panic",
            "panicked",
            "dread",
            "dreadful",
            "horrified",
            "horror",
            "nervous",
            "nervousness",
            "threat",
            "threatened",
            "unsafe",
            "danger",
            "dangerous",
            "worry",
            "worried",
            "uncertain",
            "uncertainty",
        },

        "phrases": {
            "scared to death",
            "worried about",
            "afraid of",
            "terrified of",
            "fear of",
            "worst case",
            "worst-case scenario",
            "feel unsafe",
            "not safe",
        },
    },


    "Bibhatsa": {
        "core": {
            "disgusting",
            "disgust",
            "disgusted",
            "disgustingness",
            "gross",
            "repulsive",
            "repulsed",
            "revolting",
            "revolt",
            "nauseating",
            "nauseated",
            "vile",
            "horrible",
            "filthy",
            "dirty",
            "sickening",
            "offensive",
            "abhorrent",
            "repugnant",
            "contempt",
        },

        "phrases": {
            "absolutely disgusting",
            "completely disgusting",
            "makes me sick",
            "sick to my stomach",
            "turns my stomach",
            "can't stomach",
            "cannot stomach",
        },
    },


    "Adbhuta": {
        "core": {
            "wonder",
            "wonderful",
            "wonderment",
            "amazed",
            "amazing",
            "amazement",
            "astonished",
            "astonishing",
            "astonishment",
            "awe",
            "awesome",
            "awestruck",
            "incredible",
            "incredibly",
            "curious",
            "curiosity",
            "fascinated",
            "fascinating",
            "discovery",
            "discover",
            "discovering",
            "surprised",
            "surprise",
            "unexpected",
            "marvel",
            "marvelous",
            "extraordinary",
            "wow",
        },

        "phrases": {
            "filled with wonder",
            "full of wonder",
            "in awe",
            "blown away",
            "can't believe",
            "cannot believe",
            "mind blown",
            "mind-blowing",
            "what a discovery",
        },
    },


    "Shanta": {
        "core": {
            "calm",
            "peace",
            "peaceful",
            "serene",
            "serenity",
            "still",
            "stillness",
            "quiet",
            "tranquil",
            "tranquility",
            "content",
            "contentment",
            "relaxed",
            "relaxation",
            "balanced",
            "balance",
            "acceptance",
            "accept",
            "mindful",
            "mindfulness",
            "centered",
            "grounded",
        },

        "phrases": {
            "at peace",
            "feel calm",
            "feeling calm",
            "feel peaceful",
            "feeling peaceful",
            "at ease",
            "inner peace",
            "peace of mind",
            "calm down",
        },
    },
}


# ============================================================
# WORDS THAT ARE GENERIC
#
# These should NOT independently create an emotional state.
# They may become meaningful only when surrounding context
# creates an explicit phrase.
# ============================================================

GENERIC_WORDS = {
    "new",
    "people",
    "person",
    "places",
    "place",
    "travel",
    "travelling",
    "traveling",
    "see",
    "seeing",
    "look",
    "looking",
    "learn",
    "learning",
    "story",
    "stories",
    "beautifully",
    "absolutely",
    "really",
    "very",
    "extremely",
    "much",
    "more",
    "good",
    "great",
    "nice",
    "interesting",
}


# ============================================================
# INTENSITY MODIFIERS
# ============================================================

INTENSITY_MODIFIERS = {
    "slightly": 0.70,
    "somewhat": 0.80,
    "a little": 0.75,
    "little": 0.75,
    "mildly": 0.75,

    "quite": 1.10,
    "rather": 1.10,
    "pretty": 1.10,

    "really": 1.20,
    "very": 1.25,
    "so": 1.25,

    "deeply": 1.35,
    "strongly": 1.35,
    "extremely": 1.45,
    "absolutely": 1.45,
    "completely": 1.45,
    "totally": 1.45,
    "utterly": 1.50,
    "incredibly": 1.40,
}


# ============================================================
# NEGATION WORDS
# ============================================================

NEGATION_WORDS = {
    "not",
    "never",
    "no",
    "none",
    "neither",
    "nor",
    "without",
    "hardly",
    "barely",
    "don't",
    "dont",
    "doesn't",
    "doesnt",
    "didn't",
    "didnt",
    "isn't",
    "isnt",
    "wasn't",
    "wasnt",
    "can't",
    "cant",
    "cannot",
    "won't",
    "wont",
}


# ============================================================
# SENTIMENT FALLBACK LEXICON
#
# Used only if vaderSentiment is unavailable.
# ============================================================

POSITIVE_WORDS = {
    "love",
    "beautiful",
    "amazing",
    "wonderful",
    "happy",
    "joy",
    "joyful",
    "great",
    "good",
    "brave",
    "peace",
    "peaceful",
    "calm",
    "excited",
    "awesome",
    "incredible",
    "funny",
    "laugh",
    "laughing",
    "adore",
}

NEGATIVE_WORDS = {
    "sad",
    "angry",
    "furious",
    "hate",
    "frustrated",
    "afraid",
    "fear",
    "terrified",
    "scared",
    "anxious",
    "pain",
    "hurt",
    "lonely",
    "disgusting",
    "horrible",
    "hopeless",
    "helpless",
    "grief",
}


# ============================================================
# TOKENIZATION
# ============================================================

def tokenize(text):
    """
    Convert text into lowercase word tokens.
    """
    return re.findall(r"\b[\w'-]+\b", text.lower())


# ============================================================
# PHRASE MATCHING
# ============================================================

def phrase_occurrences(text, phrase):
    """
    Return the number of times an emotional phrase occurs.
    """
    pattern = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)"
    return len(re.findall(pattern, text.lower()))


# ============================================================
# INTENSITY DETECTION
# ============================================================

def get_intensity(tokens, index):
    """
    Look backwards for an intensity modifier.

    Example:
        "absolutely love"

    gives love a stronger intensity.
    """

    intensity = 1.0

    window_start = max(0, index - 3)
    previous_words = tokens[window_start:index]

    for modifier, multiplier in INTENSITY_MODIFIERS.items():

        modifier_tokens = modifier.split()

        if len(modifier_tokens) <= len(previous_words):

            if previous_words[-len(modifier_tokens):] == modifier_tokens:
                intensity *= multiplier
                break

    return round(min(intensity, 1.5), 3)


# ============================================================
# NEGATION DETECTION
# ============================================================

def is_negated(tokens, index):
    """
    Check whether an emotional word is negated.

    Example:
        "I am not happy"

    should not produce the same emotional signal
    as "I am happy".
    """

    window_start = max(0, index - 3)

    for word in tokens[window_start:index]:
        if word in NEGATION_WORDS:
            return True

    return False


# ============================================================
# SENTIMENT
# ============================================================

def calculate_sentiment(text):
    """
    Try VADER first.

    If VADER is unavailable, use a lightweight fallback.
    """

    # --------------------------------------------------------
    # Preferred: VADER
    # --------------------------------------------------------

    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(text)

        return {
            "positive": round(scores.get("pos", 0.0), 3),
            "negative": round(scores.get("neg", 0.0), 3),
            "neutral": round(scores.get("neu", 0.0), 3),
            "compound": round(scores.get("compound", 0.0), 3),
        }

    except ImportError:
        pass

    # --------------------------------------------------------
    # Fallback sentiment
    # --------------------------------------------------------

    tokens = tokenize(text)

    if not tokens:
        return {
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,
            "compound": 0.0,
        }

    positive_count = sum(
        1 for token in tokens
        if token in POSITIVE_WORDS
    )

    negative_count = sum(
        1 for token in tokens
        if token in NEGATIVE_WORDS
    )

    total = len(tokens)

    positive = positive_count / total
    negative = negative_count / total

    neutral = max(
        0.0,
        1.0 - positive - negative
    )

    compound = 0.0

    if positive_count > negative_count:
        compound = min(
            1.0,
            positive_count / max(1, positive_count + negative_count)
        )

    elif negative_count > positive_count:
        compound = -min(
            1.0,
            negative_count / max(1, positive_count + negative_count)
        )

    return {
        "positive": round(positive, 3),
        "negative": round(negative, 3),
        "neutral": round(neutral, 3),
        "compound": round(compound, 3),
    }


# ============================================================
# MAIN ANALYSIS FUNCTION
# ============================================================

def analyse_text(text):
    """
    Analyse a piece of text and return a JSON-compatible result.

    This is the PUBLIC function that main_watcher.py should import.
    """

    if not isinstance(text, str):
        text = str(text)

    text = text.strip()

    # --------------------------------------------------------
    # Empty text
    # --------------------------------------------------------

    if not text:

        return {
            "primary_rasa": "Shanta",
            "rasa_scores": {},
            "evidence": {},
            "emotional_words": [],
            "analysis_quality": "no_text",
            "sentiment": calculate_sentiment(""),
            "text": "",
        }

    lower_text = text.lower()
    tokens = tokenize(lower_text)

    evidence = defaultdict(list)
    raw_scores = defaultdict(float)

    detected_words = []

    # --------------------------------------------------------
    # STEP 1
    # Phrase matching
    #
    # Phrases are checked first because:
    #
    # "face my fear"
    #
    # should be treated as a Veera expression,
    # rather than only "fear" -> Bhayanaka.
    # --------------------------------------------------------

    matched_phrase_ranges = []

    for rasa, lexicon in EMOTIONAL_LEXICON.items():

        for phrase in lexicon["phrases"]:

            occurrences = phrase_occurrences(
                lower_text,
                phrase
            )

            if occurrences == 0:
                continue

            confidence = 1.0

            # Longer phrases provide stronger evidence.
            phrase_word_count = len(phrase.split())

            confidence = min(
                1.0,
                0.90 + (0.03 * min(phrase_word_count, 3))
            )

            # Detect simple phrase-level negation.
            phrase_tokens = phrase.split()

            phrase_index = lower_text.find(phrase)

            before_phrase = lower_text[
                max(0, phrase_index - 20):
                phrase_index
            ]

            negated = any(
                word in before_phrase.split()
                for word in NEGATION_WORDS
            )

            if negated:
                confidence *= 0.20

            for _ in range(occurrences):

                evidence[rasa].append({
                    "word": phrase,
                    "rasa": rasa,
                    "confidence": round(confidence, 3),
                    "intensity": 1.0,
                    "reason": "exact_emotional_phrase",
                    "occurrences": 1,
                })

                raw_scores[rasa] += (
                    confidence * 1.5
                )

                detected_words.append(phrase)

    # --------------------------------------------------------
    # STEP 2
    # Single-word matching
    # --------------------------------------------------------

    for index, token in enumerate(tokens):

        # Generic words are deliberately ignored.
        if token in GENERIC_WORDS:
            continue

        for rasa, lexicon in EMOTIONAL_LEXICON.items():

            if token not in lexicon["core"]:
                continue

            # ------------------------------------------------
            # Negation
            # ------------------------------------------------

            if is_negated(tokens, index):
                continue

            # ------------------------------------------------
            # Intensity
            # ------------------------------------------------

            intensity = get_intensity(tokens, index)

            confidence = 0.95

            # ------------------------------------------------
            # Store evidence
            # ------------------------------------------------

            evidence[rasa].append({
                "word": token,
                "rasa": rasa,
                "confidence": confidence,
                "intensity": intensity,
                "reason": "exact_emotional_lexicon",
                "occurrences": 1,
            })

            # ------------------------------------------------
            # Score
            #
            # We cap individual word contribution so that:
            #
            # "love love love love love"
            #
            # does not completely destroy the scoring model.
            # ------------------------------------------------

            raw_scores[rasa] += (
                confidence * intensity
            )

            detected_words.append(token)

    # --------------------------------------------------------
    # STEP 3
    # Remove duplicate evidence entries where appropriate.
    #
    # We retain occurrence count so the system still knows
    # repetition happened.
    # --------------------------------------------------------

    cleaned_evidence = {}

    for rasa, items in evidence.items():

        grouped = {}

        for item in items:

            key = (
                item["word"],
                item["reason"]
            )

            if key not in grouped:

                grouped[key] = dict(item)

            else:

                grouped[key]["occurrences"] += (
                    item.get("occurrences", 1)
                )

        cleaned_evidence[rasa] = list(
            grouped.values()
        )

    # --------------------------------------------------------
    # STEP 4
    # Calculate normalized Rasa scores.
    #
    # Highest score becomes 1.0.
    # Other Rasas are represented proportionally.
    # --------------------------------------------------------

    if raw_scores:

        max_score = max(raw_scores.values())

        rasa_scores = {}

        for rasa, score in raw_scores.items():

            normalized = score / max_score

            rasa_scores[rasa] = round(
                normalized,
                3
            )

    else:

        rasa_scores = {}

    # --------------------------------------------------------
    # STEP 5
    # Determine primary Rasa.
    # --------------------------------------------------------

    if rasa_scores:

        primary_rasa = max(
            rasa_scores,
            key=rasa_scores.get
        )

    else:

        primary_rasa = "Shanta"

    # --------------------------------------------------------
    # STEP 6
    # Determine analysis quality.
    # --------------------------------------------------------

    emotional_count = len(detected_words)

    if emotional_count == 0:

        analysis_quality = "no_emotion_detected"

    elif emotional_count == 1:

        analysis_quality = "weak_emotion_signal"

    elif emotional_count <= 3:

        analysis_quality = "moderate_emotion_signal"

    else:

        analysis_quality = "strong_emotion_signal"

    # --------------------------------------------------------
    # STEP 7
    # Unique emotional words.
    # --------------------------------------------------------

    emotional_words = sorted(
        set(detected_words),
        key=str.lower
    )

    # --------------------------------------------------------
    # STEP 8
    # Sentiment.
    # --------------------------------------------------------

    sentiment = calculate_sentiment(text)

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    result = {
        "primary_rasa": primary_rasa,

        "rasa_scores": rasa_scores,

        "evidence": cleaned_evidence,

        "emotional_words": emotional_words,

        "analysis_quality": analysis_quality,

        "sentiment": sentiment,

        "text": text,
    }

    return result


# ============================================================
# PRETTY TERMINAL OUTPUT
# ============================================================

def print_profile(result):

    print()
    print("[NAVARASA PROFILE]")
    print("=" * 60)

    if not result["rasa_scores"]:

        print("No explicit emotional Rasa detected.")
        print("Defaulting to Shanta.")

    else:

        # Highest score first
        sorted_rasas = sorted(
            result["rasa_scores"].items(),
            key=lambda item: item[1],
            reverse=True
        )

        for rasa, score in sorted_rasas:

            print()
            print(rasa)
            print(f"Score: {score}")

            for item in result["evidence"].get(
                rasa,
                []
            ):

                print(
                    "  • "
                    f"{item['word']} | "
                    f"confidence={item['confidence']} | "
                    f"intensity={item['intensity']} | "
                    f"{item['reason']}"
                )

    print()
    print("PRIMARY RASA:")
    print(result["primary_rasa"])

    print()
    print("[SENTIMENT]")
    print("-" * 60)

    sentiment = result["sentiment"]

    print(
        f"Positive : {sentiment['positive']:.3f}"
    )

    print(
        f"Negative : {sentiment['negative']:.3f}"
    )

    print(
        f"Neutral  : {sentiment['neutral']:.3f}"
    )

    print(
        f"Compound : {sentiment['compound']:.3f}"
    )

    print()
    print("[ANALYSIS QUALITY]")
    print(result["analysis_quality"])

    print()
    print("[RAW JSON]")
    print("-" * 60)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )


# ============================================================
# SELF TESTS
# ============================================================

SELF_TESTS = [

    {
        "text": "I love beautiful things and wonder at the world.",
        "expected": "Shringara",
    },

    {
        "text": "I am absolutely terrified of what might happen.",
        "expected": "Bhayanaka",
    },

    {
        "text": "I am frustrated and furious about this.",
        "expected": "Raudra",
    },

    {
        "text": "I feel alone and completely heartbroken.",
        "expected": "Karuna",
    },

    {
        "text": "I was amazed by the incredible discovery.",
        "expected": "Adbhuta",
    },

    {
        "text": "I am determined to face my fear and keep going.",
        "expected": "Veera",
    },

    {
        "text": "That joke made me laugh so hard.",
        "expected": "Hasya",
    },

    {
        "text": "That is absolutely disgusting.",
        "expected": "Bibhatsa",
    },

    {
        "text": "I feel calm and completely at peace.",
        "expected": "Shanta",
    },

    {
        "text": "I love this.",
        "expected": "Shringara",
    },

    {
        "text": "The table is next to the window.",
        "expected": "Shanta",
    },
]


def run_self_tests():

    print()
    print("=" * 60)
    print("FREEING THE PARROT")
    print("NAVARASA ENGINE SELF TEST")
    print("=" * 60)

    passed = 0

    for number, test in enumerate(
        SELF_TESTS,
        start=1
    ):

        result = analyse_text(
            test["text"]
        )

        actual = result["primary_rasa"]

        if actual == test["expected"]:

            status = "PASS"
            passed += 1

        else:

            status = "FAIL"

        print()
        print(
            f"[TEST {number:02d}] {status}"
        )

        print(
            f"Expected : {test['expected']}"
        )

        print(
            f"Actual   : {actual}"
        )

        print(
            f"Scores   : {result['rasa_scores']}"
        )

        print(
            f"Words    : {result['emotional_words']}"
        )

    print()
    print("=" * 60)
    print(
        f"SELF TEST COMPLETE: "
        f"{passed}/{len(SELF_TESTS)} passed"
    )
    print("=" * 60)

    return passed == len(SELF_TESTS)


# ============================================================
# INTERACTIVE MODE
# ============================================================

def interactive_mode():

    print()
    print("=" * 60)
    print("CUSTOM TEST")
    print("=" * 60)

    print()
    print(
        "Type a sentence to analyse "
        "(or press Enter to exit):"
    )

    while True:

        try:

            text = input("> ")

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print()
            break

        if not text.strip():
            break

        result = analyse_text(text)

        print_profile(result)

        print()
        print(
            "Type another sentence "
            "(or press Enter to exit):"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    tests_passed = run_self_tests()

    print()

    if not tests_passed:

        print(
            "[WARNING] "
            "One or more self-tests failed."
        )

        print(
            "[WARNING] "
            "Review the lexicon before integrating "
            "this engine with the watcher."
        )

    else:

        print(
            "[ENGINE] "
            "All self-tests passed."
        )

    interactive_mode()