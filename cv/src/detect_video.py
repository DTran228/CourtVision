"""Milestone 2: read frames, detect basketballs and hoops, and save labeled video.

Run from the project root:
    .venv/Scripts/python.exe cv/src/detect_video.py cv/sample_videos/threemade.mp4
"""

import argparse
import json
import math
from pathlib import Path
import time

import cv2

from detector import DEFAULT_WEIGHTS, Detector
from visualize import draw_detections


def main():
    # 1. Read settings. A new output folder prevents overwriting earlier experiments.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Input video path")
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--image-size", type=int, default=704)
    parser.add_argument("--output-dir", type=Path, help="A new folder for results")
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error(f"Video not found: {args.video}")
    if not 0 < args.confidence <= 1:
        parser.error("Confidence must be greater than 0 and at most 1.")
    if args.image_size <= 0 or args.image_size % 32 != 0:
        parser.error("Image size must be a positive multiple of 32, such as 704.")
    output = args.output_dir or Path("cv/output") / args.video.stem
    if output.exists():
        parser.error("Output folder already exists. Use --output-dir with a new name.")

    capture = cv2.VideoCapture(str(args.video))
    writer = None
    frames_read = 0
    frames_with_ball = 0
    frames_with_hoop = 0
    started = time.perf_counter()

    try:
        # 2. Validate the video before creating output files or loading the model.
        if not capture.isOpened():
            raise ValueError("OpenCV could not open the video.")
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("The video has no usable FPS; cannot preserve playback speed.")
        success, frame = capture.read()
        if not success:
            raise ValueError("No frames could be decoded.")
        height, width = frame.shape[:2]

        print("Loading the model on CPU...", flush=True)
        detector = Detector(args.weights, args.confidence, args.image_size)
        output.mkdir(parents=True)
        # FourCC is the four-character code identifying the output video codec.
        codec = cv2.VideoWriter.fourcc("m", "p", "4", "v")
        writer = cv2.VideoWriter(str(output / "detected.mp4"), codec, fps, (width, height))
        if not writer.isOpened():
            raise ValueError("OpenCV could not create the output video.")

        # 3. Reuse the same model for every frame. JSONL stores one JSON object per line.
        with (output / "detections.jsonl").open("w", encoding="utf-8") as log:
            while success:
                if frame.shape[:2] != (height, width):
                    raise ValueError("Frame dimensions changed during the video.")
                detections = detector.detect(frame)
                annotated = draw_detections(frame, detections)
                writer.write(annotated)
                log.write(json.dumps({
                    "frame": frames_read,  # Frames are numbered starting at zero.
                    "timestamp_seconds": round(frames_read / fps, 4),
                    "detections": detections,
                }) + "\n")
                if frames_read == 0:
                    if not cv2.imwrite(str(output / "preview.jpg"), annotated):
                        raise ValueError("Could not save the preview image.")

                labels = {item["class"] for item in detections}
                frames_with_ball += int("basketball" in labels)
                frames_with_hoop += int("hoop" in labels)
                frames_read += 1
                if frames_read % 30 == 0:
                    print(f"Processed {frames_read} frames...", flush=True)
                success, frame = capture.read()
    except (ValueError, OSError, RuntimeError, cv2.error) as error:
        parser.exit(1, f"Error: {error}\nAny partial output is in {output}.\n")
    finally:
        capture.release()
        if writer is not None:
            writer.release()

    # 4. Counts describe model behavior, NOT accuracy or number of shots.
    summary = {
        "video": str(args.video),
        "weights": str(args.weights),
        "confidence_threshold": args.confidence,
        "image_size": args.image_size,
        "fps": fps,
        "width": width,
        "height": height,
        "frames_processed": frames_read,
        "frames_with_basketball": frames_with_ball,
        "frames_with_hoop": frames_with_hoop,
        "processing_seconds": round(time.perf_counter() - started, 2),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved results to {output.resolve()}")
    print("Output is silent. Inspect the boxes yourself; counts are not accuracy.")


if __name__ == "__main__":
    main()
