import json
from pathlib import Path

from navarasa_engine import analyse_text


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "golden_navarasa_fixtures.json"


def load_fixtures():
    with FIXTURE_PATH.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def test_golden_navarasa_fixtures():
    for case in load_fixtures():
        result = analyse_text(case["text"])
        expected = case["expected"]

        for key, value in expected.items():
            assert result[key] == value, (
                f"{case['name']}: expected {key}={value!r}, "
                f"got {result[key]!r}"
            )
