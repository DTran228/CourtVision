"""Run exactly one explicit worker. Its OS lock is released even after a crash."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import time

import av

from backend.app.jobs import Store
from backend.app.storage import attempt_path, data_root, video_path
from cv.src.contract import Settings, code_hash, sha256, validate_result
from cv.src.pipeline import analyze_video


@contextmanager
def worker_lock(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with (root/"worker.lock").open("a+b") as lock:
        if (root/"worker.lock").stat().st_size == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("Another worker owns this data directory") from None
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


class Worker:
    def __init__(self, store, analyze=analyze_video, remote=None):
        self.store, self.analyze, self.remote = store, analyze, remote
        self.detector_cache = {}

    def detector(self, weights, settings, device):
        key = (sha256(weights), settings.confidence, settings.image_size, device)
        if key not in self.detector_cache:
            from cv.src.detector import Detector
            self.detector_cache.clear()
            self.detector_cache[key] = Detector(weights, settings.confidence, settings.image_size, device)
        return self.detector_cache[key]

    def tick(self):
        job = self.store.claim()
        if job is None:
            return False
        ident = job["id"]
        output = attempt_path(self.store.root, ident, job["attempt"])
        source = video_path(self.store.root, job["video_id"])
        try:
            if job["code_sha256"] != code_hash():
                raise ValueError("Pipeline changed since submission; submit a new job")
            if sha256(source) != job["source_sha256"]:
                raise ValueError("Video hash changed after upload")
            if job["runner"] == "modal":
                if self.remote is None:
                    from cloud.modal_runner import ModalRunner
                    self.remote = ModalRunner()
                result = self.remote.step(job, source, output, self.store)
                if result is None:
                    return True
            else:
                result = self.analyze(source, Settings(**job["settings"]), output,
                                      detector_factory=self.detector,
                                      progress=lambda stage, processed, total: self.store.progress(ident, stage, processed, total))
            validate_result(result)
            for field, expected in (("video_sha256", job["source_sha256"]), ("config_sha256", job["config_sha256"]),
                                    ("model_sha256", job["model_sha256"]), ("code_sha256", job["code_sha256"])):
                if result[field] != expected:
                    raise ValueError(f"Result provenance mismatch: {field}")
            manifest = json.loads((output/"manifest.json").read_text())
            if manifest.get("complete") is not True or manifest["run_id"] != result["run_id"]:
                raise ValueError("Incomplete artifact manifest")
            from backend.app.storage import confined
            for name, digest in manifest["artifacts"].items():
                if sha256(confined(output, name)) != digest:
                    raise ValueError("Artifact hash mismatch")
            self.store.succeed(ident, result, manifest)
        except (ValueError, av.error.FFmpegError) as error:
            self.store.fail(ident, "invalid_input_or_configuration", str(error))
        except FileNotFoundError as error:
            self.store.fail(ident, "missing_input_or_dependency", str(error))
        except (OSError, TimeoutError) as error:
            self.store.fail(ident, "transient_io", str(error), retryable=True)
        except Exception as error:
            self.store.fail(ident, "compute_failure", f"{type(error).__name__}: {error}", retryable=True)
        return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--once", action="store_true")
    p.add_argument("--data", type=Path)
    args = p.parse_args()
    root = args.data or data_root()
    with worker_lock(root):
        store = Store(root)
        store.reconcile()
        worker = Worker(store)
        while True:
            worked = worker.tick()
            if args.once:
                break
            time.sleep(2 if worked else 1)


if __name__ == "__main__":
    main()
