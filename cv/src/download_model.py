"""Download the pinned E-BARD model used in our M2 experiments."""

import hashlib
from pathlib import Path
from urllib.request import urlopen

REVISION = "3f4789c4431aa73269f60107a4ba0a5f86b7af8b"
URL = (
    "https://huggingface.co/GabrieleGiudici/E-BARD-detection-models/resolve/"
    + REVISION + "/BODD_yolov8n_0001.pt"
)
SHA256 = "dfe3534d51bb21024d1a400c37f0c1fbf0c8b96ea9a56a5f3cb5454813bfd641"
DESTINATION = Path(__file__).resolve().parents[1] / "models" / "ebard-yolov8n.pt"


def main():
    # A hash identifies the exact file used in our experiment.
    if DESTINATION.exists():
        if hashlib.sha256(DESTINATION.read_bytes()).hexdigest() != SHA256:
            raise SystemExit("Existing weights differ from the documented model; not overwriting.")
        print(f"Model already downloaded and verified: {DESTINATION}")
        return

    print("Downloading E-BARD YOLOv8n weights (about 6 MB)...")
    try:
        with urlopen(URL, timeout=60) as response:
            weights = response.read()
        if hashlib.sha256(weights).hexdigest() != SHA256:
            raise ValueError("Downloaded file does not match the expected SHA-256 hash.")
        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        DESTINATION.write_bytes(weights)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Model download failed: {error}") from error
    print(f"Saved model to {DESTINATION}")


if __name__ == "__main__":
    main()
