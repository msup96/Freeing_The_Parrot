"""Measure how predictable the Parrot's live behaviour is across many simulated sessions.

Usage:  python audit_parrot_variability.py [sessions] [turns]

Runs the real Behaviour Director twice: with the original fixed arc and with a
per-session temperament, then prints per-turn predictability so the difference can
be cited (for example in a seminar write-up). The simulation replays behaviour
selection only; it does not call any language model.
"""

from __future__ import annotations

import collections
import math
import random
import sys

from ftp.parrot.director import BehaviourDirector
from ftp.session.coordinator import SessionCoordinator
from ftp.session.states import SessionState

NAV = {"primary_rasa": "Shanta", "rasa_scores": {}, "sentiment": {}}


def _session(varied: bool, seed: int, turns: int) -> list[str]:
    rng = random.Random(seed)
    coord = SessionCoordinator(f"audit-{seed}")
    coord.start()
    coord.advance(SessionState.LIVE_CONVERSATION)
    if varied:
        coord.director_state.randomize_temperament(random.Random(seed + 10_000))
    sequence = []
    for turn in range(1, turns + 1):
        instruction = BehaviourDirector.decide(
            coord, turn_index=turn, turn_text="x", navarasa_result=NAV, rng=rng
        )
        sequence.append(instruction["behaviour"])
    return sequence


def _report(label: str, sequences: list[list[str]], turns: int) -> None:
    n = len(sequences)
    print(f"\n{label}")
    print("turn | share 'understanding' | entropy (bits)")
    for t in range(turns):
        counts = collections.Counter(s[t] for s in sequences)
        entropy = -sum((v / n) * math.log2(v / n) for v in counts.values())
        print(f"{t + 1:>4} | {counts['understanding'] / n:>21.2f} | {entropy:>6.2f}")
    first_calm = [next((i for i, b in enumerate(s) if b != "understanding"), turns) for s in sequences]
    print(f"first non-understanding turn: {len(set(first_calm))} distinct values, "
          f"most common used by {collections.Counter(first_calm).most_common(1)[0][1] / n:.0%} of sessions")


def main() -> None:
    sessions = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    turns = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    fixed = [_session(False, i, turns) for i in range(sessions)]
    varied = [_session(True, i, turns) for i in range(sessions)]
    _report("ORIGINAL (same trust window and curve for everyone)", fixed, turns)
    _report("PER-SESSION TEMPERAMENT", varied, turns)


if __name__ == "__main__":
    main()
