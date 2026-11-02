"""Review snapshots never mutate the automatic result or benchmark labels."""
import json
import math

from backend.app.jobs import Conflict, now
from cv.src.contract import counts


def get_session(store, ident):
    with store.connect() as db:
        row = db.execute("SELECT * FROM sessions WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise KeyError("Session not found")
        automatic = json.loads(row["automatic"])
        review = db.execute("SELECT body FROM reviews WHERE session_id=? AND revision=?", (ident, row["revision"])).fetchone()
    if review:
        review = json.loads(review[0])
    else:
        review = {"events": [{"id": e["id"], "contact_seconds": e["contact_seconds"], "outcome": e["outcome"],
                               "provenance": "automatic"} for e in automatic["events"]], "complete": False}
    transport = None
    job = store.get(ident)
    if job["runner"] == "modal":
        from backend.app.storage import attempt_path
        path = attempt_path(store.root, ident, job["attempt"])/"transport.json"
        if path.is_file():
            transport = json.loads(path.read_text())
    return {"id": ident, "automatic": automatic, "revision": row["revision"], "review": review,
            "review_summary": counts(review["events"], review["complete"]), "transport_measurements": transport}


def save_review(store, ident, expected_revision, events, complete):
    if type(expected_revision) is not int or expected_revision < 0 or type(complete) is not bool:
        raise ValueError("Invalid revision/completeness")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM sessions WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise KeyError("Session not found")
        if expected_revision != row["revision"]:
            raise Conflict("Review changed; reload before saving")
        automatic = json.loads(row["automatic"])
        originals = {e["id"]: e for e in automatic["events"]}
        ids, clean = set(), []
        if not isinstance(events, list) or len(events) > 500:
            raise ValueError("At most 500 review attempts")
        for event in events:
            ident_event, t, outcome = event["id"], event["contact_seconds"], event["outcome"]
            if (not isinstance(ident_event, str) or not 1 <= len(ident_event) <= 100 or ident_event in ids
                    or type(t) not in {int, float} or not math.isfinite(t)
                    or not 0 <= t <= automatic["timebase"]["duration_seconds"]
                    or outcome not in {"made", "missed", "unknown"}):
                raise ValueError("Invalid/duplicate review attempt")
            ids.add(ident_event)
            original = originals.get(ident_event)
            provenance = "manual_addition" if original is None else (
                "automatic" if (original["outcome"], original["contact_seconds"]) == (outcome, t) else "user_correction")
            clean.append({"id": ident_event, "contact_seconds": t, "outcome": outcome, "provenance": provenance})
        body = {"events": sorted(clean, key=lambda e: (e["contact_seconds"], e["id"])), "complete": complete,
                "removed_automatic_ids": sorted(set(originals)-ids), "provenance": "user_review_not_benchmark_ground_truth"}
        revision = expected_revision+1
        db.execute("INSERT INTO reviews VALUES (?,?,?,?)", (ident, revision, json.dumps(body), now()))
        db.execute("UPDATE sessions SET revision=? WHERE id=?", (revision, ident))
    return get_session(store, ident)


def list_sessions(store):
    with store.connect() as db:
        ids = [r[0] for r in db.execute("SELECT s.id FROM sessions s JOIN jobs j ON s.id=j.id ORDER BY j.created_at DESC LIMIT 50")]
    return [{"id": s["id"], "revision": s["revision"], "automatic_summary": s["automatic"]["summary"],
             "review_summary": s["review_summary"]} for s in (get_session(store, ident) for ident in ids)]
