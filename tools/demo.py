"""API -> durable worker -> persisted review demonstration, in an isolated directory."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import time
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.jobs import Store
from backend.app.main import create_app
from backend.app.worker import Worker, worker_lock
from cv.src.contract import sha256
from cv.src.pipeline import analyze_video, atomic_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--video", type=Path, help="Real CFR footage; real pinned YOLO inference")
    group.add_argument("--synthetic", action="store_true", help="Offline fixture, NOT real basketball/model evidence")
    p.add_argument("--output", type=Path, required=True, help="New isolated directory")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    video = args.video
    model_patch = nullcontext()
    analyze = analyze_video
    if args.synthetic:
        from tests.fixtures import make_video, ScriptedDetector
        video = make_video(args.output/"synthetic.mp4")
        weights = args.output/"synthetic-weights.bin"
        weights.write_bytes(b"synthetic-test-only")
        model_patch = patch("backend.app.jobs.MODEL_SHA256", sha256(weights))
        def analyze(source, settings, output, **kwargs):
            kwargs.pop("detector_factory", None)
            return analyze_video(source, settings, output, detector=ScriptedDetector(), weights=weights, **kwargs)
    data = args.output/"app-data"
    started = time.perf_counter()
    with model_patch, TestClient(create_app(data)) as client, worker_lock(data):
        upload_started = time.perf_counter()
        with video.open("rb") as stream:
            uploaded = client.post("/videos", content=stream, headers={"Content-Type": "video/mp4"})
        uploaded.raise_for_status()
        upload_seconds = time.perf_counter()-upload_started
        job = client.post("/jobs", json={"video_id": uploaded.json()["id"], "idempotency_key": "demo"})
        job.raise_for_status()
        job = job.json()
        store = Store(data)
        worker = Worker(store, analyze=analyze)
        while worker.tick():
            state = store.get(job["id"])
            if state["status"] in {"failed", "succeeded"}:
                break
        state = store.get(job["id"])
        if state["status"] != "succeeded":
            raise RuntimeError(json.dumps(state["error"]))
        ready_seconds = time.perf_counter()-started
        session = client.get(f"/sessions/{job['id']}")
        session.raise_for_status()
        session = session.json()
        # Save an incomplete review; no automatic estimate is promoted to ground truth.
        saved = client.patch(f"/sessions/{job['id']}/review", json={"expected_revision": 0,
            "events": session["review"]["events"], "complete": False})
        saved.raise_for_status()
        assert saved.json()["revision"] == 1
        assert saved.json()["automatic"] == session["automatic"]
        evidence = {"synthetic": args.synthetic, "transport": "in-process HTTP TestClient; not phone/LAN latency",
                    "input_sha256": sha256(video), "job_id": job["id"], "status": state["status"],
                    "upload_validation_seconds": upload_seconds, "upload_to_review_ready_seconds": ready_seconds,
                    "automatic_summary": session["automatic"]["summary"],
                    "timings": session["automatic"]["timings"], "saved_review_revision": 1,
                    "result_path": str((data/f"jobs/{job['id']}/attempt-1/result.json").resolve()),
                    "model_sha256": session["automatic"]["model_sha256"], "code_sha256": session["automatic"]["code_sha256"]}
        atomic_json(args.output/"demo.json", evidence)
        if args.synthetic:
            label = {"schema_version": 1, "video_sha256": sha256(video), "recording_session_id": "synthetic-demo",
                     "split": "dev", "duration_seconds": session["automatic"]["timebase"]["duration_seconds"],
                     "reviewer": "Scripted synthetic fixture; not a human basketball review", "review_status": "provisional",
                     "fully_reviewed": True, "reviewed_intervals": [[0, session["automatic"]["timebase"]["duration_seconds"]]],
                     "attempts": [{"id": "scripted-shot", "contact_window": [.15, .19], "outcome": "made",
                                   "visibility_tags": ["synthetic"], "occlusion_tags": []}]}
            (args.output/"synthetic-labels.jsonl").write_text(json.dumps(label)+"\n", encoding="utf-8")
        print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
