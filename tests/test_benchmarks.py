import copy
import unittest

from benchmarks.parity import compare
from benchmarks.summarize import distribution, summarize, failure_summary
from cv.src.contract import counts


class BenchmarkTests(unittest.TestCase):
    def test_small_samples_never_publish_p95(self):
        result = distribution([1, 2, 10])
        self.assertEqual((result["n"], result["median"], result["min"], result["max"]), (3, 2, 1, 10))
        self.assertIsNone(result["p95"])

    def test_tail_summary_shows_sample_count_and_interval(self):
        result = distribution(list(range(1, 101)))
        self.assertEqual(result["p95"], 95)
        self.assertEqual(result["n"], 100)
        self.assertEqual(len(result["p95_bootstrap_95pct_interval"]), 2)

    def test_failures_cold_warm_and_cache_are_separate(self):
        base = {"runner": "modal", "clip_sha256": "a", "config_sha256": "b", "model_sha256": "c", "code_sha256": "d", "hardware": "test-GPU",
                "status": "succeeded", "client_total_seconds": 10, "client_review_ready_seconds": 9,
                "stages": {"pipeline_seconds": 4, "inference_seconds": 3}}
        rows = [{**base, "observed_temperature": "cold"}, {**base, "observed_temperature": "warm"},
                {**base, "observed_temperature": "cold", "status": "failed"}, {**base, "observed_temperature": "cold", "cache_hit": True}]
        result = summarize(rows)
        self.assertEqual(len(result), 2)
        cold = next(r for r in result if r["group"]["observed_temperature"] == "cold")
        self.assertEqual(cold["error_rate"], .5)
        self.assertEqual(cold["timings"]["client_total_seconds"]["n"], 1)

    def test_parity_flags_quality_and_config_differences(self):
        event = {"id": "1", "start_seconds": 1, "contact_seconds": 1.2, "end_seconds": 1.5, "outcome": "made", "evidence": [{"status": "observed"}]}
        a = {"schema_version": 1, **{k: "a"*64 for k in ("video_sha256", "config_sha256", "model_sha256", "code_sha256")},
             "events": [event], "timebase": {"duration_seconds": 2}, "summary": counts([event])}
        b = copy.deepcopy(a)
        b["events"][0]["contact_seconds"] += .01
        self.assertTrue(compare(a, b)["parity_passed"])
        b["events"][0]["outcome"] = "unknown"
        b["summary"] = counts(b["events"])
        self.assertFalse(compare(a, b)["parity_passed"])
        b["config_sha256"] = "b"*64
        self.assertFalse(compare(a, b)["provenance_equal"]["config_sha256"])

    def test_failure_before_runtime_still_counts_against_input(self):
        base = {"runner": "modal", "requested_temperature": "cold", "clip_sha256": "a",
                "config_sha256": "b", "model_sha256": "c", "code_sha256": "d"}
        rows = [{**base, "status": "succeeded", "hardware": "gpu"}, {**base, "status": "failed"}]
        self.assertEqual(failure_summary(rows)[0]["error_rate"], .5)
