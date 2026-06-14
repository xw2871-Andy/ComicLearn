"""FastAPI app for the ComicLearn studio.

Routes
------
GET    /                          → SPA shell (index.html)
GET    /static/*                  → JS/CSS/assets
GET    /assets/runs/*             → per-run panel images / PDFs (auth required)
GET    /assets/showcase/*         → ships-with-repo showcase assets (public)

POST   /api/signup                {email, display_name, password}
POST   /api/login                 {email, password}
POST   /api/logout
GET    /api/me

GET    /api/projects              list current user's projects
POST   /api/projects              create
PATCH  /api/projects/{id}         update
DELETE /api/projects/{id}

GET    /api/projects/{id}/runs    list runs for project
POST   /api/projects/{id}/runs    enqueue + start a run
GET    /api/runs/{id}             status + events replay
GET    /api/runs/{id}/stream      SSE event stream
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import auth, db, runner

# Resolve key paths.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
OUTPUT_ROOT = Path(
    os.environ.get("DEFAULT_OUTPUT_DIR", PROJECT_ROOT / "outputs")
).expanduser()
SAMPLES_ROOT = PROJECT_ROOT / "samples"

OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

# .env loader (no python-dotenv dep needed).
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    for _line in ENV_PATH.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))


APP_VERSION = "0.4.0"

app = FastAPI(title="ComicLearn Studio", version=APP_VERSION)

# Initialize DB on first import so the first request doesn't pay the cost.
db.init_db()


# --------------------------- helpers / dependencies ------------------------- #


def require_user(c2c_sess: str | None = Cookie(default=None)) -> dict:
    user = auth.resolve_session(c2c_sess)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


def public_user_dict(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
    }


def _set_session_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        key=auth.SESSION_COOKIE,
        value=token,
        max_age=auth.SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )


# ----- usage budget (hosted, owner-pays protection) ------------------------ #

MAX_RUNS_PER_USER_PER_DAY = int(os.environ.get("MAX_RUNS_PER_USER_PER_DAY", "10"))
MAX_RUNS_GLOBAL_PER_DAY = int(os.environ.get("MAX_RUNS_GLOBAL_PER_DAY", "100"))


def enforce_run_budget(user: dict) -> None:
    """Cap generation runs per rolling 24h — per user and globally — so a
    hosted deployment on the owner's keys can't be drained. Set either env var
    to 0 to disable that cap (the default for local use is effectively open)."""

    since = db.now_ts() - 86_400
    if MAX_RUNS_PER_USER_PER_DAY > 0:
        used = db.count_runs_since(since, user_id=int(user["id"]))
        if used >= MAX_RUNS_PER_USER_PER_DAY:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Daily limit reached ({MAX_RUNS_PER_USER_PER_DAY} comics/day). "
                "Please try again tomorrow.",
            )
    if MAX_RUNS_GLOBAL_PER_DAY > 0:
        total = db.count_runs_since(since)
        if total >= MAX_RUNS_GLOBAL_PER_DAY:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "The studio is at today's global capacity. Please try again later.",
            )


# --------------------------- auth routes ----------------------------------- #


class SignupBody(BaseModel):
    email: str
    display_name: str | None = None
    password: str
    access_code: str | None = None


class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/api/signup")
def api_signup(body: SignupBody, response: Response) -> dict:
    try:
        uid, token = auth.signup(
            body.email, body.display_name or "", body.password, body.access_code
        )
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc)) from exc
    _set_session_cookie(response, token)
    user = db.get_user(uid)
    return {"user": public_user_dict(user)}  # type: ignore[arg-type]


@app.post("/api/login")
def api_login(body: LoginBody, response: Response) -> dict:
    try:
        uid, token = auth.login(body.email, body.password)
    except auth.AuthError as exc:
        raise HTTPException(401, str(exc)) from exc
    _set_session_cookie(response, token)
    user = db.get_user(uid)
    return {"user": public_user_dict(user)}  # type: ignore[arg-type]


@app.post("/api/logout")
def api_logout(response: Response, c2c_sess: str | None = Cookie(default=None)) -> dict:
    auth.logout(c2c_sess)
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
def api_me(user: dict = Depends(require_user)) -> dict:
    return {"user": public_user_dict(user)}


# --------------------------- project routes -------------------------------- #


class ProjectCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    grade_level: str = "AP Calculus AB"
    cast: list[str] = Field(default_factory=lambda: ["Doraemon", "Nobita"])
    setting_hint: str | None = None


class ProjectPatchBody(BaseModel):
    name: str | None = None
    grade_level: str | None = None
    cast: list[str] | None = None
    setting_hint: str | None = None


@app.get("/api/projects")
def api_list_projects(user: dict = Depends(require_user)) -> dict:
    return {"projects": db.list_projects(int(user["id"]))}


@app.post("/api/projects")
def api_create_project(body: ProjectCreateBody, user: dict = Depends(require_user)) -> dict:
    proj = db.create_project(
        user_id=int(user["id"]),
        name=body.name.strip(),
        grade_level=body.grade_level.strip() or "AP Calculus AB",
        cast=[c.strip() for c in body.cast if c.strip()][:6] or ["Doraemon", "Nobita"],
        setting_hint=(body.setting_hint or "").strip() or None,
    )
    return {"project": proj}


@app.patch("/api/projects/{project_id}")
def api_patch_project(
    project_id: str, body: ProjectPatchBody, user: dict = Depends(require_user)
) -> dict:
    fields: dict[str, Any] = {}
    for k in ("name", "grade_level", "cast", "setting_hint"):
        v = getattr(body, k)
        if v is not None:
            fields[k] = v
    proj = db.update_project(project_id, int(user["id"]), **fields)
    if proj is None:
        raise HTTPException(404, "Project not found")
    return {"project": proj}


@app.delete("/api/projects/{project_id}")
def api_delete_project(project_id: str, user: dict = Depends(require_user)) -> dict:
    if not db.delete_project(project_id, int(user["id"])):
        raise HTTPException(404, "Project not found")
    return {"ok": True}


# --------------------------- run routes ------------------------------------ #


class RunCreateBody(BaseModel):
    source_kind: str = Field(pattern="^(topic|markdown)$")
    title: str = Field(min_length=1, max_length=160)
    grade_level: str | None = None
    source_text: str | None = None
    backend: str = Field(default="gemini", pattern="^(svg|gemini|mock)$")
    provider: str = Field(default="auto", pattern="^(auto|anthropic|gemini)$")
    image_quality: str = Field(default="2K", pattern="^(1K|2K|4K)$")
    run_qa: bool = True


@app.get("/api/projects/{project_id}/runs")
def api_list_runs(project_id: str, user: dict = Depends(require_user)) -> dict:
    if db.get_project(project_id, int(user["id"])) is None:
        raise HTTPException(404, "Project not found")
    return {"runs": db.list_runs(project_id, int(user["id"]))}


@app.post("/api/projects/{project_id}/runs")
def api_create_run(
    project_id: str, body: RunCreateBody, user: dict = Depends(require_user)
) -> dict:
    proj = db.get_project(project_id, int(user["id"]))
    if proj is None:
        raise HTTPException(404, "Project not found")
    enforce_run_budget(user)
    grade = (body.grade_level or proj["grade_level"] or "").strip()

    run = db.create_run(
        project_id=project_id,
        user_id=int(user["id"]),
        title=body.title.strip(),
        grade_level=grade,
        source_kind=body.source_kind,
        source_text=body.source_text,
        backend=body.backend,
        provider=body.provider,
        run_qa=body.run_qa,
        image_quality=body.image_quality,
    )

    if body.backend == "mock":
        runner.start_mock_run(
            run_id=run["id"], title=body.title, output_root=OUTPUT_ROOT
        )
    else:
        runner.start_run(
            run_id=run["id"],
            title=body.title.strip(),
            grade_level=grade,
            source_kind=body.source_kind,
            source_text=body.source_text,
            backend=body.backend,
            provider=body.provider,
            run_qa=body.run_qa,
            cast=proj["cast"],
            setting_hint=proj.get("setting_hint"),
            output_root=OUTPUT_ROOT,
            image_quality=body.image_quality,
        )
    return {"run": run}


@app.post("/api/projects/{project_id}/runs/pdf")
async def api_create_pdf_run(
    project_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    grade_level: str = Form(""),
    pages: str = Form(""),
    backend: str = Form("gemini"),
    provider: str = Form("auto"),
    image_quality: str = Form("2K"),
    run_qa: bool = Form(True),
    user: dict = Depends(require_user),
) -> dict:
    """Create a run from an uploaded textbook/worksheet PDF.

    The PDF is stored under outputs/runs/_uploads/, then extracted (Mathpix
    OCR when configured, else pdfplumber) and fed through the same
    worksheet → storyboard → pages pipeline.
    """

    proj = db.get_project(project_id, int(user["id"]))
    if proj is None:
        raise HTTPException(404, "Project not found")
    enforce_run_budget(user)
    title = title.strip()
    if not title:
        raise HTTPException(400, "Topic / title is required")
    if backend not in {"svg", "gemini", "mock"}:
        raise HTTPException(400, "Bad backend")
    if provider not in {"auto", "anthropic", "gemini"}:
        raise HTTPException(400, "Bad provider")
    if image_quality not in {"1K", "2K", "4K"}:
        raise HTTPException(400, "Bad image quality")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a .pdf file")

    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(400, "PDF is too large (max 50 MB)")

    page_range: tuple[int, int] | None = None
    pages = (pages or "").strip()
    if pages:
        try:
            lo, hi = pages.split("-", 1)
            page_range = (int(lo), int(hi))
        except ValueError:
            raise HTTPException(400, "Pages must look like '380-400'")

    grade = (grade_level or proj["grade_level"] or "").strip()

    run = db.create_run(
        project_id=project_id,
        user_id=int(user["id"]),
        title=title,
        grade_level=grade,
        source_kind="pdf",
        source_text=f"[uploaded pdf] {file.filename}"
        + (f" · pages {pages}" if pages else ""),
        backend=backend,
        provider=provider,
        run_qa=run_qa,
        image_quality=image_quality,
    )

    upload_dir = OUTPUT_ROOT / "runs" / "_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / f"{run['id']}.pdf"
    pdf_path.write_bytes(contents)

    if backend == "mock":
        runner.start_mock_run(
            run_id=run["id"], title=title, output_root=OUTPUT_ROOT
        )
        return {"run": run}

    runner.start_run(
        run_id=run["id"],
        title=title,
        grade_level=grade,
        source_kind="pdf",
        source_text=None,
        backend=backend,
        provider=provider,
        run_qa=run_qa,
        cast=proj["cast"],
        setting_hint=proj.get("setting_hint"),
        output_root=OUTPUT_ROOT,
        source_path=str(pdf_path),
        page_range=page_range,
        image_quality=image_quality,
    )
    return {"run": run}


class ReviseBody(BaseModel):
    scene: int = Field(ge=1, le=12)
    feedback: str = Field(min_length=3, max_length=2000)


@app.post("/api/runs/{run_id}/revise")
def api_revise_run(
    run_id: str, body: ReviseBody, user: dict = Depends(require_user)
) -> dict:
    """Teacher feedback loop: re-draw one page of a finished run with the
    teacher's notes, re-QA it, and recompile the PDF."""

    run = db.get_run(run_id, int(user["id"]))
    if run is None:
        raise HTTPException(404, "Run not found")
    enforce_run_budget(user)
    if run["status"] != "done":
        raise HTTPException(409, "Run is not finished yet — wait for it to complete.")
    if run["backend"] == "mock":
        raise HTTPException(400, "Mock runs can't be revised (no real pages).")
    if not run.get("run_dir") or not Path(run["run_dir"]).exists():
        raise HTTPException(410, "This run's files are no longer on disk.")

    runner.start_revision(
        run_id=run_id,
        scene_number=body.scene,
        feedback=body.feedback.strip(),
        output_root=OUTPUT_ROOT,
        provider=run.get("provider") or "auto",
        backend=run["backend"],
        run_qa=bool(run.get("run_qa", 1)),
    )
    return {"ok": True, "run_id": run_id, "scene": body.scene}


