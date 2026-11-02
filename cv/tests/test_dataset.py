import copy
import unittest

from cv.src.dataset import score_clip, validate_dataset, track_selection_accuracy


def label():
    return {"schema_version": 1, "video_sha256": "a"*64, "recording_session_id": "synthetic-session",
            "split": "dev", "duration_seconds": 10, "reviewer": "synthetic test fixture",
            "review_status": "provisional", "fully_reviewed": True, "reviewed_intervals": [[0, 10]],
            "attempts": [{"id": "a", "contact_window": [2, 2.2], "outcome": "made", "visibility_tags": [], "occlusion_tags": []},
                         {"id": "b", "contact_window": [5, 5.2], "outcome": "missed", "visibility_tags": [], "occlusion_tags": []}]}


class DatasetTests(unittest.TestCase):
    def test_duplicate_miss_unknown_and_false_positive_have_correct_denominators(self):
        events = [{"id": str(i), "contact_seconds": t, "outcome": o}
                  for i, (t, o) in enumerate([(2.1, "unknown"), (2.1, "made"), (8, "missed")])]
        result = score_clip(label(), events)
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (1, 2, 1))
        self.assertEqual(result["precision"], 1/3)
        self.assertEqual(result["recall"], 1/2)
        self.assertEqual(result["correct_over_all_labeled"], 0)
        self.assertEqual(result["confusion"]["made"]["unknown"], 1)
        self.assertEqual(result["unknown_rate"], 1/3)
        self.assertEqual(result["false_positives_per_minute"], 12)

    def test_session_split_leakage_rejected(self):
        a = label()
        b = {**copy.deepcopy(a), "video_sha256": "b"*64, "split": "test"}
        with self.assertRaisesRegex(ValueError, "leaks"):
            validate_dataset([a, b])

    def test_partial_review_excludes_unreviewed_predictions(self):
        a = label()
        a.update(fully_reviewed=False, reviewed_intervals=[[1, 6]])
        r = score_clip(a, [{"id": "outside", "contact_seconds": 8, "outcome": "made"}])
        self.assertEqual(r["fp"], 0)
        self.assertEqual(r["fn"], 2)
        self.assertIsNone(r["false_positives_per_minute"])

    def test_negative_interval_and_fixed_tolerance(self):
        a = label()
        a["attempts"] = []
        self.assertEqual(score_clip(a, [{"id": "x", "contact_seconds": 3, "outcome": "made"}])["fp"], 1)
        e = [{"id": "x", "contact_seconds": 2.34, "outcome": "made"}]
        self.assertEqual(score_clip(label(), e)["tp"], 1)
        e[0]["contact_seconds"] = 2.36
        self.assertEqual(score_clip(label(), e)["tp"], 0)

    def test_frame_selection_includes_missing(self):
        rows = [{"video_sha256": "a"*64, "frame": i, "expected_detection_id": 1,
                 "selected_detection_id": selected} for i, selected in enumerate([1, None, 2])]
        self.assertEqual(track_selection_accuracy(rows)["accuracy"], 1/3)
