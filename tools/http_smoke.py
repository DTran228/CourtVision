"""Opt-in loopback smoke: separate API/worker processes, real model, tiny synthetic input."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from unittest.mock import patch
import uuid

from benchmarks.run import http_json
from cv.src.pipeline import atomic_json
from tests.fixtures import make_video


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    video = make_video(args.output/"synthetic.mp4")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    api = f"http://127.0.0.1:{port}"
    env = {**os.environ, "COURTVISION_DATA": str(args.output/"app-data"),
           "COURTVISION_ACCESS_TOKEN": str(uuid.uuid4()), "COURTVISION_ENABLE_MODAL": "0"}
    processes = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    root = Path(__file__).resolve().parents[1]
    try:
        with (args.output/"api.log").open("w") as api_log, (args.output/"worker.log").open("w") as worker_log, patch.dict(os.environ, env):
            processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=root, env=env, stdout=api_log, stderr=subprocess.STDOUT, creationflags=flags))
            deadline = time.monotonic()+30
            while True:
                try:
                    if http_json(api, "GET", "/health")["status"] == "ok":
                        break
                except OSError:
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError("API startup failed; inspect api.log")
                time.sleep(.25)
            processes.append(subprocess.Popen([sys.executable, "-m", "backend.app.worker"], cwd=root, env=env,
                stdout=worker_log, stderr=subprocess.STDOUT, creationflags=flags))
            manifest = args.output/"manifest.json"
            subprocess.run([sys.executable, "-m", "benchmarks.manifest", "--videos", str(video), "--output", str(manifest)], check=True, cwd=root, env=env)
            subprocess.run([sys.executable, "-m", "benchmarks.run", "--manifest", str(manifest), "--runner", "local", "--pilot",
                "--api", api, "--repeats", "1", "--timeout-seconds", "180", "--output", str(args.output/"runs")], check=True, cwd=root, env=env)
            runs = [json.loads(path.read_text()) for path in (args.output/"runs").glob("*-run.json")]
            if len(runs) != 1 or runs[0]["status"] != "succeeded":
                raise RuntimeError(f"Loopback smoke failed: {runs}")
            job_id = runs[0]["job_id"]
            session = http_json(api, "GET", f"/sessions/{job_id}")
            saved = http_json(api, "PATCH", f"/sessions/{job_id}/review", {
                "expected_revision": session["revision"], "complete": False, "events": session["review"]["events"]})
            assert saved["revision"] == 1
            # Restart API and verify the same session/review survive a real process boundary.
            processes[0].terminate()
            processes[0].wait(timeout=10)
            processes[0] = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=root, env=env, stdout=api_log, stderr=subprocess.STDOUT, creationflags=flags)
            deadline = time.monotonic()+30
            while True:
                try:
                    persisted = http_json(api, "GET", f"/sessions/{job_id}")
                    if persisted["revision"] == 1:
                        break
                except OSError:
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError("API restart failed")
                time.sleep(.25)
            atomic_json(args.output/"http-smoke.json", {"status": "succeeded", "synthetic_video": True, "real_model": True,
                "api_worker_separate_processes": True, "api_restart_review_persisted": True,
                "review_revision": persisted["revision"], "job_id": job_id,
                "automatic_summary": session["automatic"]["summary"], "benchmark_run": runs[0],
                "note": "Loopback plumbing only, not basketball accuracy, phone latency or a controlled benchmark"})
            print("Loopback API + worker + real model + API restart: passed")
    finally:
        for proc in reversed(processes):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == "__main__":
    main()
