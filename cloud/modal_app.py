"""Deployment definition only; importing this file makes no paid calls.

Deploy explicitly after following docs/MODAL.md. Weights are baked into the image;
user footage is transferred only by the enabled server-side runner.
"""
import os
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
app = modal.App("courtvision")
volume = modal.Volume.from_name("courtvision-artifacts", create_if_missing=True, version=2)
image = (modal.Image.debian_slim(python_version="3.12")
         .apt_install("libgl1", "libglib2.0-0")
         .pip_install("torch==2.14.0", "torchvision==0.29.0", "ultralytics==8.4.164",
                      "opencv-python==4.14.0.94", "av==16.1.0", "numpy==2.5.3")
         .add_local_dir(ROOT/"cv/src", "/opt/courtvision/cv/src", copy=True,
                        ignore=["__pycache__", "*.pyc"])
         .add_local_file(ROOT/"cv/models/ebard-yolov8n.pt", "/opt/courtvision/cv/models/ebard-yolov8n.pt", copy=True)
         .env({"PYTHONPATH": "/opt/courtvision"}))


@app.cls(image=image, gpu=os.environ.get("COURTVISION_GPU", "T4"),
         volumes={"/artifacts": volume}, min_containers=0, max_containers=1,
         scaledown_window=60, timeout=900, retries=0)
class GPUWorker:
    @modal.enter()
    def load(self):
        import time
        import uuid
        from cv.src.contract import MODEL_SHA256, sha256
        from cv.src.detector import DEFAULT_WEIGHTS, Detector
        start = time.perf_counter()
        if sha256(DEFAULT_WEIGHTS) != MODEL_SHA256:
            raise ValueError("Model hash mismatch")
        self.detector = Detector(device="cuda:0")
        self.model_init_seconds = time.perf_counter()-start
        self.container_id = str(uuid.uuid4())
        self.invocations = 0

    @modal.method()
    def analyze(self, payload):
        import importlib.metadata
        import json
        import platform
        import time
        import torch
        from cv.src.contract import Settings, code_hash, sha256
        from cv.src.pipeline import analyze_video, atomic_json, DEFAULT_WEIGHTS
        import uuid
        if str(uuid.UUID(payload["job_id"])) != payload["job_id"] or type(payload["attempt"]) is not int or payload["attempt"] < 1:
            raise ValueError("Invalid job/attempt")
        volume.reload()  # No Volume files are open at reload/commit boundaries.
        root = Path("/artifacts/jobs")/payload["job_id"]/f"attempt-{payload['attempt']}"
        source = root/"input.mp4"
        settings = Settings(**payload["settings"])
        if (sha256(source) != payload["video_sha256"] or code_hash() != payload["code_sha256"]
                or sha256(DEFAULT_WEIGHTS) != payload["model_sha256"] or settings.hash != payload["config_sha256"]):
            raise ValueError("CPU/cloud input, settings, code or model mismatch; redeploy identical source")
        output = root/"output"
        remote_manifest = f"/jobs/{payload['job_id']}/attempt-{payload['attempt']}/output/manifest.json"
        if (output/"manifest.json").is_file():
            return {"manifest_path": remote_manifest}
        work = root/"work"
        if work.exists():
            raise ValueError("Partial remote attempt exists; inspect it, do not append/recompute silently")
        cold = self.invocations == 0
        self.invocations += 1
        self.detector.confidence, self.detector.image_size = settings.confidence, settings.image_size
        started = time.perf_counter()
        result = analyze_video(source, settings, work, detector=self.detector, device="cuda:0")
        runtime = {"container_id": self.container_id, "cold_first_request": cold,
                   "model_initialization_seconds": self.model_init_seconds if cold else 0,
                   "remote_method_seconds": time.perf_counter()-started,
                   "gpu": torch.cuda.get_device_name(0), "python": platform.python_version(),
                   "versions": {name: importlib.metadata.version(name) for name in
                                ("torch", "torchvision", "ultralytics", "opencv-python", "av", "numpy")}}
        atomic_json(work/"runtime.json", runtime)
        result["execution"] = runtime
        atomic_json(work/"result.json", result)
        manifest = json.loads((work/"manifest.json").read_text())
        manifest["artifacts"]["runtime.json"] = sha256(work/"runtime.json")
        manifest["artifacts"]["result.json"] = sha256(work/"result.json")
        atomic_json(work/"manifest.json", manifest)
        work.rename(output)  # Publish an immutable completed directory, then commit.
        volume.commit()
        return {"manifest_path": remote_manifest}
