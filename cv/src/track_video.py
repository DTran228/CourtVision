"""M3, step 1: track a ball using the saved M2 detections (no YOLO rerun).

Run from the project root; use the exact video that produced the detection log.
Output is a silent diagnostic video, a per-frame track log, and a summary.
"""

import argparse
import json
import math
from pathlib import Path

import cv2

from tracker import BallTracker
from visualize import draw_detections, draw_track


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--detections-dir", type=Path, required=True,
                        help="M2 folder containing detections.jsonl and summary.json")
    parser.add_argument("--output-dir", type=Path, required=True, help="A new folder")
    parser.add_argument("--max-distance", type=float, default=0.05,
                        help="Matching radius as a fraction of the frame diagonal (default: 0.05)")
    parser.add_argument("--gap-seconds", type=float, default=0.20,
                        help="How long to remember an unmatched track (default: 0.20)")
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error("Input video does not exist.")
    if args.output_dir.exists():
        parser.error("Output folder already exists; choose a new folder.")
    if not 0 < args.max_distance <= 1:
        parser.error("Maximum distance must be greater than 0 and at most 1.")
    if not math.isfinite(args.gap_seconds) or args.gap_seconds < 0:
        parser.error("Gap seconds must be nonnegative and finite.")

    capture = cv2.VideoCapture(str(args.video))
    writer = None
    count = 0
    statuses = {"observed": 0, "missing": 0, "lost": 0, "searching": 0}
    try:
        # 1. Check the saved run against this video's size and timing.
        metadata = json.loads((args.detections_dir / "summary.json").read_text(encoding="utf-8"))
        source = Path(metadata["video"])
        if not source.is_absolute():
            source = Path(__file__).resolve().parents[2] / source
        if source.resolve() != args.video.resolve():
            raise ValueError("Use the same video path recorded in the detection summary.")
        fps = capture.get(cv2.CAP_PROP_FPS)
        success, frame = capture.read()
        if not success or not math.isfinite(fps) or fps <= 0:
            raise ValueError("Could not read a video with usable FPS.")
        height, width = frame.shape[:2]
        if (width, height) != (metadata["width"], metadata["height"]) or not math.isclose(fps, metadata["fps"], rel_tol=0.001):
            raise ValueError("Video dimensions or FPS do not match the saved detection run.")

        max_missing = math.floor(args.gap_seconds * fps)
        radius = args.max_distance * math.hypot(width, height)
        tracker = BallTracker(radius, max_missing, trail_length=max(2, round(fps * 0.5)))
        args.output_dir.mkdir(parents=True)
        writer = cv2.VideoWriter(str(args.output_dir / "tracked.mp4"),
                                 cv2.VideoWriter.fourcc("m", "p", "4", "v"), fps, (width, height))
        if not writer.isOpened():
            raise ValueError("Could not create the tracked video.")

        # 2. Consume exactly one saved prediction record for each video frame.
        with (args.detections_dir / "detections.jsonl").open(encoding="utf-8") as predictions, \
                (args.output_dir / "tracks.jsonl").open("w", encoding="utf-8") as log:
            while success:
                line = predictions.readline()
                if not line:
                    raise ValueError("Detection log ended before the video.")
                row = json.loads(line)
                if row["frame"] != count or abs(row["timestamp_seconds"] - count / fps) > 0.001:
                    raise ValueError("Detection frame index or timestamp does not match the video.")
                if frame.shape[:2] != (height, width):
                    raise ValueError("Video dimensions changed.")
                track = tracker.update(row["detections"])
                statuses[track["status"]] += 1
                annotated = draw_detections(frame, row["detections"])
                draw_track(annotated, track, tracker.trail)
                writer.write(annotated)
                log.write(json.dumps({"frame": count, "timestamp_seconds": row["timestamp_seconds"],
                                      **track}) + "\n")
                if count == 0 and not cv2.imwrite(str(args.output_dir / "preview.jpg"), annotated):
                    raise ValueError("Could not save preview.")
                count += 1
                if count % 300 == 0:
                    print(f"Tracked {count} frames...", flush=True)
                success, frame = capture.read()
            if predictions.read().strip() or count != metadata["frames_processed"]:
                raise ValueError("Video and saved run have different frame counts.")

        # 3. Only a completed run gets a summary. Counts are not tracking accuracy.
        summary = {"video": str(args.video), "detections_dir": str(args.detections_dir),
                   "frames_processed": count, "fps": fps, "width": width, "height": height,
                   "max_distance_fraction": args.max_distance, "max_distance_pixels": radius,
                   "gap_seconds": args.gap_seconds, "max_missing_frames": max_missing,
                   "track_segments": tracker.track_id, "status_counts": statuses}
        (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        print(f"Saved tracking results to {args.output_dir.resolve()}")
    except (OSError, ValueError, KeyError, TypeError, cv2.error) as error:
        parser.exit(1, f"Error: {error}\nAny partial output is in {args.output_dir}.\n")
    finally:
        capture.release()
        if writer is not None:
            writer.release()


if __name__ == "__main__":
    main()
