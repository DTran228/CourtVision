"""Compare shot candidates with provisional, time-window-based visual reviews.

Unreviewed times are excluded. Temporal matching is not proof that a candidate
followed the real ball. This tiny review is a regression check, not a benchmark.
"""

import argparse
import hashlib
import json
from pathlib import Path

CV_ROOT = Path(__file__).resolve().parents[1]


def compare_attempts(attempts, windows, candidates):
    """Match at most one candidate to each non-overlapping attempt window.

    Use the observed crossing frame when available, otherwise candidate start.
    A second candidate in an already matched window counts as an extra alarm.
    """
    matched = []
    extra = []
    unreviewed = []
    used = set()
    ordered = sorted(candidates, key=lambda item: item.get("crossing_frame", item["start_frame"]))
    for candidate in ordered:
        anchor = candidate.get("crossing_frame", candidate["start_frame"])
        if not any(start <= anchor <= end for start, end in windows):
            unreviewed.append(candidate["candidate_id"])
            continue
        match = next((a for a in attempts if a["id"] not in used
                      and a["window"][0] <= anchor <= a["window"][1]), None)
        if match is None:
            extra.append(candidate["candidate_id"])
            continue
        used.add(match["id"])
        expected = {"made": "possible_make", "missed": "possible_miss", "unknown": "unknown"}[match["outcome"]]
        matched.append({"attempt_id": match["id"], "candidate_id": candidate["candidate_id"],
                        "reviewed_outcome": match["outcome"], "predicted_outcome": candidate["outcome"],
                        "outcome_agrees": candidate["outcome"] == expected if match["outcome"] != "unknown" else None})
    return {"reviewed_attempts": len(attempts), "matched_attempts": len(matched),
            "missed_attempt_ids": [a["id"] for a in attempts if a["id"] not in used],
            "extra_candidates_in_reviewed_windows": extra,
            "unreviewed_candidate_ids": unreviewed, "matches": matched}


def validate_review(clip):
    """Reject ambiguous windows before counting matches or slicing frame logs."""
    def valid_window(window):
        return (len(window) == 2 and all(isinstance(value, int) for value in window)
                and 0 <= window[0] <= window[1] < clip["frames"])

    windows = sorted(clip["reviewed_windows"])
    attempts = sorted(clip["attempts"], key=lambda item: item["window"][0])
    if not all(valid_window(window) for window in windows):
        raise ValueError("Review window is outside the clip.")
    if any(a[1] >= b[0] for a, b in zip(windows, windows[1:])):
        raise ValueError("Review windows must not overlap.")
    ids = [a["id"] for a in attempts]
    if len(ids) != len(set(ids)):
        raise ValueError("Attempt IDs must be unique.")
    for attempt in attempts:
        start, end = attempt["window"]
        if not valid_window(attempt["window"]) or not any(a <= start <= end <= b for a, b in windows):
            raise ValueError("Attempt must lie inside a reviewed window.")
        if attempt["outcome"] not in {"made", "missed", "unknown"}:
            raise ValueError("Reviewed outcome must be made, missed, or unknown.")
        first, last = attempt["visible_ball_window"]
        if not valid_window(attempt["visible_ball_window"]) or not start <= first <= last <= end:
            raise ValueError("Visibility check must lie inside the attempt window.")
    if any(a["window"][1] >= b["window"][0] for a, b in zip(attempts, attempts[1:])):
        raise ValueError("Attempt windows must not overlap.")
    return attempts, windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clip", help="Reviewed clip name, such as threemade")
    parser.add_argument("--review", type=Path, default=CV_ROOT / "experiments/shot-review.json")
    parser.add_argument("--detections-dir", type=Path, help="Default: cv/output/<clip>")
    parser.add_argument("--tracks-dir", type=Path, help="Default: cv/output/<clip>-tracking")
    parser.add_argument("--shots", type=Path, help="Default: cv/output/<clip>-shots/shots.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output folder exists; choose a new one.")
    try:
        review = json.loads(args.review.read_text(encoding="utf-8"))
        clip = next((item for item in review["clips"] if item["name"] == args.clip), None)
        if clip is None:
            raise ValueError("Clip has no saved visual review.")
        video = CV_ROOT.parent / clip["video"]
        if hashlib.sha256(video.read_bytes()).hexdigest() != clip["video_sha256"]:
            raise ValueError("Video changed; review the replacement before scoring.")
        detection_dir = args.detections_dir or CV_ROOT / "output" / args.clip
        track_dir = args.tracks_dir or CV_ROOT / "output" / f"{args.clip}-tracking"
        shots_path = args.shots or CV_ROOT / "output" / f"{args.clip}-shots/shots.json"
        shots = json.loads(shots_path.read_text())
        detection_path = detection_dir / "detections.jsonl"
        track_path = track_dir / "tracks.jsonl"
        for name, path in [("detections", detection_path), ("tracks", track_path)]:
            if hashlib.sha256(path.read_bytes()).hexdigest() != shots["source_sha256"][name]:
                raise ValueError("Shot results were generated from different logs.")
        detections = [json.loads(line) for line in detection_path.read_text().splitlines()]
        tracks = [json.loads(line) for line in track_path.read_text().splitlines()]
        if not len(detections) == len(tracks) == clip["frames"] == shots["frames_processed"]:
            raise ValueError("Frame counts do not match the reviewed clip.")
        summary = json.loads((detection_dir / "summary.json").read_text())
        source = Path(summary["video"])
        if not source.is_absolute():
            source = CV_ROOT.parent / source
        if source.resolve() != video.resolve() or summary["fps"] != clip["fps"]:
            raise ValueError("Detection run does not match the reviewed video.")
        attempts, windows = validate_review(clip)
        for index, (detection, track) in enumerate(zip(detections, tracks)):
            if detection["frame"] != index or track["frame"] != index:
                raise ValueError("Log frame indices do not align.")
        result = compare_attempts(attempts, windows, shots["candidates"])
        result["reviewer"] = review["reviewer"]
        result["clip"] = args.clip
        result["source_sha256"] = {"review": hashlib.sha256(args.review.read_bytes()).hexdigest(),
                                   "shots": hashlib.sha256(shots_path.read_bytes()).hexdigest(),
                                   "video": clip["video_sha256"]}
        # Separate upstream detection availability from downstream track selection.
        result["visibility_checks"] = []
        for attempt in attempts:
            start, end = attempt["visible_ball_window"]
            rows = detections[start:end+1]
            selected = tracks[start:end+1]
            result["visibility_checks"].append({
                "attempt_id": attempt["id"], "window": [start, end], "frames": len(rows),
                "frames_with_any_ball_prediction": sum(any(d["class"] == "basketball" for d in row["detections"]) for row in rows),
                "frames_with_observed_track": sum(row["status"] == "observed" for row in selected),
                "note": "Presence counts only; a prediction is not necessarily the reviewed real ball.",
            })
        args.output_dir.mkdir(parents=True)
        (args.output_dir / "evaluation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
