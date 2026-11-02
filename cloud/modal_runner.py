"""Transfer/dispatch/poll/retrieve state machine; injected transport supports offline tests."""
import json
import os
from pathlib import Path
import time

from backend.app.storage import confined, identifier
from cv.src.contract import sha256
from cv.src.pipeline import atomic_json


class SDKTransport:
    def __init__(self):
        import modal
        self.modal = modal
        self.volume = modal.Volume.from_name("courtvision-artifacts")
        self.function = modal.Cls.from_name("courtvision", "GPUWorker")().analyze

    def upload(self, source, remote):
        with self.volume.batch_upload() as batch:
            batch.put_file(source, remote)

    def spawn(self, payload):
        return self.function.spawn(payload).object_id

    def poll(self, call_id):
        try:
            return self.modal.FunctionCall.from_id(call_id).get(timeout=0)
        except TimeoutError:
            return None

    def download(self, remote, local):
        with Path(local).open("wb") as f:
            for chunk in self.volume.read_file(remote):
                f.write(chunk)


class ModalRunner:
    def __init__(self, transport=None):
        if transport is None:
            if os.environ.get("COURTVISION_ENABLE_MODAL") != "1":
                raise ValueError("Modal disabled; see docs/MODAL.md")
            transport = SDKTransport()
        self.transport = transport

    def step(self, job, source, output, store):
        ident = identifier(job["id"])
        attempt = job["attempt"]
        remote = f"/jobs/{ident}/attempt-{attempt}"
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        control_path = output/"transport.json"
        timing = json.loads(control_path.read_text()) if control_path.exists() else {}
        call_id = job["remote_call_id"]
        if call_id is None:
            if job["dispatch_intent"]:
                raise ValueError("Ambiguous dispatch; inspect Modal call/artifacts, never automatically respawn")
            started = time.perf_counter()
            store.progress(ident, "cloud_upload")
            self.transport.upload(source, remote+"/input.mp4")
            timing["backend_to_cloud_seconds"] = time.perf_counter()-started
            atomic_json(control_path, timing)
            payload = {"job_id": ident, "attempt": attempt, "settings": job["settings"],
                       "video_sha256": job["source_sha256"], "config_sha256": job["config_sha256"],
                       "model_sha256": job["model_sha256"], "code_sha256": job["code_sha256"]}
            # Crash between spawn and call-ID commit is intentionally ambiguous.
            store.dispatch(ident)
            call_id = self.transport.spawn(payload)
            store.dispatch(ident, call_id)
        store.progress(ident, "cloud_processing")
        completion = self.transport.poll(call_id)
        if completion is None:
            return None
        expected_path = remote+"/output/manifest.json"
        if completion.get("manifest_path") != expected_path:
            raise ValueError("Unexpected cloud completion path")
        started = time.perf_counter()
        manifest_path = output/"manifest.json"
        self.transport.download(expected_path, manifest_path.with_suffix(".partial"))
        manifest = json.loads(manifest_path.with_suffix(".partial").read_text())
        if manifest.get("complete") is not True:
            raise ValueError("Cloud manifest incomplete")
        for name, digest in manifest["artifacts"].items():
            if Path(name).name != name or name in {"manifest.json", "transport.json"}:
                raise ValueError("Invalid cloud artifact name")
            local = confined(output, name)
            partial = local.with_suffix(local.suffix+".partial")
            self.transport.download(remote+"/output/"+name, partial)
            if sha256(partial) != digest:
                raise ValueError("Cloud artifact hash mismatch")
            partial.replace(local)
        manifest_path.with_suffix(".partial").replace(manifest_path)
        timing["result_transfer_seconds"] = time.perf_counter()-started
        timing["remote_call_id"] = call_id
        atomic_json(control_path, timing)
        return json.loads((output/"result.json").read_text())
