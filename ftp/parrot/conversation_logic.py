"""Live conversational agency for THE PARROT.

This module decides how the Parrot participates in a live conversation.
It reads only the current turn plus bounded conversational context.
It never uses Silent Reader data, hidden profiles, or post-session analysis.
"""

from __future__ import annotations

import re
from typing import Sequence

DIRECT_MOVE = "answer"
QUESTION_MOVE = "ask"
REFLECTION_MOVES = ("reflect", "acknowledge", "clarify", "continue")
ALL_MOVES = frozenset({DIRECT_MOVE, QUESTION_MOVE, *REFLECTION_MOVES})

GLITCH_BEHAVIOURS = frozenset({
    "absurd", "memory_loss", "system_glitch", "help_me", "banana",
    "binary", "sarcasm", "judgment", "stupidity", "irrelevant", "roast", "mixed",
})

_GENERIC_OPENERS = (
    "you seem", "it sounds like", "there is a sense", "you appear",
    "you may be", "it seems as though", "you are looking", "it feels like", "you sound",
)

_STOPWORDS = frozenset({
    "about", "after", "again", "also", "because", "before", "been", "being",
    "between", "could", "does", "doing", "done", "from", "have", "having",
    "here", "into", "just", "like", "more", "most", "much", "need", "only",
    "really", "same", "something", "that", "their", "them", "then", "there",
    "these", "they", "this", "those", "through", "very", "want", "what",
    "when", "where", "which", "while", "with", "would", "your", "you",
    "feel", "feeling", "felt", "think", "thought", "know", "knew", "say",
    "saying", "tell", "told", "make", "made", "makes", "trying", "still",
})

_TOPIC_PATTERNS = (
    ("pattern", ("pattern", "patterns", "behaviour", "behavior", "repeats", "repeat")),
    ("relationship", ("relationship", "relationships", "partner", "person", "people", "used", "loved")),
    ("reaction", ("reaction", "reactions", "respond", "response", "anger", "angry", "withdraw")),
    ("understanding", ("understand", "understanding", "make sense", "clarity", "guidance", "perspective")),
    ("trust", ("trust", "trusted", "believe", "belief", "confidence")),
    ("choice", ("choice", "choose", "decision", "decide", "unsure", "uncertain")),
    ("weight", ("heavy", "weight", "tiring", "tired", "exhausted", "drained", "overwhelmed")),
    ("change", ("change", "changed", "changing", "different", "moving", "leaving", "ending")),
    ("work", ("work", "project", "design", "career", "job", "study", "research", "deadline")),
)

