"""Conversation-derived thematic vocabulary for the post-session 27-card reading.

This module is deliberately post-session only. It reads participant turns from
the locked EventStore and produces a small, neutral thematic vocabulary. It
does not infer identity, diagnosis, or sensitive attributes.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from ftp.events.model import EventType

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")

_STOPWORDS = frozenset({
    "about", "after", "again", "also", "been", "being", "because", "before",
    "between", "could", "does", "doing", "done", "during", "each", "even",
    "from", "have", "having", "here", "into", "just", "like", "more", "most",
    "much", "need", "only", "really", "said", "same", "some", "something",
    "that", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "very", "want", "what", "when", "where", "which",
    "while", "with", "would", "your", "you", "came", "come", "feel", "feeling",
    "felt", "think", "thought", "know", "knew", "say", "saying", "tell",
    "told", "make", "made", "makes", "trying", "still", "keep", "keeps",
})

_THEME_LEXICONS: dict[str, tuple[str, ...]] = {
    "expectation_pressure": (
        "expectation", "expectations", "perform", "performance", "enough",
        "needed", "demand", "demands", "pressure", "supposed", "should",
        "prove", "proving", "approval", "burden", "responsibility", "role",
    ),
    "clarity_guidance": (
        "clarity", "clear", "guidance", "perspective", "sensible", "mindful",
        "understand", "understanding", "explain", "explanation", "sense",
        "meaning", "rationale", "answer", "direction", "help",
    ),
    "purpose_direction": (
        "purpose", "purposeless", "lost", "direction", "point", "meaning",
        "future", "path", "reason", "why", "aim", "beginning", "start",
    ),
    "relationships_boundaries": (
        "people", "person", "relationship", "relationships", "family",
        "partner", "friend", "friends", "others", "boundary", "boundaries",
        "giving", "taking", "judgmental", "judged", "judgment",
    ),
    "exhaustion_overload": (
        "tired", "tiredness", "exhausted", "exhausting", "heavy", "drained",
        "energy", "overwhelmed", "overload", "weary", "fatigue", "carrying",
        "weight", "errands",
    ),
    "change_transition": (
        "change", "changed", "changing", "transition", "moving", "leaving",
        "new", "ending", "started", "different", "next", "beginning",
    ),
    "decision_uncertainty": (
        "decide", "decision", "choice", "choosing", "unsure", "uncertainty",
        "uncertain", "doubt", "confused", "confusion", "whether", "maybe",
    ),
    "self_understanding": (
        "myself", "self", "pattern", "patterns", "reflection", "reflect",
        "trigger", "triggers", "behaviour", "behavior", "recognise",
        "recognize", "understanding",
    ),
    "work_craft": (
        "work", "project", "design", "job", "career", "build", "building",
        "create", "creating", "deadline", "study", "thesis", "research",
    ),
}

_THEME_PHRASES: dict[str, tuple[str, str, str]] = {
    "expectation_pressure": ("EXPECTATIONS", "CLARITY", "BURDEN"),
    "clarity_guidance": ("CLARITY", "GUIDANCE", "LANGUAGE"),
    "purpose_direction": ("PURPOSE", "DIRECTION", "BEGINNING"),
    "relationships_boundaries": ("RELATIONSHIPS", "BOUNDARIES", "RECIPROCITY"),
    "exhaustion_overload": ("EXHAUSTION", "WEIGHT", "REST"),
    "change_transition": ("CHANGE", "TRANSITION", "BEGINNING"),
    "decision_uncertainty": ("CHOICE", "UNCERTAINTY", "DISCERNMENT"),
    "self_understanding": ("SELF-UNDERSTANDING", "PATTERNS", "RECOGNITION"),
    "work_craft": ("WORK", "CRAFT", "DIRECTION"),
    "reflection": ("REFLECTION", "ATTENTION", "MEANING"),
}

_TERRITORY_TEMPLATES = (
    "{p}", "WEIGHT OF {p}", "PRESSURE AROUND {p}", "{q}",
    "EDGE OF {p}", "LANGUAGE OF {p}", "SPACE AROUND {p}", "{r}",
    "SHADOW OF {p}", "PULL OF {q}", "PATTERN OF {p}",
    "DISTANCE FROM {p}", "PAUSE AROUND {q}", "COST OF {p}",
    "RETURN TO {q}", "BOUNDARY OF {p}", "OPENING TOWARD {r}",
    "FRICTION WITH {q}", "SHAPE OF {p}", "ROOM FOR {q}",
    "THREAD BETWEEN {p} AND {q}", "WEIGHT OF {r}", "PATH BEYOND {p}",
    "ECHO OF {q}", "REPAIR OF {r}", "BEGINNING AFTER {p}",
    "NEW LANGUAGE FOR {q}",
)

_MOTIF_TEMPLATES = (
    "theme-core", "theme-weight", "theme-pressure", "theme-guidance",
    "theme-edge", "theme-language", "theme-space", "theme-secondary",
    "theme-shadow", "theme-pull", "theme-pattern", "theme-distance",
    "theme-pause", "theme-cost", "theme-return", "theme-boundary",
    "theme-opening", "theme-friction", "theme-shape", "theme-room",
    "theme-thread", "theme-weight-secondary", "theme-path",
    "theme-echo", "theme-repair", "theme-beginning", "theme-language-new",
)


def derive_conversation_theme(coordinator: Any) -> dict[str, Any]:
    """Derive a neutral post-session theme from participant turns only."""
    texts: list[str] = []
    for event in coordinator.store.all_events():
        if event.event_type != EventType.PARROT_TURN_GENERATED:
            continue
        text = str(event.payload.get("user_text") or "").strip()
        if text:
            texts.append(text)

    corpus = " ".join(texts).lower()
    tokens = [token for token in _WORD_RE.findall(corpus) if token not in _STOPWORDS]

    scores: Counter[str] = Counter()
    for theme, lexicon in _THEME_LEXICONS.items():
        lexicon_set = set(lexicon)
        scores[theme] = sum(1 for token in tokens if token in lexicon_set)

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    positive = [item for item in ranked if item[1] > 0]

    if positive:
        selected = [item[0] for item in positive[:3]]
        # Keep one representative phrase from each dominant thread so a
        # high-frequency vocabulary cluster cannot erase the other themes.
        phrase_set = []
        for theme_name in selected:
            phrase = _THEME_PHRASES[theme_name][0]
            if phrase not in phrase_set:
                phrase_set.append(phrase)
        if len(phrase_set) < 3:
            for phrase in _THEME_PHRASES[selected[0]][1:]:
                if phrase not in phrase_set:
                    phrase_set.append(phrase)
                if len(phrase_set) == 3:
                    break
        theme_name = "+".join(selected)
        phrase_set = phrase_set[:3]
    else:
        frequent = Counter(tokens).most_common(3)
        words = [word.upper() for word, _ in frequent]
        while len(words) < 3:
            words.append(("REFLECTION", "ATTENTION", "MEANING")[len(words)])
        theme_name = "lexical_reflection"
        phrase_set = words[:3]

    territories = [
        template.format(p=phrase_set[0], q=phrase_set[1], r=phrase_set[2])
        for template in _TERRITORY_TEMPLATES
    ]

    return {
        "name": theme_name,
        "phrases": phrase_set,
        "territories": territories,
        "motifs": list(_MOTIF_TEMPLATES),
        "source": "participant_turns_post_session",
        "turn_count": len(texts),
        "scores": dict(scores),
    }
