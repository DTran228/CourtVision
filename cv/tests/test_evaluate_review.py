"""Small, model-free tests for review counting and label alignment."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evaluate_review import load_review, score_threshold


class ThresholdTests(unittest.TestCase):
    def test_cutoff_includes_equal_score_and_counts_lost_correct_boxes(self):
        candidates = [
            {"confidence": 0.4, "correct": True},
            {"confidence": 0.3, "correct": True},
            {"confidence": 0.5, "correct": False},
        ]
        self.assertEqual(score_threshold(candidates, 0.4), {
            "kept_correct": 1, "kept_incorrect": 1, "removed_correct": 1,
            "precision": 0.5, "retention": 0.5,
        })

    def test_no_surviving_predictions_has_undefined_precision(self):
        score = score_threshold([{"confidence": 0.3, "correct": True}], 0.9)
        self.assertIsNone(score["precision"])
        self.assertEqual(score["retention"], 0)

    def test_no_correct_candidates_has_undefined_retention(self):
        score = score_threshold([{"confidence": 0.5, "correct": False}], 0.25)
        self.assertEqual(score["precision"], 0)
        self.assertIsNone(score["retention"])


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.predictions = Path(self.directory.name) / "predictions.jsonl"
        self.labels = Path(self.directory.name) / "review.json"
        # Hoop predictions must not change basketball candidate indices.
        rows = [{"frame": number, "detections": [
            {"class": "hoop", "confidence": 0.9},
            {"class": "basketball", "confidence": 0.4},
        ]} for number in range(3)]
        self.predictions.write_text("\n".join(json.dumps(row) for row in rows))
        self.review = {
            "prediction_sha256": hashlib.sha256(self.predictions.read_bytes()).hexdigest(),
            "minimum_confidence": 0.25,
            "frames": [
                {"frame": 0, "split": "tune", "status": "reviewed",
                 "candidates": [{"index": 0, "correct": True}]},
                {"frame": 1, "split": "tune", "status": "uncertain", "candidates": []},
                {"frame": 2, "split": "check", "status": "reviewed",
                 "candidates": [{"index": 0, "correct": False}]},
            ],
        }

    def save_labels(self):
        self.labels.write_text(json.dumps(self.review), encoding="utf-8")

    def test_only_selected_split_and_reviewed_frames_are_scored(self):
        self.save_labels()
        candidates, reviewed, skipped, minimum = load_review(self.predictions, self.labels, "tune")
        self.assertEqual(candidates, [{"confidence": 0.4, "correct": True}])
        self.assertEqual((reviewed, skipped, minimum), (1, 1, 0.25))

    def test_changed_prediction_file_is_rejected(self):
        self.save_labels()
        self.predictions.write_text("changed")
        with self.assertRaisesRegex(ValueError, "Prediction file changed"):
            load_review(self.predictions, self.labels, "tune")

    def test_missing_candidate_judgment_is_rejected(self):
        self.review["frames"][0]["candidates"] = []
        self.save_labels()
        with self.assertRaisesRegex(ValueError, "Each ball candidate"):
            load_review(self.predictions, self.labels, "tune")


if __name__ == "__main__":
    unittest.main()
