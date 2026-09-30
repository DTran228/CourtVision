"""Verify motion recovery's evidence gates without using real video labels."""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from recovery import MotionPath, NearHoopRecovery


def point(x, y):
    return {"relative": [x, y], "bbox": [10, 10, 20, 20]}


class MotionRecoveryTests(unittest.TestCase):
    def start_path(self):
        path = MotionPath(30)
        self.assertIsNone(path.update(0, [point(0, -0.7)]))
        self.assertIsNone(path.update(1, [point(0, -0.45)]))
        self.assertIsNotNone(path.update(2, [point(0, -0.2)]))
        return path

    def test_requires_three_descending_observations(self):
        self.start_path()

    def test_stationary_color_does_not_start_path(self):
        path = MotionPath(30)
        for i in range(10):
            self.assertIsNone(path.update(i, [point(0, -0.2)]))

    def test_missing_frame_does_not_emit_prediction(self):
        path = self.start_path()
        self.assertIsNone(path.update(3, []))
        self.assertIsNotNone(path.update(4, [point(0, 0.3)]))

    def test_precontact_reversal_is_rejected(self):
        path = self.start_path()
        self.assertIsNone(path.update(3, [point(0, -0.7)]))

    def test_rebound_after_contact_can_be_followed(self):
        path = self.start_path()
        self.assertIsNotNone(path.update(3, [point(0, 0.1)]))
        self.assertIsNotNone(path.update(4, [point(0, -0.1)]))

    def test_long_gap_clears_active_path(self):
        path = self.start_path()
        for i in range(3, 11):
            self.assertIsNone(path.update(i, []))
        self.assertIsNone(path.last)
        self.assertIsNone(path.update(11, [point(0, 0.1)]))

    def test_static_image_never_emits_ball(self):
        recovery = NearHoopRecovery(30)
        frame = np.full((200, 200, 3), (40, 80, 180), dtype=np.uint8)
        hoop = {"class": "hoop", "confidence": 0.8, "bbox": [80, 80, 120, 120]}
        for _ in range(12):
            self.assertIsNone(recovery.update(frame, [hoop]))

    def test_missing_hoop_clears_background(self):
        recovery = NearHoopRecovery(30)
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        recovery.update(frame, [{"class": "hoop", "confidence": 0.8, "bbox": [80, 80, 120, 120]}])
        self.assertEqual(len(recovery.history), 1)
        self.assertIsNone(recovery.update(frame, []))
        self.assertEqual(len(recovery.history), 0)


if __name__ == "__main__":
    unittest.main()
