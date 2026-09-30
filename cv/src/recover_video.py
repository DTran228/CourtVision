"""Add experimental near-hoop recovery to an existing detection run.

Run from the project root. A new folder preserves the original model predictions.
Recovered observations carry source=color_motion and no model confidence score.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2

from recovery import NearHoopRecovery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detections-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output folder exists; choose a new one.")
    capture = None
    try:
        summary = json.loads((args.detections_dir/"summary.json").read_text())
        video = Path(summary["video"])
        if not video.is_absolute():
            video = Path(__file__).resolve().parents[2]/video
        capture = cv2.VideoCapture(str(video))
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0 or not math.isclose(fps, summary["fps"], rel_tol=0.001):
            raise ValueError("Video FPS does not match the saved run.")
        recovery = NearHoopRecovery(fps)
        source = args.detections_dir/"detections.jsonl"
        count = recovered = ball_frames = 0
        args.output_dir.mkdir(parents=True)
        with source.open(encoding="utf-8") as records, (args.output_dir/"detections.jsonl").open("w", encoding="utf-8") as output:
            for line in records:
                row = json.loads(line)
                ok, frame = capture.read()
                if not ok or row["frame"] != count or abs(row["timestamp_seconds"]-count/fps) > 0.001:
                    raise ValueError("Video and detection records do not align.")
                if frame.shape[:2] != (summary["height"], summary["width"]):
                    raise ValueError("Video dimensions do not match the saved run.")
                ball = recovery.update(frame, row["detections"])
                if ball is not None:
                    # The confirmed motion path takes precedence near the hoop.
                    row["detections"] = [d for d in row["detections"] if d["class"] != "basketball"]+[ball]
                    recovered += 1
                ball_frames += any(d["class"] == "basketball" for d in row["detections"])
                output.write(json.dumps(row)+"\n")
                count += 1
                if count % 300 == 0:
                    print(f"Recovery checked {count} frames...", flush=True)
        if count != summary["frames_processed"] or capture.read()[0]:
            raise ValueError("Video and prediction frame counts differ.")
        summary.update({"frames_with_basketball": ball_frames, "frames_recovered": recovered,
                        "recovery": "experimental color/motion near hoop; not a model probability",
                        "source_detections_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "source_video_sha256": hashlib.sha256(video.read_bytes()).hexdigest()})
        (args.output_dir/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Recovered {recovered} observations across {count} frames.")
    except (OSError, ValueError, KeyError, TypeError, cv2.error) as error:
        parser.exit(1, f"Error: {error}\nAny partial output is in {args.output_dir}.\n")
    finally:
        if capture is not None:
            capture.release()


if __name__ == "__main__":
    main()