_QUESTIONS = {
    "pattern": (
        "What repeats most clearly — what they do, what you do, or what you expect will happen?",
        "When you call it a pattern, which part keeps happening in almost the same shape?",
        "What is the first thing you notice when that pattern starts again?",
    ),
    "relationship": (
        "What happens in the moments when you feel used rather than loved?",
        "What are you trying to understand about that person, exactly?",
        "What keeps pulling your attention back to the relationship?",
    ),
    "reaction": (
        "When the reaction starts, what do you usually do first?",
        "Which part is harder to catch in the moment — the feeling or what you do with it?",
        "What would you notice just before you react the way you usually do?",
    ),
    "understanding": (
        "What part of it is hardest to make sense of?",
        "Do you want me to help sort the possibilities, or challenge your read of it?",
        "What would clarity actually look like here?",
    ),
    "trust": (
        "What would make that trust feel earned rather than assumed?",
        "What makes you believe that interpretation, and what makes you doubt it?",
        "Which part of this feels hardest to trust?",
    ),
    "choice": (
        "What part of the choice are you actually stuck on?",
        "What are the two possibilities you keep moving between?",
        "What would make the decision feel less like a test?",
    ),
    "weight": (
        "What part of this is heaviest for you right now?",
        "Is the weight coming more from what happened, or from what you keep doing with it afterward?",
        "What would feel a little lighter without pretending the problem is solved?",
    ),
    "change": (
        "What changed first — the situation, your view of it, or the way you responded?",
        "What are you finding hardest about the transition itself?",
        "What are you hoping will be different on the other side of this?",
    ),
    "work": (
        "What part of the work is actually difficult, rather than merely demanding?",
        "What are you trying to make work here — the task, the outcome, or your relationship to it?",
        "What would count as enough progress for today?",
    ),
}
_DEFAULT_QUESTIONS = (
    "What part of that matters most to you right now?",
    "Where does the knot feel tightest?",
    "What would you like me to understand before I answer?",
)
_REFLECTIONS = {
    "pattern": (
        "You are not only looking at what happened; you are trying to see the repetition underneath it.",
        "The interesting part may be less the individual incident and more what keeps returning around it.",
        "I think the word you chose matters: pattern. That suggests this is not only about one moment.",
    ),
    "relationship": (
        "There is a difference between understanding someone and having your reaction to them under control. The two do not always arrive together.",
        "You can understand another person quite well and still have no idea what to do with what they bring out in you.",
        "This sounds less like a hunt for a verdict and more like an attempt to understand the space between two people.",
    ),
    "reaction": (
        "The reaction seems to be part of the problem you actually want to work on, not just an after-effect.",
        "Knowing what triggered you is one thing. Catching what happens next is another.",
        "It may be useful to separate the event from the chain of things that happens inside you afterward.",
    ),
    "understanding": (
        "You are asking for something more useful than a polished answer. You want a way to look at it.",
        "The missing piece is not information so much as a clearer frame for what is already in front of you.",
        "You want perspective without having it handed to you as a verdict.",
    ),
    "trust": (
        "You are weighing not only what happened, but whether your reading of it deserves to be trusted.",
        "There is a difference between doubt that protects you and doubt that simply keeps the question alive.",
        "The harder question may be what evidence would actually be enough for you.",
    ),
    "choice": (
        "This sounds like a decision that keeps becoming a referendum on whether you can trust yourself.",
        "The problem may be less the number of options and more what each option seems to say about you.",
        "You are trying to choose while also trying to make the uncertainty disappear.",
    ),
    "weight": (
        "The heaviness seems to be coming from more than one place.",
        "Some things are tiring because they are difficult; others are tiring because they keep asking to be revisited.",
        "You are carrying both the thing itself and the work of making sense of it.",
    ),
    "change": (
        "Part of the difficulty seems to be that the old way of reading the situation no longer fits.",
        "Change has a habit of making familiar explanations feel suddenly unreliable.",
        "You are trying to work out what still holds when the situation itself has shifted.",
    ),
    "work": (
        "The task is one thing. The meaning you are attaching to the task is another.",
        "This does not sound like a problem of effort alone.",
        "You are trying to get the work done without letting it become the measure of everything else.",
    ),
}
_DEFAULT_REFLECTIONS = (
    "I think there is more in that sentence than the surface answer.",
    "You have given me something concrete to work with. Let us stay with that instead of rushing to a verdict.",
    "That gives the conversation somewhere real to go.",
)
_DIRECT_QUESTION_ANSWERS = {
    "pattern": (
        "Look for a sequence, not a label: what happened, what you did, what followed, and what keeps recurring.",
        "Write down a few instances side by side. The useful pattern is usually in what stays constant.",
    ),
    "relationship": (
        "Start with one concrete interaction. Separate what they did from what you inferred and what you did next.",
        "Take one moment at a time. We can distinguish their behaviour from the story your mind built around it.",
    ),
    "reaction": (
        "Catch the few seconds before the reaction: what happened, what you noticed, and the first thing you did.",
        "Track the sequence before judging the reaction. The gap between trigger and response is useful information.",
    ),
    "understanding": (
        "Separate what you know happened from the story you are building around it. Then we can test each part.",
        "Start with the concrete facts, then add your interpretation. Mixing the two makes the problem harder to see.",
    ),
    "trust": (
        "Ask what evidence would make you trust that interpretation more — and what would make you change it.",
        "Give the belief a test: what supports it, what weakens it, and what would count as enough evidence?",
    ),
    "choice": (
        "Name the actual options and what each one costs. Uncertainty becomes easier to hold when it has edges.",
        "Put the choices on the table without deciding yet. The trade-offs usually become clearer once they are visible.",
    ),
    "weight": (
        "Separate what needs action from what simply needs to be carried for a while.",
        "Start by deciding which part is actionable today. The rest can stay unresolved for a moment.",
    ),
    "change": (
        "Put the old version and the current version side by side. The gap tells us where to look.",
        "Name what changed and what did not. That usually tells us more than trying to explain the whole transition at once.",
    ),
    "work": (
        "Pick the concrete problem first; we can leave the larger meaning until after the immediate part is clearer.",
        "Name the next useful outcome, not the entire mountain. Then we can see what the real obstacle is.",
    ),
    "default": (
        "Start with the specific thing that happened. We can build the larger picture from there.",
        "Let us keep it concrete first. One example is usually more useful than a theory about all of them.",
    ),
}

def response_mode_for_behaviour(behaviour: str | None) -> str:
    return "glitch" if str(behaviour or "") in GLITCH_BEHAVIOURS else "normal"

def glitch_severity_for_behaviour(behaviour: str | None, intensity: str | None) -> str:
    if str(behaviour or "") == "banana":
        return "low"
    if str(intensity or "") == "high":
        return "high"
    if str(intensity or "") == "moderate":
        return "moderate"
    return "low" if response_mode_for_behaviour(behaviour) == "glitch" else "none"

