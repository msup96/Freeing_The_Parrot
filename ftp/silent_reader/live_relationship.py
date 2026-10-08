"""Live relational signals for FTP 2.0's hidden Silent Reader.

These are interactional observations used only by the Behaviour Director.
They are never placed in Parrot context or sent to the language realizer.
They describe what happened between the participant and the Parrot, not who
the participant is.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from ftp.parrot.continuity import DialogueTurn

_FRACTURES = frozenset({
    "absurd", "memory_loss", "system_glitch", "help_me", "banana",
    "roast", "binary", "sarcasm", "judgment", "stupidity", "irrelevant",
})

_PARROT_CURIOSITY = re.compile(
    r"\b(why did you|why are you|what do you mean|what are you saying|"
    r"what is that supposed to mean|what makes you say|are you doing this|"
    r"why would you|what was that|what the hell was that|what the heck was that|"
    r"are you serious|do you mean)\b",
    re.I,
)

_CORRECTION = re.compile(
    r"\b(you are (speaking|being)|you('?re| are) confusing|"
    r"that doesn'?t make sense|doesn'?t make sense|you'?re not making sense|"
    r"i don'?t understand|i am not able to understand|"
    r"i'?m not able to understand|not able to follow|what do you mean)\b",
    re.I,
)

_REPAIR = re.compile(
    r"\b(anyway|let'?s continue|continue|back to|where were we|"
    r"i'?ll continue|okay,? so|alright,? so|let me continue|"
    r"i still want to|i'?m still here|go on|keep going)\b",
    re.I,
)

_IRRITATION = re.compile(
    r"\b(annoying|irritating|irritated|frustrating|frustrated|"
    r"stupid|ridiculous|nonsense|useless|pointless|bullshit|"
    r"what the fuck|what the hell|shut up|stop it|stop doing)\b",
    re.I,
)

_DISENGAGEMENT = re.compile(
    r"^\s*(okay|ok|fine|whatever|never mind|nevermind|forget it|"
    r"leave it|doesn'?t matter|i'?m done|i am done|i'?m leaving|"
    r"i am leaving|not interested|goodbye|bye)\s*[.!?]*$",
    re.I,
)


def derive_live_relationship_signals(
    turns: Sequence[DialogueTurn],
    *,
    current_text: str,
) -> dict[str, Any]:
    """Observe how the current turn relates to the Parrot's previous turn."""
    text = current_text.strip()
    prior = turns[-1] if turns else None
    previous_behaviour = prior.behaviour if prior else ""
    previous_fracture = previous_behaviour.lower() in _FRACTURES

    parrot_directed = bool(_PARROT_CURIOSITY.search(text))
    correction = bool(_CORRECTION.search(text))
    repair = bool(_REPAIR.search(text))
    irritation = bool(_IRRITATION.search(text))
    disengagement = bool(_DISENGAGEMENT.match(text)) if text else True

    substantive = len(re.findall(r"\b\w+\b", text)) >= 6
    continued_after_fracture = bool(previous_fracture and text and not disengagement)

    # A response can be emotionally negative and still demonstrate strong
    # relational investment if it is specifically about the Parrot.
    delta = 0.0
    if substantive:
        delta += 0.08
    if parrot_directed:
        delta += 0.14
    if repair:
        delta += 0.12
    if continued_after_fracture:
        delta += 0.16
    if correction:
        delta += 0.06
    if irritation and not disengagement:
        delta += 0.04
    if disengagement:
        delta -= 0.20

    trust_delta = 0.0
    if substantive:
        trust_delta += 0.09
    if parrot_directed:
        trust_delta += 0.10
    if repair:
        trust_delta += 0.10
    if continued_after_fracture:
        trust_delta += 0.18
    if irritation and not disengagement:
        trust_delta += 0.03
    if disengagement:
        trust_delta -= 0.18

    return {
        "current_turn_substantive": substantive,
        "parrot_directed": parrot_directed,
        "correction": correction,
        "repair_attempt": repair,
        "irritation": irritation,
        "disengagement": disengagement,
        "previous_fracture": previous_fracture,
        "continued_after_fracture": continued_after_fracture,
        "engagement_delta": round(delta, 4),
        "trust_delta": round(trust_delta, 4),
    }
