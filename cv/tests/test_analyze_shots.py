"""Exercise the real command with tiny, aligned synthetic log files."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "src/analyze_shots.py"


class ShotCommandTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.detections = self.root / "detections"
        self.tracks = self.root / "tracks"
        self.output = self.root / "output"
        self.detections.mkdir()
        self.tracks.mkdir()
        summary = {"video": str(self.root / "synthetic.mp4"), "width": 400,
                   "height": 400, "fps": 30, "frames_processed": 4}
        (self.detections / "summary.json").write_text(json.dumps(summary))
        (self.tracks / "summary.json").write_text(json.dumps({**summary, "detections_dir": str(self.detections)}))
        self.rows = []
        self.track_rows = []
        for index, y in enumerate([40, 70, 110, 160]):
            ball = {"class": "basketball", "confidence": 0.8, "bbox": [148, y-2, 152, y+2]}
            hoop = {"class": "hoop", "confidence": 0.9, "bbox": [100, 100, 200, 160]}
            timing = {"frame": index, "timestamp_seconds": round(index/30, 4)}
            self.rows.append({**timing, "detections": [ball, hoop]})
            self.track_rows.append({**timing, "status": "observed", "track_id": 1,
                                    "center": [150, y], "bbox": ball["bbox"], "confidence": 0.8})

    def run_command(self):
        for path, rows in [(self.detections / "detections.jsonl", self.rows),
                           (self.tracks / "tracks.jsonl", self.track_rows)]:
            path.write_text("\n".join(json.dumps(row) for row in rows)+"\n")
        return subprocess.run([sys.executable, str(SCRIPT), "--detections-dir", str(self.detections),
                               "--tracks-dir", str(self.tracks), "--output-dir", str(self.output)],
                              capture_output=True, text=True)

    def test_valid_logs_produce_event_states_and_review(self):
        result = self.run_command()
        self.assertEqual(result.returncode, 0, result.stderr)
        shots = json.loads((self.output / "shots.json").read_text())
        self.assertEqual(shots["outcome_counts"]["possible_make"], 1)
        self.assertEqual(len((self.output / "shot_states.jsonl").read_text().splitlines()), 4)
        self.assertIn("possible_make", (self.output / "review.md").read_text())

    def test_misaligned_timestamp_is_rejected(self):
        self.track_rows[1]["timestamp_seconds"] = 99
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not align", result.stderr)
        self.assertFalse((self.output / "shots.json").exists())

    def test_edited_center_is_rejected(self):
        self.track_rows[1]["center"] = [100, 70]
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("center does not match", result.stderr)

    def test_extra_log_record_is_rejected(self):
        self.rows.append(self.rows[-1])
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Extra records", result.stderr)

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("original")
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), "original")


if __name__ == "__main__":
    unittest.main()
