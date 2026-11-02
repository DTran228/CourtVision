"""Small shared result/config contract for CPU, cloud, API and evaluation."""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = 1
MODEL_SHA256 = "dfe3534d51bb21024d1a400c37f0c1fbf0c8b96ea9a56a5f3cb5454813bfd641"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def code_hash():
    return json_hash({p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))})


@dataclass(frozen=True)
class Settings:
    confidence: float = 0.25
    image_size: int = 704
    tracker: str = "baseline"
    recovery: bool = False

    def __post_init__(self):
        if isinstance(self.confidence, bool) or not 0 < self.confidence <= 1:
            raise ValueError("confidence must be finite, >0 and <=1")
        if type(self.image_size) is not int or not 320 <= self.image_size <= 1280 or self.image_size % 32:
            raise ValueError("image_size must be a multiple of 32 in [320,1280]")
        if self.tracker not in {"baseline", "candidate"} or type(self.recovery) is not bool:
            raise ValueError("Unsupported tracker/recovery setting")

    def to_dict(self):
        return asdict(self)

    @property
    def hash(self):
        return json_hash(self.to_dict())


def counts(events, complete=False):
    made = sum(e["outcome"] == "made" for e in events)
    missed = sum(e["outcome"] == "missed" for e in events)
    unknown = len(events) - made - missed
    return {"candidates": len(events), "makes": made, "misses": missed, "unknown": unknown,
            "review_complete": complete,
            "fg_percent": 100 * made / len(events) if complete and events and not unknown else None}


def validate_result(result):
    if result["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported result schema")
    for key in ("video_sha256", "model_sha256", "config_sha256", "code_sha256"):
        if len(result[key]) != 64 or any(c not in "0123456789abcdef" for c in result[key]):
            raise ValueError(f"Invalid {key}")
    ids = set()
    duration = result["timebase"]["duration_seconds"]
    for event in result["events"]:
        if event["id"] in ids or event["outcome"] not in {"made", "missed", "unknown"}:
            raise ValueError("Duplicate event or invalid outcome")
        ids.add(event["id"])
        start, contact, end = (event[k] for k in ("start_seconds", "contact_seconds", "end_seconds"))
        if not 0 <= start <= contact <= end <= duration:
            raise ValueError("Invalid event time bounds")
        if not event["evidence"] or any(p.get("status") != "observed" for p in event["evidence"]):
            raise ValueError("Events require observed evidence")
    if result["summary"] != counts(result["events"]):
        raise ValueError("Automatic summary mismatch")
    return result
