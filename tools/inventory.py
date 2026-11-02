"""Read-only local inventory; never uploads footage or reads credential values."""
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess

from cv.src.media import inspect_video
from cv.src.contract import sha256


def main():
    root = Path(__file__).resolve().parents[1]
    result = {"python": platform.python_version(), "platform": platform.platform(),
              "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
              "sources": {str(p.relative_to(root)): sha256(p) for p in
                          [*root.glob("cv/src/*.py"), *root.glob("cv/experiments/*"),
                           root / "README.md", root / "cv/M3.md"]},
              "models": {p.name: sha256(p) for p in (root / "cv/models").glob("*.pt")},
              "videos": []}
    for p in (root / "cv/sample_videos").iterdir():
        if p.suffix not in {".mp4", ".mkv", ".mov"}:
            continue
        row = {"path": str(p.relative_to(root)), "sha256": sha256(p), "bytes": p.stat().st_size}
        try:
            row["media"] = inspect_video(p, enforce_limits=False)
        except ValueError as e:
            row["inspection_error"] = str(e)
        result["videos"].append(row)
    out = root / "docs/evidence/initial-inventory.json"
    if out.exists():
        raise SystemExit("Inventory already exists; preserve the original evidence.")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
