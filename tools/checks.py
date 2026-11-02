"""Run existing CV regressions and product/cloud/benchmark offline tests together."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import json
import platform
import sys
import time
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="New JSON evidence file")
    args = parser.parse_args()
    if args.report and args.report.exists():
        parser.error("Report already exists; choose a new file")
    root = Path(__file__).resolve().parents[1]
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([loader.discover(str(root/"cv/tests")), loader.discover(str(root/"tests"), top_level_dir=str(root))])
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if args.report:
        from cv.src.contract import code_hash
        report = {"command": "python -m tools.checks", "utc": datetime.now(timezone.utc).isoformat(),
                  "python": platform.python_version(), "platform": platform.platform(),
                  "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                  "skipped": len(result.skipped), "successful": result.wasSuccessful(),
                  "elapsed_seconds": time.perf_counter()-started, "pipeline_code_sha256": code_hash(),
                  "scope": "Offline unittest suite; no paid cloud or phone interaction"}
        with args.report.open("x", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    sys.exit(not result.wasSuccessful())


if __name__ == "__main__":
    main()
