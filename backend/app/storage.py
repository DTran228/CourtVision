"""Server-created names only. The API never accepts filesystem paths or URLs."""
import os
from pathlib import Path
import uuid


def data_root():
    root = Path(os.environ.get("COURTVISION_DATA", Path(__file__).resolve().parents[2]/"data"))
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def confined(root, relative):
    root = Path(root).resolve()
    path = (root/relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Path escapes data directory")
    return path


def identifier(value):
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid identifier") from None
    return value


def video_path(root, ident):
    return confined(root, f"videos/{identifier(ident)}.mp4")


def attempt_path(root, ident, attempt):
    if type(attempt) is not int or attempt < 1:
        raise ValueError("Invalid attempt")
    return confined(root, f"jobs/{identifier(ident)}/attempt-{attempt}")
