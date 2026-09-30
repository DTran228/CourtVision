"""Analyze saved M2 detections and M3 tracks without rerunning the model.

Run from the project root. Outputs are provisional shot candidates for review,
not verified shot totals or shooting percentages.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

from shots import ShotAnalyzer
from shot_results import build_session


def project_path(value):
    """Stored relative paths in our run summaries are relative to the project."""
    path = Path(value)
    return path.resolve() if path.is_absolute() else (Path(__file__).resolve().parents[2] / path).resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detections-dir", type=Path, required=True)
    parser.add_argument("--tracks-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="A new results folder")
    parser.add_argument("--gap-seconds", type=float, default=0.25, help="Maximum unobserved gap; 0 restores strict mode")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output folder exists; choose a new one.")
    try:
        # Check provenance and frame timing before combining two saved runs.
        detection_summary = json.loads((args.detections_dir / "summary.json").read_text())
        track_summary = json.loads((args.tracks_dir / "summary.json").read_text())
        if project_path(track_summary["detections_dir"]) != args.detections_dir.resolve():
            raise ValueError("Tracks were generated from a different detection folder.")
        if project_path(track_summary["video"]) != project_path(detection_summary["video"]):
            raise ValueError("Run summaries refer to different videos.")
        for key in ["frames_processed", "width", "height", "fps"]:
            if track_summary[key] != detection_summary[key]:
                raise ValueError(f"Run summaries disagree on {key}.")
        fps = track_summary["fps"]
        analyzer = ShotAnalyzer(fps, max_gap_seconds=args.gap_seconds)
        count = track_summary["frames_processed"]
        if not isinstance(count, int) or count <= 0:
            raise ValueError("Expected a positive frame count.")
        detection_path = args.detections_dir / "detections.jsonl"
        track_path = args.tracks_dir / "tracks.jsonl"
        events = []
        args.output_dir.mkdir(parents=True)
        with detection_path.open(encoding="utf-8") as detections, track_path.open(encoding="utf-8") as tracks, \
                (args.output_dir / "shot_states.jsonl").open("w", encoding="utf-8") as states:
            for index in range(count):
                detection = json.loads(detections.readline())
                track = json.loads(tracks.readline())
                for row in [detection, track]:
                    timestamp = row["timestamp_seconds"]
                    if row["frame"] != index or not math.isfinite(timestamp) or abs(timestamp-index/fps) > 0.001:
                        raise ValueError("Frame indices or timestamps do not align.")
                if track["status"] == "observed":
                    # A stale/edited track must not introduce observations absent from M2.
                    matching = [d for d in detection["detections"] if d["class"] == "basketball"
                                and d["bbox"] == track["bbox"] and d["confidence"] == track["confidence"]]
                    if not matching or not isinstance(track["track_id"], int) or track["track_id"] <= 0:
                        raise ValueError("Observed track is not a saved basketball prediction.")
                    left, top, right, bottom = track["bbox"]
                    if track["center"] != [(left+right)/2, (top+bottom)/2]:
                        raise ValueError("Track center does not match its box.")
                state, event = analyzer.update(index, track, detection["detections"])
                if event:
                    events.append(event)
                states.write(json.dumps({"frame": index, "timestamp_seconds": round(index/fps, 4),
                                         "state": state, "completed_candidate": event["candidate_id"] if event else None}) + "\n")
            if detections.read().strip() or tracks.read().strip():
                raise ValueError("Extra records remain beyond the stated frame count.")
        unfinished = analyzer.finish("Video ended before outcome evidence was complete.", count-1)
        if unfinished:
            events.append(unfinished)
        result = {"provisional": True, "frames_processed": count, "fps": fps,
                  "gap_seconds": args.gap_seconds,
                  "note": "2D hoop-box heuristics; candidates are not verified shots.",
                  "source_sha256": {"detections": hashlib.sha256(detection_path.read_bytes()).hexdigest(),
                                    "tracks": hashlib.sha256(track_path.read_bytes()).hexdigest()},
                  "outcome_counts": {name: sum(e["outcome"] == name for e in events)
                                     for name in ["possible_make", "possible_miss", "unknown"]},
                  "candidates": events}
        (args.output_dir / "shots.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (args.output_dir / "session.json").write_text(json.dumps(build_session(result), indent=2), encoding="utf-8")
        report = ["# Provisional shot candidates", "", result["note"], "",
                  "| Candidate | Start (s) | End (s) | Outcome | Reason |", "| --- | --- | --- | --- | --- |"]
        for event in events:
            report.append(f"| {event['candidate_id']} | {event['start_seconds']} | {event['end_seconds']} | {event['outcome']} | {event['reason']} |")
        if not events:
            report.extend(["", "No candidates met the rules. This does NOT establish that no shots occurred."])
        (args.output_dir / "review.md").write_text("\n".join(report)+"\n", encoding="utf-8")
        print(json.dumps(result["outcome_counts"], indent=2))
        print(f"Processed {count} frames. Provisional results: {args.output_dir.resolve()}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Error: {error}\nAny partial results are in {args.output_dir}.\n")


if __name__ == "__main__":
    main()