def content_words(text: str) -> set[str]:
    return {w for w in (re.sub(r"^[^\w'-]+|[^\w'-]+$", "", x.lower()) for x in str(text or "").split())
            if len(w) >= 4 and w not in _STOPWORDS}

def is_direct_question(text: str) -> bool:
    t = str(text or "").strip()
    return bool(t) and ("?" in t or re.match(
        r"^(what|why|how|when|where|who|whom|which|can|could|would|should|is|are|was|were|do|does|did|will)\b",
        t, re.I,
    ))

def is_correction_or_complaint(text: str) -> bool:
    t = str(text or "").lower()
    return any(x in t for x in (
        "you are repeating", "you're repeating", "you keep repeating",
        "i do not understand", "i don't understand", "that is not what i said",
        "that's not what i said", "what are you doing", "what is going on",
        "what's going on", "stop doing that", "can we actually talk",
        "real conversation", "you sound like a machine",
    ))

def topic_key(text: str) -> str:
    t = str(text or "").lower()
    for key, patterns in _TOPIC_PATTERNS:
        if any(p in t for p in patterns):
            return key
    return "default"

def select_contextual_question(text: str, *, recent_questions: Sequence[str] = ()) -> str | None:
    used = {str(x).strip() for x in recent_questions}
    for q in _QUESTIONS.get(topic_key(text), _DEFAULT_QUESTIONS):
        if q not in used:
            return q
    for q in _DEFAULT_QUESTIONS:
        if q not in used:
            return q
    return None

def choose_conversation_plan(text: str, *, turn_index: int, behaviour: str,
                             last_move: str | None = None,
                             recent_questions: Sequence[str] = (),
                             recent_replies: Sequence[str] = (),
                             roll: float = 0.0) -> dict[str, object]:
    del recent_replies
    if is_correction_or_complaint(text):
        move, hint = "repair", None
    elif is_direct_question(text):
        move, hint = DIRECT_MOVE, None
    elif turn_index >= 3 and last_move != QUESTION_MOVE and roll < 0.55:
        hint = select_contextual_question(text, recent_questions=recent_questions)
        move = QUESTION_MOVE if hint else "reflect"
    elif last_move:
        choices = [m for m in REFLECTION_MOVES if m != last_move]
        idx = int(max(0, min(0.999999, roll)) * len(choices))
        move, hint = choices[idx], None
    else:
        move, hint = "reflect", None
    return {"conversation_move": move, "question_hint": hint}

def is_response_repetitive(text: str, recent_replies: Sequence[str] = ()) -> bool:
    t = " ".join(str(text or "").lower().split())
    if not t:
        return True
    for opener in _GENERIC_OPENERS:
        if t.startswith(opener) and any(
            " ".join(str(r or "").lower().split()).startswith(opener)
            for r in recent_replies[-3:]
        ):
            return True
    words = content_words(t)
    if len(words) >= 5:
        for reply in recent_replies[-3:]:
            prior = content_words(reply)
            if prior and len(words & prior) / max(1, len(words | prior)) >= 0.68:
                return True
    return any(t == " ".join(str(r or "").lower().split()) for r in recent_replies[-3:])

def render_conversation_response(text: str, *, move: str,
                                 question_hint: str | None = None,
                                 recent_replies: Sequence[str] = (),
                                 roll: float = 0.0) -> str:
    key = topic_key(text)
    idx = lambda n: int(max(0, min(0.999999, roll)) * n)
    if move == "repair":
        options = (
            "Fair point. I was circling the sentence instead of talking to you.",
            "Yes. I slipped into pattern-reading instead of staying in the conversation.",
            "You're right. That stopped sounding like a conversation.",
        )
        base = options[idx(3)]
    elif move == DIRECT_MOVE:
        answers = _DIRECT_QUESTION_ANSWERS.get(key, _DIRECT_QUESTION_ANSWERS["default"])
        base = answers[idx(len(answers))]
    elif move == QUESTION_MOVE:
        refs = _REFLECTIONS.get(key, _DEFAULT_REFLECTIONS)
        base = refs[idx(len(refs))]
        if question_hint:
            base = f"{base} {question_hint}"
    elif move == "acknowledge":
        options = ("Yes. I am with you.", "Right. I am following that.",
                   "Okay. That gives me something concrete to work with.", "I have that.")
        base = options[idx(4)]
    elif move == "clarify":
        base = "Let me keep that specific rather than turning it into a larger theory."
    else:
        refs = _REFLECTIONS.get(key, _DEFAULT_REFLECTIONS)
        base = refs[idx(len(refs))]
    if is_response_repetitive(base, recent_replies):
        base = "Let me stay with the thing you actually said."
        if move == QUESTION_MOVE and question_hint:
            base = f"{base} {question_hint}"
    return base.strip()

def count_questions(text: str) -> int:
    return str(text or "").count("?")
