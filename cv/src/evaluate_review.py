"""Compare confidence thresholds against provisional ball-candidate judgments.

This evaluates saved predictions without running YOLO again. It does NOT measure
full-video recall: uncertain and unreviewed objects are excluded.
"""

import argparse
import hashlib
import json
from pathlib import Path

CV_ROOT = Path(__file__).resolve().parents[1]


def load_review(predictions, labels, split):
    """Bind candidate indices to the exact prediction file that was reviewed."""
    review = json.loads(labels.read_text(encoding="utf-8"))
    if hashlib.sha256(predictions.read_bytes()).hexdigest() != review["prediction_sha256"]:
        raise ValueError("Prediction file changed; review its candidates again before scoring.")
    rows = [json.loads(line) for line in predictions.read_text().splitlines()]
    candidates = []
    reviewed = skipped = 0
    seen = set()
    for frame in review["frames"]:
        number = frame["frame"]
        if number in seen:
            raise ValueError("Review contains a duplicate frame index.")
        seen.add(number)
        if frame["split"] != split:
            continue
        if frame["status"] != "reviewed":
            skipped += 1
            continue
        if not 0 <= number < len(rows) or rows[number]["frame"] != number:
            raise ValueError("Review frame is missing from the prediction log.")
        balls = [d for d in rows[number]["detections"] if d["class"] == "basketball"]
        judgments = frame["candidates"]
        if sorted(j["index"] for j in judgments) != list(range(len(balls))):
            raise ValueError("Each ball candidate in a reviewed frame needs one judgment.")
        for judgment in judgments:
            if not isinstance(judgment["correct"], bool):
                raise ValueError("Candidate correctness must be true or false.")
            candidates.append({
                "confidence": balls[judgment["index"]]["confidence"],
                "correct": judgment["correct"],
            })
        reviewed += 1
    return candidates, reviewed, skipped, review["minimum_confidence"]


def score_threshold(candidates, threshold):
    """Count retained correct/incorrect candidates; never invent a recall score."""
    kept_correct = kept_incorrect = total_correct = 0
    for candidate in candidates:
        if candidate["correct"]:
            total_correct += 1
        if candidate["confidence"] >= threshold:
            if candidate["correct"]:
                kept_correct += 1
            else:
                kept_incorrect += 1
    kept = kept_correct + kept_incorrect
    return {
        "kept_correct": kept_correct,
        "kept_incorrect": kept_incorrect,
        "removed_correct": total_correct - kept_correct,
        "precision": kept_correct / kept if kept else None,
        # Retention only counts known correct baseline candidates, not all real balls.
        "retention": kept_correct / total_correct if total_correct else None,
    }


def percentage(value):
    return "n/a" if value is None else f"{value * 100:.1f}%"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, default=CV_ROOT / "output/20secplay/detections.jsonl")
    parser.add_argument("--labels", type=Path, default=CV_ROOT / "experiments/20secplay-review.json")
    parser.add_argument("--split", choices=["tune", "check"], default="tune")
    parser.add_argument("--thresholds", type=float, nargs="+", default=[0.25, 0.35, 0.40, 0.50, 0.60])
    args = parser.parse_args()
    try:
        candidates, reviewed, skipped, minimum = load_review(args.predictions, args.labels, args.split)
        if not reviewed:
            raise ValueError("No reviewed frames in this split.")
        if any(not minimum <= value <= 1 for value in args.thresholds):
            raise ValueError(f"Thresholds must be between {minimum} and 1; lower candidates were not logged.")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"Split: {args.split}; reviewed frames: {reviewed}; excluded frames: {skipped}")
    print("Threshold | Correct kept | Incorrect kept | Correct removed | Precision | Retention")
    for threshold in args.thresholds:
        score = score_threshold(candidates, threshold)
        print(f"{threshold:.2f} | {score['kept_correct']} | {score['kept_incorrect']} | "
              f"{score['removed_correct']} | {percentage(score['precision'])} | {percentage(score['retention'])}")
    print("Provisional visual review only. Retention is NOT recall. No IoU matching was performed.")


if __name__ == "__main__":
    main()
