"""Freeze allowed local footage metadata/hashes before benchmarking; no uploads."""
import argparse
import json
from pathlib import Path

from cv.src.contract import Settings, sha256
from cv.src.media import inspect_video


def load_manifest(path, pilot=False):
    data = json.loads(Path(path).read_text())
    if data["schema_version"] != 1:
        raise ValueError("Unsupported manifest")
    Settings(**data["settings"])
    clips = data["clips"]
    if not clips or (len(clips) < 5 and not pilot):
        raise ValueError("At least five varied clips required; use --pilot for explicitly limited trials")
    hashes = set()
    for clip in clips:
        path = Path(clip["path"])
        if not path.is_absolute():
            path = Path(data["root"])/path
        if sha256(path) != clip["sha256"] or clip["sha256"] in hashes:
            raise ValueError("Changed or duplicate input")
        hashes.add(clip["sha256"])
        clip["resolved_path"] = str(path.resolve())
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--videos", type=Path, nargs="+", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    clips = []
    for path in args.videos:
        media = inspect_video(path)
        clips.append({"path": str(path.resolve()), "sha256": sha256(path), "bytes": path.stat().st_size,
                      "media": {k: v for k, v in media.items() if k != "pts_seconds"}})
    result = {"schema_version": 1, "root": str(Path.cwd()), "settings": Settings().to_dict(), "clips": clips,
              "note": "Input manifest only; not labels, timing results or footage upload permission"}
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote {len(clips)} clip(s); full benchmark requires at least five varied inputs")


if __name__ == "__main__":
    main()
