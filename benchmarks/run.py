"""Append-only client-observed benchmark via a running API + explicit worker.

Each run uploads the same frozen bytes and settings. No cache is used. Cloud
requires explicit --paid and a declared approved budget; see docs/BENCHMARKS.md.
"""
import argparse
from datetime import datetime, timezone
import http.client
import json
import math
import os
from pathlib import Path
import platform
import time
from urllib.parse import urlsplit
import uuid

from benchmarks.manifest import load_manifest
from cv.src.contract import Settings, MODEL_SHA256, code_hash, sha256


def http_json(api, method, path, value=None, file=None):
    url = urlsplit(api)
    if url.scheme not in {"http", "https"} or not url.hostname or url.query or url.fragment:
        raise ValueError("Invalid API URL")
    cls = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
    client = cls(url.hostname, url.port, timeout=180)
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("COURTVISION_ACCESS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(value).encode() if value is not None else None
    try:
        if file:
            headers.update({"Content-Type": "video/mp4", "Content-Length": str(Path(file).stat().st_size)})
            with Path(file).open("rb") as stream:
                client.request(method, url.path.rstrip("/")+path, stream, headers)
        else:
            client.request(method, url.path.rstrip("/")+path, body, headers)
        response = client.getresponse()
        result = json.loads(response.read())
        if not 200 <= response.status < 300:
            raise RuntimeError(f"HTTP {response.status}: {result}")
        return result
    finally:
        client.close()


def write_once(path, value):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, allow_nan=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--api", default="http://127.0.0.1:8000")
    p.add_argument("--runner", choices=["local", "modal"], required=True)
    p.add_argument("--temperature", choices=["cold", "warm", "unclassified"], default="unclassified", help="Requested stratum; actual cloud container observation is logged separately")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--max-runs", type=int, default=40)
    p.add_argument("--timeout-seconds", type=float, default=1800)
    p.add_argument("--pilot", action="store_true")
    p.add_argument("--paid", action="store_true")
    p.add_argument("--budget-usd", type=float)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    manifest = load_manifest(args.manifest, args.pilot)
    planned = len(manifest["clips"])*args.repeats
    if args.repeats < 1 or planned > args.max_runs or not math.isfinite(args.timeout_seconds) or args.timeout_seconds <= 0:
        p.error("Invalid repeats/timeout or plan exceeds max-runs")
    if args.runner == "modal" and not args.dry_run and (not args.paid or not args.budget_usd or not math.isfinite(args.budget_usd) or args.budget_usd <= 0):
        p.error("Paid cloud needs --paid and --budget-usd after owner approval; no automatic monetary cap")
    if args.dry_run:
        print(json.dumps({"planned_runs": planned, "runner": args.runner, "settings": manifest["settings"],
                          "requested_temperature": args.temperature, "pilot": args.pilot, "uploads": False}, indent=2))
        return
    args.output.mkdir(parents=True, exist_ok=False)
    write_once(args.output/"plan.json", {"schema_version": 1, "manifest_sha256": sha256(args.manifest),
        "manifest": manifest, "runner": args.runner, "repeats": args.repeats, "pilot": args.pilot,
        "requested_temperature": args.temperature, "approved_budget_usd": args.budget_usd,
        "client_platform": platform.platform(), "client_python": platform.python_version(),
        "note": "Budget value is owner declaration, not billing enforcement. No result cache."})
    for clip in manifest["clips"]:
        for repeat in range(args.repeats):
            ident = str(uuid.uuid4())
            row = {"schema_version": 1, "run_id": ident, "clip_sha256": clip["sha256"], "runner": args.runner,
                   "config_sha256": Settings(**manifest["settings"]).hash, "code_sha256": code_hash(), "model_sha256": MODEL_SHA256,
                   "requested_temperature": args.temperature, "repeat": repeat, "pilot": args.pilot,
                   "started_at": datetime.now(timezone.utc).isoformat(), "status": "failed",
                   "duration_seconds": clip["media"]["duration_seconds"], "resolution": [clip["media"]["width"], clip["media"]["height"]],
                   "fps": clip["media"]["fps"], "concurrency": 1, "cache_hit": False,
                   "stages": {"cloud_queue_seconds": None, "cloud_startup_seconds": None, "encode_seconds": None,
                              "measured_cloud_cost_usd": None}, "cost_note": "Unmeasured; use provider billing export"}
            write_once(args.output/f"{ident}-request.json", {**row, "status": "starting"})
            started = time.perf_counter()
            try:
                t = time.perf_counter()
                video = http_json(args.api, "POST", "/videos", file=clip["resolved_path"])
                row["stages"]["client_upload_validation_seconds"] = time.perf_counter()-t
                job = http_json(args.api, "POST", "/jobs", {"video_id": video["id"], "runner": args.runner,
                    "settings": manifest["settings"], "idempotency_key": ident})
                write_once(args.output/f"{ident}-job.json", job)  # Preserve ID even if polling is interrupted.
                while job["status"] in {"queued", "running"}:
                    if time.perf_counter()-started > args.timeout_seconds:
                        raise TimeoutError("Client wait exceeded limit; job may still run. Resume saved job ID, do not resubmit.")
                    time.sleep(2)
                    job = http_json(args.api, "GET", f"/jobs/{job['id']}")
                if job["status"] != "succeeded":
                    raise RuntimeError(json.dumps(job["error"]))
                row["client_review_ready_seconds"] = time.perf_counter()-started
                t = time.perf_counter()
                session = http_json(args.api, "GET", f"/sessions/{job['id']}")
                row["stages"]["client_result_fetch_seconds"] = time.perf_counter()-t
                result = session["automatic"]
                if (result["video_sha256"] != clip["sha256"] or result["config_sha256"] != row["config_sha256"]
                        or result["code_sha256"] != row["code_sha256"] or result["model_sha256"] != row["model_sha256"]):
                    raise ValueError("Benchmark input/config/code/model parity mismatch")
                write_once(args.output/f"{ident}-result.json", result)
                row.update(status="succeeded", code_sha256=result["code_sha256"], model_sha256=result["model_sha256"],
                           config_sha256=result["config_sha256"], summary=result["summary"], job_id=job["id"], attempt=job["attempt"])
                row["stages"].update(result["timings"])
                if job["started_at"]:
                    row["stages"]["backend_queue_seconds"] = (datetime.fromisoformat(job["started_at"])-datetime.fromisoformat(job["created_at"])).total_seconds()
                execution = result.get("execution", {})
                row["observed_temperature"] = ("cold" if execution["cold_first_request"] else "warm") if "cold_first_request" in execution else "unclassified"
                row["hardware"] = execution.get("gpu", "local CPU; see server runtime metadata")
                row["execution"] = execution
                if session.get("transport_measurements"):
                    row["stages"].update(session["transport_measurements"])
                row["processed_fps"] = result["timebase"]["frames"]/result["timings"]["pipeline_seconds"]
                row["seconds_per_video_minute"] = result["timings"]["pipeline_seconds"]/(row["duration_seconds"]/60)
            except Exception as error:
                row["error"] = {"type": type(error).__name__, "message": str(error)}
            row["client_total_seconds"] = time.perf_counter()-started
            write_once(args.output/f"{ident}-run.json", row)
            print(json.dumps({"run_id": ident, "status": row["status"]}), flush=True)


if __name__ == "__main__":
    main()