@app.get("/api/runs/{run_id}")
def api_get_run(
    run_id: str,
    after_seq: int = 0,
    user: dict = Depends(require_user),
) -> dict:
    run = db.get_run(run_id, int(user["id"]))
    if run is None:
        raise HTTPException(404, "Run not found")
    events = db.list_events(run_id, after_seq=after_seq)
    return {"run": run, "events": events}


@app.get("/api/runs/{run_id}/stream")
async def api_stream_run(
    run_id: str,
    user: dict = Depends(require_user),
):
    run = db.get_run(run_id, int(user["id"]))
    if run is None:
        raise HTTPException(404, "Run not found")

    async def gen():
        # 1) replay any past events from the DB so late subscribers catch up.
        last_seq = 0
        for ev in db.list_events(run_id):
            yield _sse(ev)
            last_seq = max(last_seq, int(ev["seq"]))

        if run["status"] in ("done", "error"):
            yield _sse({"kind": "eof", "seq": last_seq + 1, "payload": {}})
            return

        # 2) live subscription.
        q = runner.BUS.subscribe(run_id)
        try:
            loop = asyncio.get_event_loop()
            while True:
                ev = await loop.run_in_executor(None, _q_get, q)
                if ev is None:
                    break
                yield _sse(ev)
                if ev.get("kind") in ("done", "error"):
                    break
        finally:
            runner.BUS.unsubscribe(run_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream")


def _q_get(q, timeout: float = 30.0):
    import queue as _q

    try:
        return q.get(timeout=timeout)
    except _q.Empty:
        # heartbeat
        return {"kind": "heartbeat", "seq": 0, "payload": {}}


def _sse(event: dict) -> str:
    data = json.dumps(event, default=str)
    return f"event: {event.get('kind','message')}\ndata: {data}\n\n"


# --------------------------- asset serving --------------------------------- #


@app.get("/assets/runs/{rest:path}")
def assets_runs(rest: str, user: dict = Depends(require_user)) -> FileResponse:
    safe = (OUTPUT_ROOT / "runs" / rest).resolve()
    if OUTPUT_ROOT not in safe.parents and safe != OUTPUT_ROOT:
        raise HTTPException(400, "Bad path")
    if not safe.exists() or safe.is_dir():
        raise HTTPException(404, "Not found")
    return FileResponse(safe)


@app.get("/assets/showcase/{rest:path}")
def assets_showcase(rest: str) -> FileResponse:
    safe = (SAMPLES_ROOT / "showcase" / rest).resolve()
    if SAMPLES_ROOT not in safe.parents and safe != SAMPLES_ROOT:
        raise HTTPException(400, "Bad path")
    if not safe.exists() or safe.is_dir():
        raise HTTPException(404, "Not found")
    return FileResponse(safe)


# --------------------------- static SPA ------------------------------------ #

# Mount static last so /api/* routes win.
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return HTMLResponse(
            "<h1>ComicLearn Studio</h1>"
            "<p>Frontend not built yet. Add web/static/index.html.</p>",
            status_code=500,
        )
    return HTMLResponse(index.read_text(encoding="utf-8"))


# Healthcheck.
@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "version": APP_VERSION,
        "output_root": str(OUTPUT_ROOT),
        "db_path": str(db.DB_PATH),
    }


# Capability discovery for the frontend (which keys are configured).
@app.get("/api/config")
def api_config() -> dict:
    return {
        "app_version": APP_VERSION,
        "providers": {
            "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "gemini": bool(os.environ.get("GEMINI_API_KEY")),
        },
        "mathpix": bool(
            os.environ.get("MATHPIX_APP_ID") and os.environ.get("MATHPIX_APP_KEY")
        ),
        "default_backend": os.environ.get("IMAGE_BACKEND", "gemini"),
        "image_model": os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image"),
    }


# Fallback 404 JSON for /api/*.
@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
    raise exc
