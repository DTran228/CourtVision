"""Copy measured local smoke results without copying private footage/databases."""
import json
from pathlib import Path
import platform
import importlib.metadata

from cv.src.contract import sha256


def copy_once(source, target):
    source, target = Path(source), Path(target)
    with target.open("xb") as stream:
        stream.write(source.read_bytes())
    return {"file": str(target), "sha256": sha256(target), "source": str(source)}


def main():
    root = Path("docs/evidence")
    sources = {}
    for name, directory in (("20secplay", "smoke-20secplay-real"), ("shootout", "smoke-shootout-real")):
        summary = Path("data")/directory/"demo.json"
        result_path = Path(json.loads(summary.read_text())["result_path"])
        sources[f"{name}_smoke"] = copy_once(summary, root/f"real-{name}-smoke.json")
        sources[f"{name}_result"] = copy_once(result_path, root/f"real-{name}-result.json")
        sources[f"{name}_manifest"] = copy_once(result_path.parent/"manifest.json", root/f"real-{name}-manifest.json")
    sources["http_smoke"] = copy_once("data/http-smoke/http-smoke.json", root/"loopback-smoke.json")
    sources["http_summary"] = copy_once("data/http-smoke-summary/summary.json", root/"loopback-benchmark-summary.json")
    sources["http_csv"] = copy_once("data/http-smoke-summary/runs.csv", root/"loopback-runs.csv")
    packages = ["torch", "torchvision", "ultralytics", "opencv-python", "numpy", "av", "fastapi", "starlette", "uvicorn", "modal"]
    evidence = {"platform": platform.platform(), "processor": platform.processor(), "python": platform.python_version(),
                "versions": {name: importlib.metadata.version(name) for name in packages}, "sources": sources,
                "note": "Single uncontrolled local smoke runs. No phone latency, held-out accuracy, GPU speedup or user impact is established."}
    with (root/"smoke-evidence-index.json").open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2)
    print("Copied measured smoke evidence (no videos or databases)")


if __name__ == "__main__":
    main()
