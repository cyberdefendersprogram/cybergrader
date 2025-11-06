"""FastAPI application implementing the Cyber Grader MVP API."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import content_loader, google_sync, schemas, store

DEFAULT_CONTENT_REPO = "https://github.com/cyberdefenders/cis53.git"
CONTENT_REPO_URL = os.getenv("CONTENT_REPO_URL", DEFAULT_CONTENT_REPO)
CONTENT_REPO_BRANCH = os.getenv("CONTENT_REPO_BRANCH", "main")
CONTENT_REPO_PATH = Path(os.getenv("CONTENT_REPO_PATH", "/tmp/cis53-content"))
CONTENT_REFRESH_SCHEDULE = os.getenv("CONTENT_REFRESH_SCHEDULE", "nightly")

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "public")
DATABASE_BACKUP_SCHEDULE = os.getenv("DATABASE_BACKUP_SCHEDULE", "nightly")

if CONTENT_REPO_URL:
    from . import repo_sync

    CONTENT_ROOT, CONTENT_REPO_STATUS = repo_sync.prepare_content_repo(
        CONTENT_REPO_URL, CONTENT_REPO_PATH, CONTENT_REPO_BRANCH
    )
    if CONTENT_REPO_STATUS.get("status") == "error":
        logging.getLogger(__name__).warning(
            "Falling back to bundled content after repo clone failure"
        )
        CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "content"
        CONTENT_SOURCE = str(CONTENT_ROOT)
        CONTENT_REPO_STATUS = {"status": "local", "source": CONTENT_SOURCE, "branch": None}
        repo_sync = None  # type: ignore[assignment]
    else:
        CONTENT_SOURCE = CONTENT_REPO_URL
else:
    CONTENT_ROOT = Path(os.getenv("CONTENT_ROOT", Path(__file__).resolve().parent.parent.parent / "content"))
    CONTENT_REPO_STATUS = {"status": "local", "source": str(CONTENT_ROOT), "branch": None}
    CONTENT_SOURCE = str(CONTENT_ROOT)
    repo_sync = None  # type: ignore[assignment]

app = FastAPI(title="Cyber Grader MVP", version="0.1.0")


def _create_store() -> store.InMemoryStore:
    if DATABASE_URL:
        try:
            from .postgres_store import PostgresStore

            return PostgresStore(DATABASE_URL, CONTENT_ROOT, schema=DATABASE_SCHEMA)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Falling back to in-memory store")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if supabase_url and supabase_key:
        try:
            from .supabase_store import SupabaseStore

            return SupabaseStore(supabase_url, supabase_key, CONTENT_ROOT)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Falling back to in-memory store")
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
    content_loader.sync_all(
        data_store,
        CONTENT_ROOT,
        content_source=CONTENT_SOURCE,
        repo_branch=CONTENT_REPO_STATUS.get("branch"),
        refresh_status=CONTENT_REPO_STATUS.get("status"),
        refresh_schedule=CONTENT_REFRESH_SCHEDULE,
        backup_schedule=DATABASE_BACKUP_SCHEDULE,
        refreshed_at=CONTENT_REPO_STATUS.get("refreshed_at"),
    )


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
async def sync_content(db: store.InMemoryStore = Depends(get_store)) -> schemas.SyncResponse:
    repo_status: Optional[dict] = None
    if CONTENT_REPO_URL and repo_sync:
        repo_status = repo_sync.refresh_repo(CONTENT_ROOT, CONTENT_REPO_BRANCH, CONTENT_REPO_URL)
        if repo_status:
            CONTENT_REPO_STATUS.update({k: v for k, v in repo_status.items() if v is not None})
    return content_loader.sync_all(
        db,
        CONTENT_ROOT,
        content_source=CONTENT_SOURCE,
        repo_branch=(repo_status or CONTENT_REPO_STATUS).get("branch"),
        refresh_status=(repo_status or CONTENT_REPO_STATUS).get("status"),
        refresh_schedule=CONTENT_REFRESH_SCHEDULE,
        backup_schedule=DATABASE_BACKUP_SCHEDULE,
        refreshed_at=(repo_status or CONTENT_REPO_STATUS).get("refreshed_at"),
    )


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
