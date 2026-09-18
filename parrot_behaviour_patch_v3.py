# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime
import re
import shutil
import py_compile
import sys

TARGET = Path(r"C:\freeing_the_parrot\scripts\interface_server.py")

if not TARGET.exists():
    print(f"ERROR: File not found: {TARGET}")
    sys.exit(1)

source = TARGET.read_text(encoding="utf-8")

# SAFETY: backup first.
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = TARGET.with_name(
    f"{TARGET.stem}.backup_{stamp}{TARGET.suffix}"
)
shutil.copy2(TARGET, backup)
print(f"BACKUP: {backup}")

# ------------------------------------------------------------
# 1. Replace ONLY choose_behaviour().
# The regex stops BEFORE ABSURD_GLITCHES, so that declaration
# is never duplicated.
# ------------------------------------------------------------
new_choose_behaviour = """def choose_behaviour(session):
    \"\"\"
    Choose the next behavioural mode.

    EXPERIENCE CONTRACT
    -------------------
    Turns 1-3 are guaranteed apparent understanding.

    From turn 4 onward, instability becomes increasingly likely.
    The increase is gradual, not a scripted escalation sequence.

    Every answered turn gets a fresh random decision:
        - apparent understanding, OR
        - one randomly selected unstable behaviour.

    Turn number changes probability only. It never dictates the
    identity or order of the next behaviour.
    \"\"\"

    turn = session.get("turn", 0)
    last = session.get("last_behaviour")

    # TRUST WINDOW: FIRST THREE TURNS
    if turn <= 3:
        behaviour = "understanding"

    else:
        # GRADUAL INSTABILITY CURVE
        # Turn 4 = 8%.
        # Each later turn adds 5.5 percentage points.
        # Cap at 70%, so recovery remains possible.
        instability = min(
            0.70,
            0.08 + ((turn - 4) * 0.055)
        )

        if random.random() >= instability:
            behaviour = "understanding"
        else:
            # Independently random unstable behaviour.
            # There is deliberately NO escalation sequence.
            unstable_choices = [
                "socratic",
                "absurd",
                "memory_loss",
                "system_glitch",
                "help_me",
                "roast",
                "mixed",
            ]

            # Prevent immediate repetition without imposing order.
            candidates = [
                item
                for item in unstable_choices
                if item != last
            ]

            if not candidates:
                candidates = unstable_choices

            behaviour = random.choice(candidates)

    session["last_behaviour"] = behaviour
    session.setdefault("behaviour_history", []).append(behaviour)
    session["behaviour_history"] = session["behaviour_history"][-12:]

    return behaviour


"""

pattern = re.compile(
    r"(?ms)^def choose_behaviour\(session\):.*?(?=^ABSURD_GLITCHES = \[)"
)

source, count = pattern.subn(
    lambda _match: new_choose_behaviour,
    source,
    count=1,
)

if count != 1:
    print(
        "ERROR: Could not locate exactly one choose_behaviour() block. "
        "No source changes were written."
    )
    sys.exit(1)

print("PATCHED: choose_behaviour()")

# ------------------------------------------------------------
# 2. Fix the browser ReferenceError:
#    rasaClass is not defined.
# ------------------------------------------------------------
old_rasa = '"rasa-detected rasa-" + rasaClass'
new_rasa = '"rasa-detected rasa-" + rasa.toLowerCase()'

rasa_count = source.count(old_rasa)

if rasa_count:
    source = source.replace(old_rasa, new_rasa)
    print(f"FIXED: rasaClass ReferenceError ({rasa_count} occurrence)")
else:
    print("INFO: rasaClass expression not present; no frontend fix needed.")

# ------------------------------------------------------------
# 3. Make primary Rasa common to every regular response.
# ------------------------------------------------------------
old_parts = """    parts = []

    # ========================================================
    # VALIDATION
"""

new_parts = """    primary = analysis.get(
        "primary_rasa",
        "Shanta"
    )

    parts = [
        f"I detected {primary.upper()}."
    ]

    # ========================================================
    # VALIDATION
"""

parts_count = source.count(old_parts)

if parts_count == 1:
    source = source.replace(old_parts, new_parts, 1)
    print("FIXED: primary Rasa now enters every regular response")
elif parts_count == 0:
    print("WARNING: common response insertion point not found; Rasa placement unchanged.")
else:
    print(f"ERROR: found {parts_count} response insertion points; refusing to guess.")
    print(f"RESTORING BACKUP: {backup}")
    shutil.copy2(backup, TARGET)
    sys.exit(1)

# Remove the known branch-local duplicate.
local_rasa_block = """        parts.append(
            f"I detected {primary.upper()}."
        )


"""

local_count = source.count(local_rasa_block)

if local_count:
    source = source.replace(local_rasa_block, "", local_count)
    print(f"REMOVED: duplicate branch-local Rasa lines ({local_count})")
else:
    print("INFO: no duplicate branch-local Rasa block found.")

# ------------------------------------------------------------
# 4. Write, compile, restore automatically if compilation fails.
# ------------------------------------------------------------
TARGET.write_text(source, encoding="utf-8", newline="")
print(f"UPDATED: {TARGET}")

try:
    py_compile.compile(str(TARGET), doraise=True)
except Exception as exc:
    print("FAIL: Python syntax check")
    print(exc)
    print(f"RESTORING BACKUP: {backup}")
    shutil.copy2(backup, TARGET)
    sys.exit(1)

print("PASS: Python syntax check")
print("PATCH COMPLETE")
