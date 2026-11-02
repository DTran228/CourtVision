"""Compare trackers on unchanged saved detections; not a held-out accuracy claim."""
import argparse
import json
from pathlib import Path

from cv.src.contract import Settings, sha256
from cv.src.pipeline import make_tracker, process_observation
from cv.src.shots import ShotAnalyzer


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--detections", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    metadata = json.loads((args.detections/"summary.json").read_text())
    source = args.detections/"detections.jsonl"
    report = {"detections_sha256": sha256(source), "summary_sha256": sha256(args.detections/"summary.json"),
              "clock": "historical frame/FPS; not validated PTS; development comparison only", "variants": {}}
    for variant in ("baseline", "association_only", "association_time_aware"):
        mode = "baseline" if variant == "baseline" else "candidate"
        tracker = make_tracker(Settings(tracker=mode), metadata)
        analyzer = ShotAnalyzer(metadata["fps"], .25, time_aware=variant == "association_time_aware")
        candidates, observed = [], 0
        for index, line in enumerate(source.read_text().splitlines()):
            row = json.loads(line)
            if row["frame"] != index or abs(row["timestamp_seconds"]-index/metadata["fps"]) > .001:
                raise ValueError("Misaligned detection log")
            track, _, event = process_observation(tracker, analyzer, index, index/metadata["fps"], row["detections"])
            observed += track["status"] == "observed"
            if event:
                candidates.append(event)
        final = analyzer.finish("Input ended", index)
        if final:
            candidates.append(final)
        report["variants"][variant] = {"observed_frames": observed, "candidates": candidates,
                                   "counts": {o: sum(e["outcome"] == o for e in candidates)
                                              for o in ("possible_make", "possible_miss", "unknown")}}
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({m: v["counts"] for m, v in report["variants"].items()}))


if __name__ == "__main__":
    main()
