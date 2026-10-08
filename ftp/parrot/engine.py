"""FTP 2.0 Parrot Behaviour Engine.

Phase 1A:
Extracted from the existing interface_server.py without
changing the behaviour implementation.
"""

import random


BEHAVIOUR_NAMES = (
    "understanding",
    "absurd",
    "memory_loss",
    "roast",
    "system_glitch",
    "help_me",
    "mixed",
    "mirroring",
    "banana",
    "binary",
    "sarcasm",
    "judgment",
    "stupidity",
    "irrelevant",
)


def choose_behaviour(session):
    """
    Choose the next behavioural mode.

    EXPERIENCE CONTRACT
    -------------------
    The first three actual conversational interactions establish
    perceived understanding.

    From interaction 4 onward, the machine enters a genuinely
    unpredictable behavioural field containing both apparent
    understanding and chaotic behaviours.

    The probability of chaos increases with interaction length,
    but never reaches 100%. Recovery remains possible.

    Behaviour order is never scripted.
    """

    last = session.get("last_behaviour")
    understanding_turns = session.get("understanding_turns", 0)
    chaos_count = session.get("chaos_count", 0)

    # ========================================================
    # PHASE 1: ESTABLISH PERCEIVED UNDERSTANDING
    # ========================================================

    if understanding_turns < 3:
        behaviour = "understanding"

        session["understanding_turns"] = (
            understanding_turns + 1
        )

    else:
        # ====================================================
        # PHASE 2: RANDOM BEHAVIOURAL FIELD
        # ====================================================
        #
        # Chaos becomes increasingly likely after the first
        # three understanding interactions.
        #
        # Approximate chaos probability:
        #
        # Turn 4  -> 35%
        # Turn 5  -> 43%
        # Turn 6  -> 51%
        # Turn 7  -> 59%
        # Turn 8  -> 67%
        # Turn 9+ -> 75%
        #
        # The machine can still recover and appear helpful.
        # ====================================================

        interaction_number = session.get(
    	"substantive_turns",
    	0
	)

        instability = min(
            0.75,
            0.35 + (
                max(0, interaction_number - 4) * 0.08
            )
        )

        if random.random() >= instability:
            behaviour = "understanding"

        else:
            unstable_choices = [
                "absurd",
                "memory_loss",
                "system_glitch",
                "help_me",
                "roast",
                "mixed",
                "mirroring",
                "banana",
            ]

            # Prevent immediate repetition without imposing
            # a prescribed sequence.

            candidates = [
                item
                for item in unstable_choices
                if item != last
            ]

            if not candidates:
                candidates = unstable_choices

            behaviour = random.choice(
                candidates
            )

            # Count only genuinely chaotic behaviours.
            session["chaos_count"] = (
                chaos_count + 1
            )

    # ========================================================
    # BEHAVIOUR MEMORY
    # ========================================================

    session["last_behaviour"] = behaviour

    session.setdefault(
        "behaviour_history",
        []
    ).append(
        behaviour
    )

    session["behaviour_history"] = (
        session["behaviour_history"][-12:]
    )

    return behaviour
