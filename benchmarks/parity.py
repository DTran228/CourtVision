"""Compare CPU/cloud provenance and event quality with declared time tolerance."""
import argparse
import json
import math
from pathlib import Path

from cv.src.contract import sha256, validate_result


def compare(a, b, tolerance=.05):
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Invalid tolerance")
    validate_result(a)
    validate_result(b)
    same = {key: a[key] == b[key] for key in ("video_sha256", "config_sha256", "model_sha256", "code_sha256")}
    unmatched = list(enumerate(b["events"]))
    matches, missing, differences = [], [], []
    for event in sorted(a["events"], key=lambda e: e["contact_seconds"]):
        nearby = [(abs(event["contact_seconds"]-e["contact_seconds"]), i, e) for i, e in unmatched
                  if abs(event["contact_seconds"]-e["contact_seconds"]) <= tolerance]
        if not nearby:
            missing.append(event["id"])
            continue
        error, index, other = min(nearby, key=lambda t: (t[0], t[1]))
        unmatched = [(i, e) for i, e in unmatched if i != index]
        matches.append({"cpu_event": event["id"], "cloud_event": other["id"], "timestamp_error_seconds": error})
        if event["outcome"] != other["outcome"]:
            differences.append({"cpu_event": event["id"], "cpu_outcome": event["outcome"], "cloud_outcome": other["outcome"]})
    return {"provenance_equal": same, "timestamp_tolerance_seconds": tolerance, "matches": matches,
            "missing_cloud_events": missing, "extra_cloud_events": [e["id"] for _, e in unmatched],
            "outcome_differences": differences,
            "parity_passed": all(same.values()) and not missing and not unmatched and not differences,
            "note": "Pairwise output agreement is not accuracy; evaluate both against held-out human labels."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cpu", type=Path)
    p.add_argument("cloud", type=Path)
    p.add_argument("--tolerance", type=float, default=.05)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = compare(json.loads(args.cpu.read_text()), json.loads(args.cloud.read_text()), args.tolerance)
    report["input_sha256"] = {"cpu": sha256(args.cpu), "cloud": sha256(args.cloud)}
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    if not report["parity_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
