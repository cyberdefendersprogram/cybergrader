"""FastAPI application implementing the Cyber Grader MVP API."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import content_loader, google_sync, schemas, store

# Always use bundled local content directory for content.
CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "content"
CONTENT_SOURCE = str(CONTENT_ROOT)
CONTENT_REFRESH_SCHEDULE = os.getenv("CONTENT_REFRESH_SCHEDULE", "nightly")

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "public")
DATABASE_BACKUP_SCHEDULE = os.getenv("DATABASE_BACKUP_SCHEDULE", "nightly")

app = FastAPI(title="Cyber Grader MVP", version="0.1.0")

# Ensure important app logs appear under Uvicorn's default logging config
APP_LOG = logging.getLogger("uvicorn.error")


def _create_store() -> store.InMemoryStore:
    if DATABASE_URL:
        try:
            from .postgres_store import PostgresStore

            APP_LOG.info("Database backend: postgres (schema=%s)", DATABASE_SCHEMA)
            return PostgresStore(DATABASE_URL, CONTENT_ROOT, schema=DATABASE_SCHEMA)
        except Exception:
            APP_LOG.exception("Falling back to in-memory store")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if supabase_url and supabase_key:
        try:
            from .supabase_store import SupabaseStore

            APP_LOG.info("Database backend: supabase")
            return SupabaseStore(supabase_url, supabase_key, CONTENT_ROOT)
        except Exception:
            APP_LOG.exception("Falling back to in-memory store")
    APP_LOG.info("Database backend: memory")
    return store.InMemoryStore(CONTENT_ROOT)


data_store = _create_store()

# Allow all origins for the MVP demo environment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    result = content_loader.sync_all(
        data_store,
        CONTENT_ROOT,
        content_source=CONTENT_SOURCE,
        repo_branch=None,
        refresh_status="local",
        refresh_schedule=CONTENT_REFRESH_SCHEDULE,
        backup_schedule=DATABASE_BACKUP_SCHEDULE,
        refreshed_at=None,
    )
    APP_LOG.info(
        "Startup content sync completed: labs=%d, quizzes=%d, exams=%d",
        result.labs,
        result.quizzes,
        result.exams,
    )
    APP_LOG.info("Content source: %s (status=local, branch=None)", CONTENT_SOURCE)


# ---------------------------------------------------------------------------
# Authentication (Supabase simulated)
MOCK_USERS: Dict[str, schemas.Role] = {
    "alice@student.edu": "student",
    "sam@staff.edu": "staff",
    "ada@admin.edu": "admin",
}


@app.post("/auth/login", response_model=schemas.LoginResponse)
async def login(payload: schemas.LoginRequest) -> schemas.LoginResponse:
    role = MOCK_USERS.get(payload.email, "student")
    user_id = payload.email.split("@")[0]
    token = f"demo-token-{user_id}"
    return schemas.LoginResponse(user_id=user_id, role=role, token=token)


# ---------------------------------------------------------------------------
# Dependencies

def get_store() -> store.InMemoryStore:
    return data_store


# ---------------------------------------------------------------------------
# Labs
@app.get("/labs", response_model=list[schemas.LabStatus])
async def list_labs(user_id: str, db: store.InMemoryStore = Depends(get_store)) -> list[schemas.LabStatus]:
    if user_id:
        return db.lab_status_for_user(user_id)
    raise HTTPException(status_code=400, detail="user_id is required")


@app.post("/labs/{lab_id}/flags/{flag_name}", response_model=schemas.FlagSubmissionResult)
async def submit_flag(
    lab_id: str,
    flag_name: str,
    submission: schemas.FlagSubmission,
    db: store.InMemoryStore = Depends(get_store),
) -> schemas.FlagSubmissionResult:
    lab = db.labs.get(lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Unknown lab")
    flag = next((flag for flag in lab.flags if flag.name == flag_name), None)
    if flag is None:
        raise HTTPException(status_code=404, detail="Unknown flag")
    return db.record_flag_submission(lab_id, flag, submission)


# ---------------------------------------------------------------------------
# Quizzes
@app.get("/quizzes", response_model=list[schemas.QuizDefinition])
async def list_quizzes(db: store.InMemoryStore = Depends(get_store)) -> list[schemas.QuizDefinition]:
    return list(db.quizzes.values())


@app.post("/quizzes/{quiz_id}/submit", response_model=schemas.QuizSubmissionResult)
async def submit_quiz(
    quiz_id: str,
    submission: schemas.QuizSubmission,
    db: store.InMemoryStore = Depends(get_store),
) -> schemas.QuizSubmissionResult:
    quiz = db.quizzes.get(quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Unknown quiz")
    return db.record_quiz_submission(quiz, submission)


# ---------------------------------------------------------------------------
# Exams
@app.get("/exams", response_model=list[schemas.ExamDefinition])
async def list_exams(db: store.InMemoryStore = Depends(get_store)) -> list[schemas.ExamDefinition]:
    return list(db.exams.values())


@app.post("/exams/{exam_id}/submit", response_model=schemas.ExamSubmissionResult)
async def submit_exam_stage(
    exam_id: str,
    submission: schemas.ExamSubmission,
    db: store.InMemoryStore = Depends(get_store),
) -> schemas.ExamSubmissionResult:
    exam = db.exams.get(exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Unknown exam")
    return db.record_exam_submission(exam, submission)


# ---------------------------------------------------------------------------
# Dashboard & exports
@app.get("/dashboard/{user_id}", response_model=schemas.DashboardSummary)
async def dashboard(user_id: str, db: store.InMemoryStore = Depends(get_store)) -> schemas.DashboardSummary:
    return db.dashboard_for_user(user_id)


@app.post("/admin/sync", response_model=schemas.SyncResponse)
async def sync_content(
    db: store.InMemoryStore = Depends(get_store),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> schemas.SyncResponse:
    # Minimal role guard for demo auth: only staff/admin may sync
    if x_user_role not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Forbidden: staff/admin role required")
    result = content_loader.sync_all(
        db,
        CONTENT_ROOT,
        content_source=CONTENT_SOURCE,
        repo_branch=None,
        refresh_status="local",
        refresh_schedule=CONTENT_REFRESH_SCHEDULE,
        backup_schedule=DATABASE_BACKUP_SCHEDULE,
        refreshed_at=None,
    )
    APP_LOG.info(
        "Manual sync by role=%s from %s (status=local, branch=None): labs=%d, quizzes=%d, exams=%d",
        x_user_role,
        result.content_source,
        result.labs,
        result.quizzes,
        result.exams,
    )
    return result


@app.get("/admin/export-scores", response_model=schemas.ExportResponse)
async def export_scores(db: store.InMemoryStore = Depends(get_store)) -> schemas.ExportResponse:
    export_payload = db.export_all()
    google_result = google_sync.sync_scores_to_sheet(export_payload)
    return schemas.ExportResponse(**export_payload.dict(), google_sync=google_result)


# ---------------------------------------------------------------------------
# Notes (markdown content)
@app.get("/notes/{note_name}")
async def get_note(note_name: str) -> dict:
    note_path = CONTENT_ROOT / "notes" / f"{note_name}.md"
    if not note_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")
    return {"name": note_name, "body": note_path.read_text()}


@app.get("/health")
async def healthcheck() -> dict:
    return {"status": "ok"}


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_frontend_index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend_app(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
