import copy
import json
from pathlib import Path
import tempfile
import unittest

from backend.app.jobs import Store, Conflict
from cloud.modal_runner import ModalRunner
from cv.src.contract import Settings, sha256
from cv.src.pipeline import analyze_video
from tests.fixtures import make_video, ScriptedDetector


class FakeTransport:
    def __init__(self):
        self.spawns = 0
        self.polls = []
        self.files = {}
        self.completion = None
        self.fail_spawn = False

    def upload(self, source, remote):
        self.files[remote] = Path(source).read_bytes()

    def spawn(self, payload):
        self.spawns += 1
        if self.fail_spawn:
            raise OSError("dispatch outcome unknown")
        return "fc-synthetic"

    def poll(self, call_id):
        self.polls.append(call_id)
        return self.completion

    def download(self, remote, local):
        Path(local).write_bytes(self.files[remote])


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root/"data")
        self.video = make_video(self.root/"synthetic.mp4")
        import uuid
        self.video_id = str(uuid.uuid4())
        self.store.add_video(self.video_id, sha256(self.video), {}, "video/mp4")
        self.job = self.store.create(self.video_id, "modal", Settings(), "cloud-fixture")
        self.job = self.store.claim()
        self.transport = FakeTransport()
        self.runner = ModalRunner(self.transport)
        self.output = self.root/"retrieved"

    def test_known_call_resumes_after_store_and_runner_restart(self):
        self.assertIsNone(self.runner.step(self.job, self.video, self.output, self.store))
        self.store.reconcile()
        restarted = Store(self.store.root).get(self.job["id"])
        self.assertEqual(restarted["remote_call_id"], "fc-synthetic")
        self.assertIsNone(ModalRunner(self.transport).step(restarted, self.video, self.output, self.store))
        self.assertEqual(self.transport.spawns, 1)
        self.assertEqual(self.transport.polls, ["fc-synthetic", "fc-synthetic"])

    def test_ambiguous_dispatch_cannot_blindly_retry(self):
        self.transport.fail_spawn = True
        with self.assertRaises(OSError):
            self.runner.step(self.job, self.video, self.output, self.store)
        self.store.reconcile()
        failed = self.store.get(self.job["id"])
        self.assertEqual(failed["error"]["type"], "dispatch_ambiguous")
        with self.assertRaises(Conflict):
            self.store.retry(failed["id"])
        self.assertEqual(self.transport.spawns, 1)

    def prepare_output(self):
        weights = self.root/"synthetic.bin"
        weights.write_bytes(b"synthetic")
        source_output = self.root/"produced"
        result = analyze_video(self.video, Settings(), source_output, detector=ScriptedDetector(), weights=weights)
        remote = f"/jobs/{self.job['id']}/attempt-1/output"
        self.transport.files.update({remote+"/"+p.name: p.read_bytes() for p in source_output.iterdir()})
        self.transport.completion = {"manifest_path": remote+"/manifest.json"}
        return result, remote

    def test_artifacts_download_hashes_and_cpu_schema_parity(self):
        expected, _ = self.prepare_output()
        actual = self.runner.step(self.job, self.video, self.output, self.store)
        self.assertEqual(actual, expected)
        self.assertTrue((self.output/"manifest.json").is_file())

    def test_corrupt_or_traversing_cloud_artifacts_rejected(self):
        _, remote = self.prepare_output()
        self.transport.files[remote+"/result.json"] = b"tampered"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.runner.step(self.job, self.video, self.output, self.store)
        manifest = json.loads(self.transport.files[remote+"/manifest.json"])
        manifest["artifacts"] = {"../escape": "a"*64}
        self.transport.files[remote+"/manifest.json"] = json.dumps(manifest).encode()
        saved_job = self.store.get(self.job["id"])
        with self.assertRaisesRegex(ValueError, "artifact name"):
            self.runner.step(saved_job, self.video, self.output, self.store)
