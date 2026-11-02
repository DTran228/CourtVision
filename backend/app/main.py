"""Single-user local API. Inference belongs to `python -m backend.app.worker`."""
import hmac
import os
from pathlib import Path
import uuid

import av
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from backend.app.jobs import Conflict, QueueFull, Store
from backend.app.sessions import get_session, list_sessions, save_review
from backend.app.storage import data_root, identifier, video_path
from cv.src.contract import Settings, sha256
from cv.src.media import MAX_BYTES, inspect_video


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    video_id: str
    runner: str = "local"
    settings: dict = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=100)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0, strict=True)
    events: list[dict]
    complete: bool = Field(strict=True)


def create_app(root=None):
    app = FastAPI(title="CourtVision")

    def store():
        return Store(Path(root).resolve() if root is not None else data_root())

    def authorize(authorization: str | None = Header(default=None)):
        token = os.environ.get("COURTVISION_ACCESS_TOKEN")
        if token and not hmac.compare_digest(authorization or "", f"Bearer {token}"):
            raise HTTPException(401, "Backend access token required")

    @app.exception_handler(KeyError)
    async def not_found(request, error):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(Conflict)
    async def conflict(request, error):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(QueueFull)
    async def full(request, error):
        return JSONResponse(status_code=429, content={"detail": str(error)})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/videos", status_code=201, dependencies=[Depends(authorize)])
    async def upload(request: Request):
        content_type = request.headers.get("content-type", "").split(";")[0]
        if content_type not in {"video/mp4", "video/quicktime", "video/x-matroska"}:
            raise HTTPException(415, "Send raw mp4/mov/mkv bytes with a video Content-Type")
        declared = request.headers.get("content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > MAX_BYTES):
            raise HTTPException(413, "Upload exceeds 250 MiB or invalid Content-Length")
        db = store()
        ident = str(uuid.uuid4())
        path = video_path(db.root, ident)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".upload")
        accepted = False
        try:
            size = 0
            with temp.open("xb") as stream:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise HTTPException(413, "Upload exceeds 250 MiB")
                    stream.write(chunk)
            try:
                media = await run_in_threadpool(inspect_video, temp)
            except (ValueError, av.error.FFmpegError) as error:
                raise HTTPException(422, f"Invalid/unsupported video: {error}") from error
            digest = await run_in_threadpool(sha256, temp)
            temp.replace(path)
            db.add_video(ident, digest, media, content_type)
            accepted = True
            return {"id": ident, "sha256": digest, "media": {k: v for k, v in media.items() if k != "pts_seconds"}}
        finally:
            temp.unlink(missing_ok=True)
            if not accepted:
                path.unlink(missing_ok=True)

    @app.post("/jobs", status_code=202, dependencies=[Depends(authorize)])
    def create_job(body: JobRequest):
        identifier(body.video_id)
        if body.runner not in {"local", "modal"}:
            raise HTTPException(422, "runner must be local or modal")
        if body.runner == "modal" and os.environ.get("COURTVISION_ENABLE_MODAL") != "1":
            raise HTTPException(422, "Modal is disabled; complete cloud setup and budget approval first")
        try:
            settings = Settings(**body.settings)
        except TypeError as error:
            raise HTTPException(422, "Unknown settings") from error
        return store().create(body.video_id, body.runner, settings, body.idempotency_key)

    @app.get("/jobs/{ident}", dependencies=[Depends(authorize)])
    def job(ident: str):
        return store().get(identifier(ident))

    @app.get("/jobs", dependencies=[Depends(authorize)])
    def recent_jobs():
        db = store()
        with db.connect() as connection:
            return [db.job_dict(row) for row in connection.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 50")]

    @app.post("/jobs/{ident}/retry", status_code=202, dependencies=[Depends(authorize)])
    def retry(ident: str):
        return store().retry(identifier(ident))

    @app.get("/sessions", dependencies=[Depends(authorize)])
    def history():
        return list_sessions(store())

    @app.get("/sessions/{ident}", dependencies=[Depends(authorize)])
    def session(ident: str):
        return get_session(store(), identifier(ident))

    @app.patch("/sessions/{ident}/review", dependencies=[Depends(authorize)])
    def review(ident: str, body: ReviewRequest):
        try:
            return save_review(store(), identifier(ident), body.expected_revision, body.events, body.complete)
        except (KeyError, TypeError) as error:
            if isinstance(error, KeyError) and str(error) == "'Session not found'":
                raise
            raise HTTPException(422, "Each event needs id, contact_seconds and outcome") from error

    @app.get("/sessions/{ident}/media", dependencies=[Depends(authorize)])
    def media(ident: str):
        db = store()
        get_session(db, identifier(ident))
        video = db.video(db.get(ident)["video_id"])
        return FileResponse(video_path(db.root, video["id"]), media_type=video["content_type"],
                            headers={"Cache-Control": "private, no-cache"})

    return app


app = create_app()
