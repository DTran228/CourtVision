import unittest

from cv.src.candidate_tracker import CandidateTracker
from cv.src.shots import ShotAnalyzer


def ball(x, y, confidence=.5):
    return {"class": "basketball", "bbox": [x-3, y-3, x+3, y+3], "confidence": confidence}


HOOP = {"class": "hoop", "bbox": [80, 100, 120, 120], "confidence": .9}


class CandidateTests(unittest.TestCase):
    def acquire(self, fps=30):
        tracker = CandidateTracker(fps, 300)
        rows = []
        for i in range(round(fps*.11)):
            rows.append(tracker.update([ball(200, 160, .99), ball(100, 50+120*i/fps), HOOP], i/fps))
        return tracker, rows

    def test_moving_ball_beats_stationary_spare_at_30_and_60fps(self):
        for fps in (30, 60):
            tracker, rows = self.acquire(fps)
            self.assertEqual(rows[-1]["status"], "observed")
            self.assertEqual(rows[-1]["center"][0], 100)
            self.assertLessEqual(len(tracker.tracks), 8)

    def test_predictions_do_not_become_shot_evidence_and_gap_expires(self):
        tracker, rows = self.acquire()
        row = tracker.update([HOOP], .12)
        self.assertIsNone(row["center"])
        self.assertIsNotNone(row["predicted_center"])
        analyzer = ShotAnalyzer(30, .25)
        self.assertIsNone(analyzer.update(4, row, [HOOP])[1])
        row = tracker.update([HOOP], .5)
        self.assertIsNone(row["track_id"])

    def test_ambiguous_crossing_breaks_identity(self):
        tracker, rows = self.acquire()
        predicted_y = rows[-1]["center"][1]+4
        row = tracker.update([ball(99, predicted_y), ball(101, predicted_y), HOOP], .1)
        self.assertEqual(row["status"], "ambiguous")
        self.assertIsNone(row["center"])

    def test_camera_cut_resets_selection(self):
        tracker, _ = self.acquire()
        moved = {**HOOP, "bbox": [180, 100, 220, 120]}
        row = tracker.update([ball(100, 62), moved], .1)
        self.assertIsNone(row["track_id"])

    def test_locked_track_follows_rebound_without_switching_to_spare(self):
        tracker, rows = self.acquire()
        ident = rows[-1]["track_id"]
        for i, y in enumerate([62, 66, 70, 66, 62], 3):
            row = tracker.update([ball(100, y), ball(200, 160, .99), HOOP], i/30, shot_active=True)
            self.assertEqual(row["track_id"], ident)

    def test_non_increasing_time_rejected(self):
        tracker, _ = self.acquire()
        with self.assertRaises(ValueError):
            tracker.update([], 0)

    def test_time_aware_outcomes_and_cooldown_agree_at_30_and_60fps(self):
        for fps in (30, 60):
            analyzer = ShotAnalyzer(fps, .25, time_aware=True)
            events = []
            for i in range(round(fps*1.6)):
                y = 70+36*i/fps  # 0.9 hoop-widths/second, identical physical motion.
                track = {"status": "observed", "track_id": 1, "center": [100, y], "source": "model"}
                _, event = analyzer.update(i, track, [HOOP])
                if event:
                    events.append(event)
            self.assertEqual([e["outcome"] for e in events], ["possible_make"])
            self.assertAlmostEqual(events[0]["crossing_frame"]/fps, 5/6, delta=1/fps)
