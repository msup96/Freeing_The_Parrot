import collections

from interface_server import choose_behaviour


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
    "banana",
}


def make_session(substantive_turns):
    """
    Construct the minimum realistic behavioural state required
    by choose_behaviour().

    The first three substantive interactions have already consumed
    the understanding window.
    """
    return {
        "substantive_turns": substantive_turns,
        "understanding_turns": 3,
        "chaos_count": 0,
        "last_behaviour": None,
    }


def sample_behaviour(substantive_turns, samples=5000):
    results = []

    for _ in range(samples):
        session = make_session(substantive_turns)
        results.append(choose_behaviour(session))

    return results


def test_first_three_substantive_interactions_are_understanding():
    for _ in range(1000):
        session = {
            "substantive_turns": 0,
            "understanding_turns": 0,
            "chaos_count": 0,
            "last_behaviour": None,
        }

        assert choose_behaviour(session) == "understanding"
        assert session["understanding_turns"] == 1

        assert choose_behaviour(session) == "understanding"
        assert session["understanding_turns"] == 2

        assert choose_behaviour(session) == "understanding"
        assert session["understanding_turns"] == 3


def test_behaviour_outputs_are_allowed():
    for substantive_turns in range(1, 51):
        results = sample_behaviour(
            substantive_turns,
            samples=200,
        )

        unexpected = set(results) - ALLOWED

        assert not unexpected, (
            f"Substantive turn {substantive_turns} produced "
            f"unexpected behaviours: {sorted(unexpected)}"
        )


def test_chaos_probability_matches_current_contract():
    samples = 5000

    for substantive_turns in range(4, 16):
        results = sample_behaviour(
            substantive_turns,
            samples=samples,
        )

        counts = collections.Counter(results)
        observed_chaos = (
            1.0 - counts["understanding"] / samples
        )

        expected_chaos = min(
            0.75,
            0.35
            + (
                max(0, substantive_turns - 4)
                * 0.08
            ),
        )

        assert abs(
            observed_chaos - expected_chaos
        ) <= 0.025, (
            f"Substantive turn {substantive_turns}: "
            f"expected chaos ~{expected_chaos:.1%}, "
            f"observed {observed_chaos:.1%}"
        )


def test_chaos_probability_does_not_drop_sharply():
    samples = 5000
    observed = {}

    for substantive_turns in range(4, 16):
        results = sample_behaviour(
            substantive_turns,
            samples=samples,
        )

        counts = collections.Counter(results)

        observed[substantive_turns] = (
            1.0
            - counts["understanding"] / samples
        )

    turns = sorted(observed)

    for previous, current in zip(turns, turns[1:]):
        assert not (
            observed[current] + 0.03
            < observed[previous]
        ), (
            f"Chaos probability dropped too sharply: "
            f"turn {previous}={observed[previous]:.1%}, "
            f"turn {current}={observed[current]:.1%}"
        )


def test_late_recovery_remains_possible():
    for substantive_turns in (10, 15, 20, 30, 50):
        results = sample_behaviour(
            substantive_turns,
            samples=2000,
        )

        assert "understanding" in results, (
            f"Understanding never appeared at "
            f"substantive turn {substantive_turns}."
        )


def test_unstable_behaviour_does_not_immediately_repeat():
    for _ in range(1000):
        session = make_session(15)
        previous = None

        for _ in range(20):
            current = choose_behaviour(session)

            if (
                previous not in (None, "understanding")
                and current == previous
                and current != "understanding"
            ):
                raise AssertionError(
                    "Immediate repeated unstable behaviour "
                    f"detected: {current}"
                )

            previous = current
