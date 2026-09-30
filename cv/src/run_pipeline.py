"""Run the local M3 workflow: detections -> optional recovery -> tracks -> shots.

All output stays in a new local folder. No uploads or mobile/backend integration.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from shot_results import build_session

SRC = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reuse-detections", type=Path, help="Existing M2 run for the exact same video")
    parser.add_argument("--recover-ball", action="store_true", help="Enable experimental near-hoop color/motion recovery")
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error("Video does not exist.")
    if args.output_dir.exists():
        parser.error("Output folder exists; choose a new one.")
    try:
        if args.reuse_detections is not None:
            summary = json.loads((args.reuse_detections/"summary.json").read_text())
            source = Path(summary["video"])
            if not source.is_absolute():
                source = SRC.parents[1]/source
            if source.resolve() != args.video.resolve():
                raise ValueError("Reused detections belong to a different video.")
        args.output_dir.mkdir(parents=True)

        def run(script, *arguments):
            subprocess.run([sys.executable, str(SRC/script), *map(str, arguments)], check=True)

        detections = args.reuse_detections
        if detections is None:
            detections = args.output_dir/"model-detections"
            run("detect_video.py", args.video, "--output-dir", detections)
        if args.recover_ball:
            recovered = args.output_dir/"recovered-detections"
            run("recover_video.py", "--detections-dir", detections, "--output-dir", recovered)
            detections = recovered
        tracks = args.output_dir/"tracking"
        shots = args.output_dir/"shots"
        run("track_video.py", args.video, "--detections-dir", detections, "--output-dir", tracks)
        run("analyze_shots.py", "--detections-dir", detections, "--tracks-dir", tracks, "--output-dir", shots)
        analysis = json.loads((shots/"shots.json").read_text())
        session = build_session(analysis)
        session["video"] = str(args.video.resolve())
        session["recovery_enabled"] = args.recover_ball
        (args.output_dir/"session.json").write_text(json.dumps(session, indent=2), encoding="utf-8")
        print(json.dumps(session, indent=2))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Pipeline failed: {error}\nInspect partial output in {args.output_dir}.\n")


if __name__ == "__main__":
    main()
