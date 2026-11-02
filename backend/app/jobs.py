"""One small SQLite store. Transactions are the durable queue, not RAM tasks."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import uuid

from cv.src.contract import MODEL_SHA256, code_hash


def now():
    return datetime.now(timezone.utc).isoformat()


class Conflict(Exception):
    pass


class QueueFull(Exception):
    pass


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root/"courtvision.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, media TEXT NOT NULL,
                    content_type TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(id),
                    idempotency_key TEXT NOT NULL UNIQUE, request_hash TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed')),
                    stage TEXT NOT NULL, runner TEXT NOT NULL, settings TEXT NOT NULL,
                    config_sha256 TEXT NOT NULL, code_sha256 TEXT NOT NULL, model_sha256 TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
                    processed INTEGER, total INTEGER, error TEXT, remote_call_id TEXT,
                    dispatch_intent INTEGER NOT NULL DEFAULT 0, manifest TEXT);
                CREATE TABLE IF NOT EXISTS attempts (
                    job_id TEXT NOT NULL REFERENCES jobs(id), number INTEGER NOT NULL,
                    started_at TEXT NOT NULL, finished_at TEXT, error TEXT,
                    remote_call_id TEXT, PRIMARY KEY(job_id,number));
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY REFERENCES jobs(id), automatic TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS reviews (
                    session_id TEXT NOT NULL REFERENCES sessions(id), revision INTEGER NOT NULL,
                    body TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(session_id,revision));
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def job_dict(row):
        if row is None:
            raise KeyError("Job not found")
        value = dict(row)
        for field in ("settings", "error", "manifest"):
            if value[field] is not None:
                value[field] = json.loads(value[field])
        value["session_id"] = value["id"] if value["status"] == "succeeded" else None
        return value

    def add_video(self, ident, digest, media, content_type):
        with self.connect() as db:
            db.execute("INSERT INTO videos VALUES (?,?,?,?,?)", (ident, digest, json.dumps(media), content_type, now()))

    def video(self, ident):
        with self.connect() as db:
            row = db.execute("SELECT * FROM videos WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise KeyError("Video not found")
        return {**dict(row), "media": json.loads(row["media"])}

    def create(self, video_id, runner, settings, key):
        from cv.src.contract import json_hash
        request_hash = json_hash({"video_id": video_id, "runner": runner, "settings": settings.to_dict()})
        video = self.video(video_id)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM jobs WHERE idempotency_key=?", (key,)).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise Conflict("Idempotency key already used with a different request")
                return self.job_dict(existing)
            if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0] >= 4:
                raise QueueFull("Queue is full (one active and up to three waiting)")
            ident = str(uuid.uuid4())
            db.execute("""INSERT INTO jobs
                (id,video_id,idempotency_key,request_hash,status,stage,runner,settings,
                 config_sha256,code_sha256,model_sha256,source_sha256,created_at)
                VALUES (?,?,?,?,'queued','queued',?,?,?,?,?,?,?)""",
                       (ident, video_id, key, request_hash, runner, json.dumps(settings.to_dict()),
                        settings.hash, code_hash(), MODEL_SHA256, video["sha256"], now()))
            return self.job_dict(db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone())

    def get(self, ident):
        with self.connect() as db:
            return self.job_dict(db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone())

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # Only an exclusive worker may call this. Reconciliation preserves remote work.
            running = db.execute("SELECT * FROM jobs WHERE status='running' ORDER BY created_at LIMIT 1").fetchone()
            if running:
                return self.job_dict(running)
            row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                return None
            timestamp = now()
            db.execute("""UPDATE jobs SET status='running',stage='starting',attempt=attempt+1,
                started_at=?,finished_at=NULL,error=NULL,processed=NULL,total=NULL,
                remote_call_id=NULL,dispatch_intent=0,manifest=NULL WHERE id=?""", (timestamp, row["id"]))
            db.execute("INSERT INTO attempts(job_id,number,started_at) VALUES (?,?,?)",
                       (row["id"], row["attempt"]+1, timestamp))
            return self.job_dict(db.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())

    def progress(self, ident, stage, processed=None, total=None):
        with self.connect() as db:
            db.execute("UPDATE jobs SET stage=?,processed=?,total=? WHERE id=? AND status='running'",
                       (stage, processed, total, ident))

    def dispatch(self, ident, call_id=None):
        with self.connect() as db:
            db.execute("UPDATE jobs SET dispatch_intent=1,remote_call_id=? WHERE id=? AND status='running'", (call_id, ident))
            if call_id:
                db.execute("UPDATE attempts SET remote_call_id=? WHERE job_id=? AND number=(SELECT attempt FROM jobs WHERE id=?)",
                           (call_id, ident, ident))

    def succeed(self, ident, result, manifest):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            job = db.execute("SELECT * FROM jobs WHERE id=? AND status='running'", (ident,)).fetchone()
            if not job:
                raise Conflict("Job is no longer running")
            db.execute("INSERT INTO sessions(id,automatic) VALUES (?,?)", (ident, json.dumps(result)))
            timestamp = now()
            db.execute("UPDATE jobs SET status='succeeded',stage='complete',finished_at=?,manifest=?,error=NULL WHERE id=?",
                       (timestamp, json.dumps(manifest), ident))
            db.execute("UPDATE attempts SET finished_at=? WHERE job_id=? AND number=?", (timestamp, ident, job["attempt"]))

    def fail(self, ident, kind, message, retryable=False):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            job = db.execute("SELECT * FROM jobs WHERE id=? AND status='running'", (ident,)).fetchone()
            if not job:
                raise Conflict("Job is no longer running")
            # Two automatic retries after the first attempt; remote dispatch is never retried blindly.
            retry = retryable and job["attempt"] < 3 and not job["dispatch_intent"]
            error = json.dumps({"type": kind, "message": message, "retryable": retryable})
            timestamp = now()
            db.execute("UPDATE jobs SET status=?,stage=?,error=?,finished_at=? WHERE id=?",
                       ("queued" if retry else "failed", "retry_pending" if retry else "failed", error, timestamp, ident))
            db.execute("UPDATE attempts SET error=?,finished_at=? WHERE job_id=? AND number=?",
                       (error, timestamp, ident, job["attempt"]))

    def reconcile(self):
        with self.connect() as db:
            jobs = [dict(r) for r in db.execute("SELECT * FROM jobs WHERE status='running'")]
        for job in jobs:
            if job["runner"] == "modal" and job["remote_call_id"]:
                continue  # Resume the same remote call, not a new attempt.
            kind = "dispatch_ambiguous" if job["dispatch_intent"] else "interrupted"
            self.fail(job["id"], kind, "Worker stopped; inspect attempt artifacts before explicit retry")

    def retry(self, ident):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
            if row is None:
                raise KeyError("Job not found")
            if row["status"] != "failed":
                raise Conflict("Only failed jobs can be retried")
            if row["dispatch_intent"]:
                raise Conflict("Remote work may have executed; inspect/cancel call before making a new analysis request")
            if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0] >= 4:
                raise QueueFull("Queue is full")
            # Freeze versions: a changed pipeline requires a new job, not an old metadata label.
            if row["code_sha256"] != code_hash():
                raise Conflict("Pipeline changed; submit a new analysis request")
            db.execute("UPDATE jobs SET status='queued',stage='queued' WHERE id=?", (ident,))
        return self.get(ident)
