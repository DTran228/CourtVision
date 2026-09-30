"""Check attempt matching without requiring a model or local footage."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evaluate_shots import compare_attempts, validate_review


def attempt(outcome="made"):
    return {"id": 1, "window": [10, 30], "visible_ball_window": [20, 25], "outcome": outcome}


def candidate(number=1, frame=20, outcome="possible_make"):
    return {"candidate_id": number, "start_frame": frame, "outcome": outcome}


class ShotEvaluationTests(unittest.TestCase):
    def test_no_predictions_reports_missed_attempt(self):
        result = compare_attempts([attempt()], [[10, 30]], [])
        self.assertEqual(result["matched_attempts"], 0)
        self.assertEqual(result["missed_attempt_ids"], [1])

    def test_matching_outcome_and_duplicate_are_separate(self):
        result = compare_attempts([attempt()], [[10, 30]], [candidate(), candidate(2, 21)])
        self.assertEqual(result["matched_attempts"], 1)
        self.assertTrue(result["matches"][0]["outcome_agrees"])
        self.assertEqual(result["extra_candidates_in_reviewed_windows"], [2])

    def test_unknown_prediction_is_not_a_correct_make(self):
        result = compare_attempts([attempt()], [[10, 30]], [candidate(outcome="unknown")])
        self.assertEqual(result["matched_attempts"], 1)
        self.assertFalse(result["matches"][0]["outcome_agrees"])

    def test_wrong_outcome_is_recorded(self):
        result = compare_attempts([attempt("missed")], [[10, 30]], [candidate()])
        self.assertFalse(result["matches"][0]["outcome_agrees"])

    def test_unknown_review_does_not_score_outcome(self):
        result = compare_attempts([attempt("unknown")], [[10, 30]], [candidate()])
        self.assertIsNone(result["matches"][0]["outcome_agrees"])

    def test_unreviewed_times_are_not_false_alarms(self):
        result = compare_attempts([attempt()], [[10, 30]], [candidate(frame=50)])
        self.assertEqual(result["unreviewed_candidate_ids"], [1])
        self.assertEqual(result["extra_candidates_in_reviewed_windows"], [])

    def test_crossing_time_takes_precedence_over_start(self):
        prediction = {**candidate(frame=0), "crossing_frame": 20}
        result = compare_attempts([attempt()], [[10, 30]], [prediction])
        self.assertEqual(result["matched_attempts"], 1)

    def test_no_shot_review_window_can_record_a_false_alarm(self):
        result = compare_attempts([], [[10, 30]], [candidate()])
        self.assertEqual(result["extra_candidates_in_reviewed_windows"], [1])

    def test_overlapping_review_windows_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            validate_review({"frames": 50, "reviewed_windows": [[0, 20], [20, 40]], "attempts": []})

    def test_visibility_window_cannot_extend_past_attempt(self):
        label = {**attempt(), "visible_ball_window": [20, 40]}
        with self.assertRaisesRegex(ValueError, "Visibility check"):
            validate_review({"frames": 50, "reviewed_windows": [[0, 49]], "attempts": [label]})


if __name__ == "__main__":
    unittest.main()
