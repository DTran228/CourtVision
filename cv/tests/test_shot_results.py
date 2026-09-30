"""Session totals must preserve unknowns and the timestamp definition."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from shot_results import build_session


def event(number, outcome):
    return {"candidate_id": number, "outcome": outcome, "start_seconds": 1,
            "crossing_frame": 60, "reason": "Synthetic test"}


class ResultTests(unittest.TestCase):
    def test_empty_has_no_fg_percentage(self):
        self.assertIsNone(build_session({"fps": 30, "candidates": []})["fg_percent"])

    def test_known_outcomes_produce_counts_and_crossing_timestamp(self):
        result = build_session({"fps": 30, "candidates": [event(1, "possible_make"), event(2, "possible_miss")]})
        self.assertEqual((result["attempt_candidates"], result["makes"], result["misses"]), (2, 1, 1))
        self.assertEqual(result["fg_percent"], 50)
        self.assertEqual(result["events"][0]["timestamp"], 2)
        self.assertTrue(result["events"][0]["provisional"])

    def test_unknown_does_not_become_miss_or_disappear_from_denominator(self):
        result = build_session({"fps": 30, "candidates": [event(1, "possible_make"), event(2, "unknown")]})
        self.assertEqual(result["unknown"], 1)
        self.assertEqual(result["misses"], 0)
        self.assertIsNone(result["fg_percent"])


if __name__ == "__main__":
    unittest.main()
