import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.jobs import Store, Conflict, QueueFull
from backend.app.main import create_app
from backend.app.sessions import get_session
from backend.app.storage import confined, video_path
from backend.app.worker import Worker, worker_lock
from cv.src.contract import Settings, sha256, validate_result
from cv.src.media import inspect_video
from cv.src.pipeline import analyze_video
from tests.fixtures import make_video, ScriptedDetector


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.weights = self.root/"synthetic-weights.bin"
        self.weights.write_bytes(b"synthetic-test-only")
        self.hash = sha256(self.weights)
        self.pinned = patch("backend.app.jobs.MODEL_SHA256", self.hash)
        self.pinned.start()
        self.addCleanup(self.pinned.stop)
        self.video = make_video(self.root/"synthetic.mp4")
        self.data = self.root/"data"
        self.client = TestClient(create_app(self.data))
        self.addCleanup(self.client.close)
        self.store = Store(self.data)

    def upload(self):
        response = self.client.post("/videos", content=self.video.read_bytes(), headers={"Content-Type": "video/mp4"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    def job(self, video=None, key="fixture-key"):
        response = self.client.post("/jobs", json={"video_id": video or self.upload(), "idempotency_key": key})
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    def worker(self):
        def analyze(video, settings, output, **kwargs):
            kwargs.pop("detector_factory", None)
            return analyze_video(video, settings, output, detector=ScriptedDetector(), weights=self.weights, **kwargs)
        return Worker(self.store, analyze=analyze)

    def test_upload_job_worker_review_reload_and_range(self):
        job = self.job()
        self.worker().tick()
        completed = self.client.get(f"/jobs/{job['id']}").json()
        self.assertEqual(completed["status"], "succeeded", completed)
        s = self.client.get(f"/sessions/{job['id']}").json()
        self.assertEqual(s["automatic"]["summary"]["makes"], 1)
        self.assertIsNone(s["review_summary"]["fg_percent"])
        events = [{"id": "manual-1", "contact_seconds": .5, "outcome": "missed"},
                  {**s["review"]["events"][0], "outcome": "missed"}]
        body = {"expected_revision": 0, "events": events, "complete": True}
        saved = self.client.patch(f"/sessions/{job['id']}/review", json=body)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["review_summary"]["fg_percent"], 0)
        self.assertEqual(saved.json()["review_summary"]["candidates"], 2)
        self.assertEqual(self.client.patch(f"/sessions/{job['id']}/review", json=body).status_code, 409)
        fresh = Store(self.data)
        reloaded = get_session(fresh, job["id"])
        self.assertEqual(reloaded["automatic"], s["automatic"])
        self.assertEqual(next(e for e in reloaded["review"]["events"] if e["id"] != "manual-1")["provenance"], "user_correction")
        delete = self.client.patch(f"/sessions/{job['id']}/review", json={"expected_revision": 1, "events": [], "complete": True})
        self.assertEqual(delete.json()["review_summary"]["candidates"], 0)
        self.assertIsNone(delete.json()["review_summary"]["fg_percent"])
        media = self.client.get(f"/sessions/{job['id']}/media", headers={"Range": "bytes=0-31"})
        self.assertEqual(media.status_code, 206)
        self.assertEqual(media.content, self.video.read_bytes()[:32])
        self.assertEqual(len(self.client.get("/sessions").json()), 1)

    def test_idempotency_queue_bound_and_atomic_claim(self):
        video = self.upload()
        first = self.job(video)
        self.assertEqual(first["id"], self.job(video)["id"])
        bad = self.client.post("/jobs", json={"video_id": video, "idempotency_key": "fixture-key", "settings": {"recovery": True}})
        self.assertEqual(bad.status_code, 409)
        for i in range(3):
            self.job(video, f"next-{i}")
        self.assertEqual(self.client.post("/jobs", json={"video_id": video, "idempotency_key": "full"}).status_code, 429)
        claimed = self.store.claim()
        self.assertEqual(claimed["attempt"], 1)
        self.assertEqual(self.store.claim()["id"], claimed["id"])
        with worker_lock(self.data):
            with self.assertRaisesRegex(RuntimeError, "Another worker"):
                with worker_lock(self.data):
                    pass

    def test_restart_interrupt_and_retry_uses_new_attempt_directory(self):
        job = self.job()
        self.store.claim()
        old = self.data/f"jobs/{job['id']}/attempt-1"
        old.mkdir(parents=True)
        (old/"partial.txt").write_text("keep")
        restarted = Store(self.data)
        restarted.reconcile()
        self.assertEqual(restarted.get(job["id"])["error"]["type"], "interrupted")
        self.assertEqual(self.client.post(f"/jobs/{job['id']}/retry").status_code, 202)
        self.worker().tick()
        self.assertEqual(restarted.get(job["id"])["attempt"], 2)
        self.assertEqual((old/"partial.txt").read_text(), "keep")
        self.assertTrue((old.parent/"attempt-2/manifest.json").is_file())

    def test_transient_retry_is_bounded_and_invalid_config_not_retried(self):
        job = self.job()
        def fail(*args, **kwargs):
            raise OSError("synthetic transient IO")
        w = Worker(self.store, analyze=fail)
        for _ in range(4):
            w.tick()
        state = self.store.get(job["id"])
        self.assertEqual((state["status"], state["attempt"]), ("failed", 3))
        self.assertEqual(self.client.post("/jobs", json={"video_id": job["video_id"], "idempotency_key": "bad", "settings": {"image_size": 705}}).status_code, 422)

    def test_invalid_oversized_and_vfr_uploads_leave_no_files(self):
        headers = {"Content-Type": "video/mp4"}
        self.assertEqual(self.client.post("/videos", content=b"not a video", headers=headers).status_code, 422)
        with patch("backend.app.main.MAX_BYTES", 10):
            self.assertEqual(self.client.post("/videos", content=b"x"*11, headers=headers).status_code, 413)
            self.assertEqual(self.client.post("/videos", content=iter([b"x"*6, b"x"*6]), headers=headers).status_code, 413)
        vfr = make_video(self.root/"vfr.mp4", pts=[0, 1, 2, 4, 5, 9, 10, 11])
        self.assertEqual(self.client.post("/videos", content=vfr.read_bytes(), headers=headers).status_code, 422)
        self.assertFalse(list((self.data/"videos").glob("*")))

    def test_interrupted_upload_cleans_temporary_file(self):
        # Exercise ASGI disconnect after a real partial body, not only invalid content.
        messages = iter([{"type": "http.request", "body": b"partial", "more_body": True}, {"type": "http.disconnect"}])
        async def receive():
            return next(messages)
        async def send(message):
            pass
        scope = {"type": "http", "asgi": {"version": "3.0"}, "method": "POST", "scheme": "http", "path": "/videos",
                 "query_string": b"", "headers": [(b"content-type", b"video/mp4")], "server": ("test", 80), "client": ("test", 123)}
        from starlette.requests import ClientDisconnect
        with self.assertRaises(ClientDisconnect):
            asyncio.run(create_app(self.data)(scope, receive, send))
        self.assertFalse(list((self.data/"videos").glob("*")))

    def test_auth_paths_settings_and_review_validation(self):
        with patch.dict(os.environ, {"COURTVISION_ACCESS_TOKEN": "test-token"}):
            self.assertEqual(self.client.get("/sessions").status_code, 401)
            self.assertEqual(self.client.get("/sessions", headers={"Authorization": "Bearer test-token"}).status_code, 200)
        with self.assertRaises(ValueError):
            confined(self.data, "../../elsewhere")
        with self.assertRaises(ValueError):
            Settings(confidence=float("nan"))
        job = self.job()
        self.worker().tick()
        response = self.client.patch(f"/sessions/{job['id']}/review", json={"expected_revision": 0, "events": [{"id": "x", "contact_seconds": 99, "outcome": "made"}], "complete": True})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/jobs/../../../x").status_code, 404)

    def test_result_manifest_and_source_hash_changes_fail_closed(self):
        job = self.job()
        video_path(self.data, job["video_id"]).write_bytes(b"tampered")
        self.worker().tick()
        self.assertEqual(self.store.get(job["id"])["status"], "failed")
        self.assertEqual(self.client.get(f"/sessions/{job['id']}").status_code, 404)

    def test_unknown_review_never_has_definitive_percentage(self):
        job = self.job()
        self.worker().tick()
        body = {"expected_revision": 0, "events": [{"id": "x", "contact_seconds": .5, "outcome": "unknown"}], "complete": True}
        self.assertIsNone(self.client.patch(f"/sessions/{job['id']}/review", json=body).json()["review_summary"]["fg_percent"])

    def test_media_contract_full_decode_and_no_overwrite(self):
        info = inspect_video(self.video)
        self.assertTrue(info["constant_frame_rate"])
        output = self.root/"analysis"
        result = analyze_video(self.video, Settings(), output, detector=ScriptedDetector(), weights=self.weights)
        validate_result(result)
        self.assertEqual(result["events"][0]["outcome"], "made")
        with self.assertRaises(FileExistsError):
            analyze_video(self.video, Settings(), output, detector=ScriptedDetector(), weights=self.weights)
