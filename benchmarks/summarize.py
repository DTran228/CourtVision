"""Reproduce timing summaries and CSV from raw run files, retaining failures."""
import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import random
import statistics


def percentile(values, q):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q*len(ordered))-1)]


def distribution(values):
    result = {"n": len(values), "median": statistics.median(values) if values else None,
              "min": min(values) if values else None, "max": max(values) if values else None,
              "p95": None, "p95_bootstrap_95pct_interval": None}
    if len(values) >= 100:
        result["p95"] = percentile(values, .95)
        rng = random.Random(0)
        samples = [percentile(rng.choices(values, k=len(values)), .95) for _ in range(1000)]
        result["p95_bootstrap_95pct_interval"] = [percentile(samples, .025), percentile(samples, .975)]
    result["p95_note"] = "Suppressed below 100 runs; exploratory bootstrap interval assumes independent repeats, not a strong tail-latency guarantee"
    return result


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        if row.get("cache_hit"):
            continue
        key = tuple(row.get(k) for k in ("runner", "observed_temperature", "clip_sha256", "config_sha256", "model_sha256", "code_sha256", "hardware"))
        groups[key].append(row)
    report = []
    for key, values in sorted(groups.items(), key=lambda item: str(item[0])):
        success = [r for r in values if r["status"] == "succeeded"]
        fields = {"client_total_seconds": [r["client_total_seconds"] for r in success],
                  "client_review_ready_seconds": [r["client_review_ready_seconds"] for r in success],
                  "compute_pipeline_seconds": [r["stages"]["pipeline_seconds"] for r in success],
                  "model_inference_seconds": [r["stages"]["inference_seconds"] for r in success]}
        report.append({"group": dict(zip(("runner", "observed_temperature", "clip_sha256", "config_sha256", "model_sha256", "code_sha256", "hardware"), key)),
                       "attempted": len(values), "succeeded": len(success), "failed": len(values)-len(success),
                       "error_rate": (len(values)-len(success))/len(values),
                       "timings": {field: distribution(samples) for field, samples in fields.items()}})
    return report


def failure_summary(rows):
    """Failed runs without runtime/GPU data must still count against attempted inputs."""
    groups = defaultdict(list)
    for row in rows:
        if not row.get("cache_hit"):
            key = tuple(row.get(k) for k in ("runner", "requested_temperature", "clip_sha256", "config_sha256", "model_sha256", "code_sha256"))
            groups[key].append(row)
    return [{"group": list(key), "attempted": len(values), "failed": sum(r["status"] != "succeeded" for r in values),
             "error_rate": sum(r["status"] != "succeeded" for r in values)/len(values)} for key, values in groups.items()]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("runs", type=Path, nargs="+")
    p.add_argument("--output", type=Path, required=True, help="New directory")
    args = p.parse_args()
    paths = sorted({p for root in args.runs for p in root.glob("*-run.json")})
    rows = [json.loads(path.read_text()) for path in paths]
    if len({r["run_id"] for r in rows}) != len(rows):
        p.error("Duplicate run IDs")
    args.output.mkdir(parents=True, exist_ok=False)
    from cv.src.contract import sha256
    report = {"schema_version": 1, "raw_sha256": {str(p): sha256(p) for p in paths},
              "runs": len(rows), "cache_hits_excluded": sum(bool(r.get("cache_hit")) for r in rows),
              "groups": summarize(rows),
              "input_failure_summary": failure_summary(rows),
              "note": "No speedup ratio without matching quality/parity and temperature. Failures remain in raw counts."}
    (args.output/"summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    fields = ["run_id", "runner", "observed_temperature", "clip_sha256", "status", "client_total_seconds", "client_review_ready_seconds", "processed_fps", "seconds_per_video_minute"]
    with (args.output/"runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"runs": len(rows), "groups": len(report["groups"])}))


if __name__ == "__main__":
    main()
