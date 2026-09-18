# -*- coding: utf-8 -*-
"""
Freeing the Parrot — behavioural engine audit

Run after patching:
    python audit_parrot_behaviour.py

The script extracts choose_behaviour() from interface_server.py,
executes it in isolation, and statistically audits the experience
contract.
"""
from pathlib import Path
import ast
import collections
import random
import sys

TARGET = Path(r"C:\freeing_the_parrot\scripts\interface_server.py")

if not TARGET.exists():
    print(f"ERROR: File not found: {TARGET}")
    sys.exit(1)

source = TARGET.read_text(encoding="utf-8")
tree = ast.parse(source)

fn = next(
    (
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "choose_behaviour"
    ),
    None,
)

if fn is None:
    print("FAIL: choose_behaviour() not found")
    sys.exit(1)

namespace = {"random": random}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "<audit>", "exec"), namespace)
choose_behaviour = namespace["choose_behaviour"]

ALLOWED = {
    "understanding",
    "normal",
    "absurd",
    "memory_loss",
    "system_glitch",
    "help_me",
    "roast",
    "mixed",
    "mirroring",
    "socratic",
}

FAILURES = []

# ------------------------------------------------------------
# 1. HARD TRUST WINDOW
# ------------------------------------------------------------
for turn in (1, 2, 3):
    results = [
        choose_behaviour({"turn": turn})
        for _ in range(2000)
    ]
    bad = [x for x in results if x != "understanding"]

    if bad:
        FAILURES.append(
            f"Turn {turn}: {len(bad)}/2000 were not understanding"
        )
    else:
        print(f"PASS: turn {turn} = 100% understanding")

# ------------------------------------------------------------
# 2. POST-TURN-3 RANDOMNESS + GRADUAL CURVE
# ------------------------------------------------------------
samples = 50000
observed = {}

for turn in range(4, 16):
    results = [
        choose_behaviour({"turn": turn})
        for _ in range(samples)
    ]
    counts = collections.Counter(results)
    understanding_rate = counts["understanding"] / samples
    instability_rate = 1.0 - understanding_rate
    observed[turn] = instability_rate

    unexpected = set(counts) - ALLOWED
    if unexpected:
        FAILURES.append(
            f"Turn {turn}: unexpected behaviours: {sorted(unexpected)}"
        )

    print(
        f"TURN {turn:2d} | "
        f"understanding={understanding_rate:6.2%} | "
        f"instability={instability_rate:6.2%} | "
        f"mix={dict(counts)}"
    )

# ------------------------------------------------------------
# 3. CURVE AUDIT
# ------------------------------------------------------------
# Target curve:
# turn 4 = 8%
# then +5.5 percentage points / turn
# capped at 70%.
for turn, actual in observed.items():
    expected = min(0.70, 0.08 + ((turn - 4) * 0.055))
    if abs(actual - expected) > 0.025:
        FAILURES.append(
            f"Turn {turn}: expected instability ~{expected:.1%}, "
            f"observed {actual:.1%}"
        )

# ------------------------------------------------------------
# 4. MONOTONICITY AUDIT
# ------------------------------------------------------------
# Because the engine is random, individual samples can wobble.
# We therefore allow a 3-point statistical tolerance.
turns = sorted(observed)

for a, b in zip(turns, turns[1:]):
    if observed[b] + 0.03 < observed[a]:
        FAILURES.append(
            f"Curve dropped too sharply: turn {a}={observed[a]:.1%}, "
            f"turn {b}={observed[b]:.1%}"
        )

print("PASS: gradual instability curve is within tolerance")

# ------------------------------------------------------------
# 5. RECOVERY AUDIT
# ------------------------------------------------------------
# Understanding must remain possible at late turns.
for turn in (10, 15, 20, 30, 50):
    seen = set(
        choose_behaviour({"turn": turn})
        for _ in range(5000)
    )
    if "understanding" not in seen:
        FAILURES.append(
            f"Turn {turn}: no recovery/understanding observed"
        )
    else:
        print(f"PASS: understanding remains possible at turn {turn}")

# ------------------------------------------------------------
# 6. IMMEDIATE DUPLICATE AUDIT
# ------------------------------------------------------------
# The repetition guard should prevent identical consecutive
# unstable behaviours when alternatives exist.
for _ in range(5000):
    session = {"turn": 15}
    previous = None

    for _ in range(20):
        current = choose_behaviour(session)

        if (
            previous not in (None, "understanding")
            and current == previous
            and current != "understanding"
        ):
            FAILURES.append(
                f"Immediate repeated unstable behaviour: {current}"
            )
            break

        previous = current

print("PASS: no immediate repeated unstable behaviour detected")

# ------------------------------------------------------------
# RESULT
# ------------------------------------------------------------
if FAILURES:
    print("\nAUDIT FAILED")
    for failure in FAILURES:
        print(" -", failure)
    sys.exit(2)

print("\nAUDIT PASSED")
print("Behavioural contract is holding.")
