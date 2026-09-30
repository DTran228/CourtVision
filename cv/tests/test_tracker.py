"""Test tracking decisions using invented boxes; no YOLO or footage needed."""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tracker import BallTracker
from visualize import draw_track


def ball(x, y=20, confidence=0.5, label="basketball"):
    """Make a small box centered at a chosen point."""
    return {"class": label, "confidence": confidence, "bbox": [x-2, y-2, x+2, y+2]}


class TrackerTests(unittest.TestCase):
    def test_start_uses_confidence_and_ignores_hoops(self):
        tracker = BallTracker(10)
        result = tracker.update([ball(10, confidence=0.3), ball(20, confidence=0.8),
                                 ball(100, confidence=0.99, label="hoop")])
        self.assertEqual(result["center"], [20, 20])
        self.assertEqual(result["track_id"], 1)

    def test_nearest_candidate_beats_a_distant_high_score(self):
        tracker = BallTracker(10)
        tracker.update([ball(20)])
        result = tracker.update([ball(21, confidence=0.3), ball(28, confidence=0.99)])
        self.assertEqual(result["center"], [21, 20])

    def test_far_candidate_cannot_teleport_active_track(self):
        tracker = BallTracker(10)
        tracker.update([ball(20)])
        result = tracker.update([ball(200)])
        self.assertEqual(result["status"], "missing")
        self.assertIsNone(result["center"])
        self.assertIsNone(result["bbox"])
        self.assertEqual(tracker.center, (20, 20))

    def test_short_gap_keeps_identity_and_marks_gap_in_trail(self):
        tracker = BallTracker(10, max_missing=2)
        tracker.update([ball(20)])
        tracker.update([])
        tracker.update([])
        result = tracker.update([ball(25)])
        self.assertEqual(result["track_id"], 1)
        self.assertEqual(result["missing_frames"], 0)
        self.assertEqual([number for number, _ in tracker.trail], [0, 3])

    def test_expiration_clears_trail_then_reacquires_with_new_id(self):
        tracker = BallTracker(10, max_missing=1)
        tracker.update([ball(20)])
        self.assertEqual(tracker.update([])["status"], "missing")
        result = tracker.update([ball(200)])
        self.assertEqual(result["status"], "lost")
        self.assertIsNone(result["track_id"])
        self.assertEqual(len(tracker.trail), 0)
        result = tracker.update([ball(200)])
        self.assertEqual(result["track_id"], 2)
        self.assertEqual(len(tracker.trail), 1)

    def test_zero_gap_expires_on_first_missing_frame(self):
        tracker = BallTracker(10, max_missing=0)
        tracker.update([ball(20)])
        self.assertEqual(tracker.update([])["status"], "lost")

    def test_distance_boundary_is_inclusive_and_trail_is_bounded(self):
        tracker = BallTracker(10, trail_length=2)
        for x in [20, 30, 40]:
            result = tracker.update([ball(x)])
            self.assertEqual(result["track_id"], 1)
        self.assertEqual(len(tracker.trail), 2)

    def test_empty_start_does_not_invent_track(self):
        result = BallTracker(10).update([])
        self.assertEqual(result["status"], "searching")
        self.assertIsNone(result["track_id"])
        self.assertIsNone(result["center"])


class TrailDrawingTests(unittest.TestCase):
    def test_adjacent_observations_are_connected(self):
        image = np.zeros((120, 120, 3), dtype=np.uint8)
        draw_track(image, {"center": None, "track_id": 1, "status": "missing"},
                   [(0, (10, 80)), (1, (90, 80))])
        self.assertEqual(image[80, 50].tolist(), [255, 255, 0])

    def test_missing_interval_is_not_connected(self):
        image = np.zeros((120, 120, 3), dtype=np.uint8)
        draw_track(image, {"center": None, "track_id": 1, "status": "missing"},
                   [(0, (10, 80)), (2, (90, 80))])
        self.assertEqual(image[80, 50].tolist(), [0, 0, 0])


if __name__ == "__main__":
    unittest.main()
