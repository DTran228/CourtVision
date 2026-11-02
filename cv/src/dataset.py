"""Versioned JSONL annotation validation and fixed, one-to-one event scoring."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from cv.src.contract import sha256, validate_result

MATCH_TOLERANCE_SECONDS = 0.15  # Freeze before opening held-out results.


def finite(value):
    return type(value) in {int, float} and math.isfinite(value)


def validate_dataset(rows):
    sessions, videos = {}, set()
    for row in rows:
        if row["schema_version"] != 1 or row["split"] not in {"dev", "test"}:
            raise ValueError("Unsupported schema/split")
        video_hash = row["video_sha256"]
        if len(video_hash) != 64 or any(c not in "0123456789abcdef" for c in video_hash) or video_hash in videos:
            raise ValueError("Invalid or duplicate video hash")
        videos.add(video_hash)
        session = row["recording_session_id"]
        if not session or sessions.setdefault(session, row["split"]) != row["split"]:
            raise ValueError("Recording session leaks across dev/test")
        if not row["reviewer"] or row["review_status"] not in {"human_reviewed", "provisional", "pending"}:
            raise ValueError("Reviewer and review status are required")
        duration = row["duration_seconds"]
        if not finite(duration) or duration <= 0:
            raise ValueError("Invalid duration")
        intervals = row["reviewed_intervals"]
        for start, end in intervals:
            if not finite(start) or not finite(end) or not 0 <= start < end <= duration:
                raise ValueError("Invalid reviewed interval")
        if intervals != sorted(intervals) or any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
            raise ValueError("Reviewed intervals must be sorted and disjoint")
        if row["fully_reviewed"] and intervals != [[0, duration]]:
            raise ValueError("Fully reviewed requires [0,duration]")
        ids, windows = set(), []
        for attempt in row["attempts"]:
            if not attempt["id"] or attempt["id"] in ids:
                raise ValueError("Duplicate/empty attempt ID")
            ids.add(attempt["id"])
            start, end = attempt["contact_window"]
            if (not finite(start) or not finite(end) or not 0 <= start <= end <= duration
                    or not any(a <= start <= end <= b for a, b in intervals)):
                raise ValueError("Contact window outside reviewed intervals")
            if attempt["outcome"] not in {"made", "missed", "unknown"}:
                raise ValueError("Invalid outcome")
            if not isinstance(attempt["visibility_tags"], list) or not isinstance(attempt["occlusion_tags"], list):
                raise ValueError("Visibility/occlusion tags must be lists")
            windows.append((start, end))
        windows.sort()
        if any(a[1] >= b[0] for a, b in zip(windows, windows[1:])):
            raise ValueError("Contact windows overlap")
    return rows


def load_labels(path):
    return validate_dataset([json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()])


def score_clip(label, events):
    validate_dataset([label])
    attempts = label["attempts"]
    in_scope = [e for e in events if any(a <= e["contact_seconds"] <= b for a, b in label["reviewed_intervals"])]
    ids = [e["id"] for e in events]
    if len(ids) != len(set(ids)) or any(e["outcome"] not in {"made", "missed", "unknown"}
                                      or not finite(e["contact_seconds"]) for e in events):
        raise ValueError("Invalid predictions")
    # Greedy closest window first. Each event and label can be used once.
    edges = []
    for i, event in enumerate(in_scope):
        for j, attempt in enumerate(attempts):
            start, end = attempt["contact_window"]
            t = event["contact_seconds"]
            distance = max(start - t, 0, t - end)
            if distance <= MATCH_TOLERANCE_SECONDS:
                edges.append((distance, abs(t - (start + end) / 2), i, j))
    used_events, used_attempts, matches = set(), set(), []
    confusion = {a: {b: 0 for b in ("made", "missed", "unknown")} for a in ("made", "missed", "unknown")}
    for distance, center_error, i, j in sorted(edges):
        if i in used_events or j in used_attempts:
            continue
        used_events.add(i)
        used_attempts.add(j)
        expected, predicted = attempts[j]["outcome"], in_scope[i]["outcome"]
        confusion[expected][predicted] += 1
        matches.append({"attempt_id": attempts[j]["id"], "event_id": in_scope[i]["id"],
                        "timestamp_window_error_seconds": distance,
                        "timestamp_midpoint_error_seconds": center_error})
    tp, fp, fn = len(matches), len(in_scope) - len(matches), len(attempts) - len(matches)
    minutes = sum(b-a for a, b in label["reviewed_intervals"]) / 60
    correct = confusion["made"]["made"] + confusion["missed"]["missed"]
    known = sum(a["outcome"] != "unknown" for a in attempts)
    return {"video_sha256": label["video_sha256"], "recording_session_id": label["recording_session_id"],
            "tp": tp, "fp": fp, "fn": fn, "labeled_attempts": len(attempts), "known_outcomes": known,
            "predictions_in_reviewed_intervals": len(in_scope), "predictions_excluded": len(events)-len(in_scope),
            "precision": tp/(tp+fp) if tp+fp else None, "recall": tp/(tp+fn) if tp+fn else None,
            "f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            "confusion": confusion, "correctly_detected_and_classified": correct,
            "correct_over_all_labeled": correct/len(attempts) if attempts else None,
            "correct_over_known_outcomes": correct/known if known else None,
            "unknown_predictions": sum(e["outcome"] == "unknown" for e in in_scope),
            "unknown_rate": sum(e["outcome"] == "unknown" for e in in_scope)/len(in_scope) if in_scope else None,
            "false_positives_per_minute": fp/minutes if minutes and label["fully_reviewed"] else None,
            "reviewed_minutes": minutes, "fully_reviewed": label["fully_reviewed"],
            "count_error": len(in_scope)-len(attempts), "matches": matches,
            "missed_attempts": [a["id"] for j, a in enumerate(attempts) if j not in used_attempts],
            "false_positive_events": [e["id"] for i, e in enumerate(in_scope) if i not in used_events]}


def summarize(scores):
    sums = Counter()
    for s in scores:
        for k in ("tp", "fp", "fn", "labeled_attempts", "known_outcomes", "correctly_detected_and_classified", "unknown_predictions", "predictions_in_reviewed_intervals"):
            sums[k] += s[k]
    tp, fp, fn = (sums[k] for k in ("tp", "fp", "fn"))
    attempts, predictions = sums["labeled_attempts"], sums["predictions_in_reviewed_intervals"]
    session_errors = Counter()
    for s in scores:
        session_errors[s["recording_session_id"]] += s["count_error"]
    return {**sums, "clips": len(scores), "recording_sessions": len(session_errors),
            "precision": tp/(tp+fp) if tp+fp else None, "recall": tp/(tp+fn) if tp+fn else None,
            "f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            "correct_over_all_labeled": sums["correctly_detected_and_classified"]/attempts if attempts else None,
            "unknown_rate": sums["unknown_predictions"]/predictions if predictions else None,
            "count_error_by_recording_session": dict(session_errors)}


def track_selection_accuracy(rows):
    """Small independently reviewed near-hoop frame set; missing/ambiguous counts as wrong."""
    if not rows:
        return {"frames": 0, "correct": 0, "accuracy": None}
    correct = 0
    keys = set()
    for r in rows:
        key = (r["video_sha256"], r["frame"])
        if key in keys:
            raise ValueError("Duplicate frame label")
        keys.add(key)
        correct += r["expected_detection_id"] == r["selected_detection_id"]
    return {"frames": len(rows), "correct": correct, "accuracy": correct/len(rows)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--predictions", type=Path, nargs="+", required=True, help="Saved pipeline result.json files")
    p.add_argument("--split", choices=["dev", "test"], required=True)
    p.add_argument("--allow-provisional", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    labels = [r for r in load_labels(args.labels) if r["split"] == args.split]
    if not labels:
        p.error("No labels for selected split")
    if any(r["review_status"] != "human_reviewed" for r in labels) and not args.allow_provisional:
        p.error("Benchmark requires human-reviewed labels; --allow-provisional is development only")
    results = [validate_result(json.loads(path.read_text())) for path in args.predictions]
    indexed = {r["video_sha256"]: r for r in results}
    if len(indexed) != len(results) or set(indexed) != {r["video_sha256"] for r in labels}:
        p.error("Provide exactly one prediction per labeled clip in selected split")
    scores = [score_clip(label, indexed[label["video_sha256"]]["events"]) for label in labels]
    report = {"schema_version": 1, "split": args.split, "provisional": args.allow_provisional,
              "tolerance_seconds": MATCH_TOLERANCE_SECONDS, "labels_sha256": sha256(args.labels),
              "prediction_sha256": {str(path): sha256(path) for path in args.predictions},
              "summary": summarize(scores), "clips": scores}
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
