"""Synthetic motion tests verify rules, not real-world shooting accuracy."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shots import ShotAnalyzer

HOOP = {"class": "hoop", "confidence": 0.9, "bbox": [100, 100, 200, 160]}


def observed(y, x=150, track_id=1):
    return {"status": "observed", "track_id": track_id, "center": [x, y]}


class ShotTests(unittest.TestCase):
    def run_path(self, x):
        analyzer = ShotAnalyzer(30)
        events = []
        for frame, y in enumerate([40, 70, 110, 160]):
            _, event = analyzer.update(frame, observed(y, x), [HOOP])
            if event:
                events.append(event)
        return analyzer, events

    def test_aligned_descent_is_only_a_possible_make(self):
        _, events = self.run_path(150)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["outcome"], "possible_make")
        self.assertTrue(events[0]["provisional"])
        self.assertEqual(events[0]["crossing_x_in_hoop_widths"], 0)

    def test_outside_descent_is_possible_miss(self):
        _, events = self.run_path(260)
        self.assertEqual(events[0]["outcome"], "possible_miss")

    def test_edge_crossing_is_unknown(self):
        _, events = self.run_path(210)
        self.assertEqual(events[0]["outcome"], "unknown")

    def test_missing_ball_is_unknown_not_a_miss(self):
        analyzer = ShotAnalyzer(30)
        analyzer.update(0, observed(40), [HOOP])
        analyzer.update(1, observed(70), [HOOP])
        _, event = analyzer.update(2, {"status": "missing"}, [HOOP])
        self.assertEqual(event["outcome"], "unknown")

    def test_missing_hoop_is_unknown(self):
        analyzer = ShotAnalyzer(30)
        analyzer.update(0, observed(40), [HOOP])
        analyzer.update(1, observed(70), [HOOP])
        _, event = analyzer.update(2, observed(110), [])
        self.assertEqual(event["outcome"], "unknown")

    def test_changed_track_cannot_complete_a_shot(self):
        analyzer = ShotAnalyzer(30)
        analyzer.update(0, observed(40), [HOOP])
        analyzer.update(1, observed(70), [HOOP])
        _, event = analyzer.update(2, observed(160, track_id=2), [HOOP])
        self.assertEqual(event["outcome"], "unknown")

    def test_hoop_jump_interrupts_active_candidate(self):
        analyzer = ShotAnalyzer(30)
        analyzer.update(0, observed(40), [HOOP])
        analyzer.update(1, observed(70), [HOOP])
        shifted = {**HOOP, "bbox": [300, 100, 400, 160]}
        _, event = analyzer.update(2, observed(160), [shifted])
        self.assertEqual(event["outcome"], "unknown")

    def test_upward_motion_and_low_dribbling_do_not_start_candidates(self):
        for path in [[160, 110, 70, 40], [300, 320, 280, 300]]:
            analyzer = ShotAnalyzer(30)
            for frame, y in enumerate(path):
                state, event = analyzer.update(frame, observed(y), [HOOP])
                self.assertEqual(state, "waiting")
                self.assertIsNone(event)

    def test_cooldown_prevents_duplicate_event(self):
        analyzer, _ = self.run_path(150)
        for frame in range(4, 20):
            state, event = analyzer.update(frame, observed(70), [HOOP])
            self.assertEqual(state, "cooldown")
            self.assertIsNone(event)

    def test_end_of_video_flushes_unfinished_candidate(self):
        analyzer = ShotAnalyzer(30)
        analyzer.update(0, observed(40), [HOOP])
        analyzer.update(1, observed(70), [HOOP])
        event = analyzer.finish("Video ended.", 1)
        self.assertEqual(event["outcome"], "unknown")
        self.assertIsNone(analyzer.finish("Video ended.", 1))

    def test_candidate_times_out(self):
        analyzer = ShotAnalyzer(10)
        analyzer.update(0, observed(40), [HOOP])
        analyzer.update(1, observed(70), [HOOP])
        for frame in range(2, 22):
            _, event = analyzer.update(frame, observed(70), [HOOP])
        self.assertEqual(event["outcome"], "unknown")
        self.assertIn("timed out", event["reason"])

    def test_crossing_needs_a_later_below_hoop_observation(self):
        analyzer = ShotAnalyzer(30)
        analyzer.update(0, observed(40), [HOOP])
        analyzer.update(1, observed(70), [HOOP])
        state, event = analyzer.update(2, observed(160), [HOOP])
        self.assertEqual(state, "candidate")
        self.assertIsNone(event)
        self.assertEqual(analyzer.finish("Video ended.", 2)["outcome"], "unknown")


class GapAndReboundTests(unittest.TestCase):
    def test_bounded_gap_keeps_candidate_without_fabricating_evidence(self):
        analyzer = ShotAnalyzer(30, max_gap_seconds=0.1)
        analyzer.update(0, observed(40), [HOOP])
        analyzer.update(1, observed(70), [HOOP])
        analyzer.update(2, {"status": "missing"}, [HOOP])
        _, event = analyzer.update(3, observed(110), [HOOP])
        self.assertIsNone(event)
        _, event = analyzer.update(4, observed(160), [HOOP])
        self.assertEqual(event["outcome"], "possible_make")
        self.assertEqual(event["crossing_gap_frames"], 1)
        self.assertNotIn(2, [p["frame"] for p in event["evidence"]])

    def test_long_gap_is_unknown(self):
        analyzer = ShotAnalyzer(30, max_gap_seconds=0.1)
        analyzer.update(0, observed(40), [HOOP])
        analyzer.update(1, observed(70), [HOOP])
        for frame in range(2, 6):
            _, event = analyzer.update(frame, {"status": "missing"}, [HOOP])
        self.assertEqual(event["outcome"], "unknown")

    def test_upward_rebound_is_possible_miss(self):
        analyzer = ShotAnalyzer(30)
        for frame, y in enumerate([40, 70, 110, 100, 85, 70]):
            _, event = analyzer.update(frame, observed(y), [HOOP])
        self.assertEqual(event["outcome"], "possible_miss")
        self.assertIn("rebound", event["reason"])

    def test_one_upward_jitter_is_not_a_rebound(self):
        analyzer = ShotAnalyzer(30)
        for frame, y in enumerate([40, 70, 110, 105]):
            _, event = analyzer.update(frame, observed(y), [HOOP])
        self.assertIsNone(event)


if __name__ == "__main__":
    unittest.main()
