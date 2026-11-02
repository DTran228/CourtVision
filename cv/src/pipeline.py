"""Callable CPU/GPU analysis. Old diagnostic CLIs remain available unchanged."""
import argparse
from contextlib import ExitStack
import json
import math
from pathlib import Path
import time
import uuid

import av

from cv.src.candidate_tracker import CandidateTracker
from cv.src.contract import Settings, MODEL_SHA256, code_hash, counts, sha256, validate_result
from cv.src.media import inspect_video
from cv.src.recovery import NearHoopRecovery
from cv.src.shots import ShotAnalyzer
from cv.src.tracker import BallTracker

DEFAULT_WEIGHTS = Path(__file__).resolve().parents[1]/"models/ebard-yolov8n.pt"


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


def make_tracker(settings, media):
    diagonal = math.hypot(media["width"], media["height"])
    if settings.tracker == "candidate":
        return CandidateTracker(media["fps"], diagonal)
    return BallTracker(.05*diagonal, math.floor(.2*media["fps"]), max(2, round(.5*media["fps"])))


def process_observation(tracker, analyzer, index, timestamp, detections):
    if isinstance(tracker, CandidateTracker):
        track = tracker.update(detections, timestamp, shot_active=analyzer.active is not None)
    else:
        track = tracker.update(detections)
    state, event = analyzer.update(index, track, detections)
    return track, state, event


def analyze_video(video, settings, output, *, detector=None, detector_factory=None, device="cpu", weights=DEFAULT_WEIGHTS, progress=None):
    """New output directory per attempt. Injected detector is for offline tests only.

    Worker supplies its cached detector, avoiding repeated model loads. A completion
    manifest is written last; partial files never constitute a completed analysis.
    """
    started = time.perf_counter()
    settings = settings if isinstance(settings, Settings) else Settings(**settings)
    video, output = Path(video), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    media = inspect_video(video)
    timings = {"media_validation_seconds": time.perf_counter()-started}
    if progress:
        progress("model_initialization", 0, media["frames"])
    load_start = time.perf_counter()
    model_hash = sha256(weights)
    if model_hash != MODEL_SHA256 and detector is None:
        raise ValueError("Model hash differs from the pinned E-BARD model")
    if detector is None:
        if detector_factory:
            detector = detector_factory(weights, settings, device)
        else:
            from cv.src.detector import Detector
            detector = Detector(weights, settings.confidence, settings.image_size, device)
    timings["model_initialization_seconds"] = time.perf_counter()-load_start
    tracker = make_tracker(settings, media)
    analyzer = ShotAnalyzer(media["fps"], .25, time_aware=settings.tracker == "candidate")
    recovery = NearHoopRecovery(media["fps"]) if settings.recovery else None
    timings.update(decode_seconds=0., inference_seconds=0., tracking_classification_seconds=0., artifact_write_seconds=0., encode_seconds=None)
    candidates = []
    with ExitStack() as stack:
        container = stack.enter_context(av.open(str(video)))
        decoded = iter(container.decode(video=0))
        logs = {name: stack.enter_context((output/f"{name}.jsonl").open("x", encoding="utf-8"))
                for name in ("detections", "tracks", "states")}
        for index, timestamp in enumerate(media["pts_seconds"]):
            t = time.perf_counter()
            frame = next(decoded).to_ndarray(format="bgr24")
            timings["decode_seconds"] += time.perf_counter()-t
            t = time.perf_counter()
            if device != "cpu":
                import torch
                torch.cuda.synchronize()
            detections = detector.detect(frame)
            if device != "cpu":
                torch.cuda.synchronize()
            timings["inference_seconds"] += time.perf_counter()-t
            t = time.perf_counter()
            if recovery:
                recovered = recovery.update(frame, detections)
                if recovered:
                    detections = [*detections, recovered]
            track, state, event = process_observation(tracker, analyzer, index, timestamp, detections)
            if event:
                candidates.append(event)
            timings["tracking_classification_seconds"] += time.perf_counter()-t
            t = time.perf_counter()
            common = {"frame": index, "timestamp_seconds": timestamp}
            logs["detections"].write(json.dumps({**common, "detections": detections})+"\n")
            logs["tracks"].write(json.dumps({**common, **track})+"\n")
            logs["states"].write(json.dumps({**common, "state": state})+"\n")
            timings["artifact_write_seconds"] += time.perf_counter()-t
            if progress and (index % 30 == 0 or index+1 == media["frames"]):
                progress("analysis", index+1, media["frames"])
        if next(decoded, None) is not None:
            raise ValueError("Decoded frame count changed")
    final = analyzer.finish("Video ended before outcome evidence was complete.", media["frames"]-1)
    if final:
        candidates.append(final)
    events = []
    for candidate in candidates:
        start, end = candidate["start_frame"], candidate["end_frame"]
        contact = candidate.get("crossing_frame", start)
        outcome = {"possible_make": "made", "possible_miss": "missed", "unknown": "unknown"}[candidate["outcome"]]
        events.append({"id": str(candidate["candidate_id"]),
                       "start_seconds": media["pts_seconds"][start], "contact_seconds": media["pts_seconds"][contact],
                       "end_seconds": media["pts_seconds"][end], "outcome": outcome, "automatic_estimate": True,
                       "reason": candidate["reason"], "uncertainty_reason": candidate["reason"] if outcome == "unknown" else None,
                       "evidence": [{**p, "status": "observed", "timestamp_seconds": media["pts_seconds"][p["frame"]],
                                     "reference": f"tracks.jsonl#{p['frame']}"} for p in candidate["evidence"]]})
    atomic_json(output/"media.json", media)
    timings["pipeline_seconds"] = time.perf_counter()-started
    result = {"schema_version": 1, "run_id": str(uuid.uuid4()), "video_sha256": sha256(video),
              "model_sha256": model_hash, "code_sha256": code_hash(), "config_sha256": settings.hash,
              "settings": settings.to_dict(), "device": device,
              "timebase": {k: v for k, v in media.items() if k != "pts_seconds"},
              "events": events, "summary": counts(events), "timings": timings}
    validate_result(result)
    atomic_json(output/"result.json", result)
    manifest = {"schema_version": 1, "run_id": result["run_id"], "complete": True,
                "artifacts": {p.name: sha256(p) for p in output.iterdir() if p.is_file()}}
    atomic_json(output/"manifest.json", manifest)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("video", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--tracker", choices=["baseline", "candidate"], default="baseline")
    p.add_argument("--recovery", action="store_true")
    args = p.parse_args()
    result = analyze_video(args.video, Settings(tracker=args.tracker, recovery=args.recovery), args.output)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
