"""Pydantic schemas used by the Cyber Grader MVP backend."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator

Role = Literal["student", "staff", "admin"]


class FlagDefinition(BaseModel):
    """A single lab flag and how to validate it."""

    name: str
    prompt: str
    validator: Literal["exact", "regex", "file_exists"]
    value: Optional[str] = None
    pattern: Optional[str] = Field(default=None, description="Regex pattern when validator=regex")

    @validator("value", always=True)
    def validate_value(cls, value: Optional[str], values: Dict[str, object]) -> Optional[str]:
        validator_type: str = values.get("validator", "")  # type: ignore[assignment]
        if validator_type == "exact" and not value:
            raise ValueError("Exact validator requires a value")
        return value


class LabDefinition(BaseModel):
    id: str
    title: str
    instructions_path: str
    version: str
    flags: List[FlagDefinition]


class FlagSubmission(BaseModel):
    user_id: str
    submission: str


class FlagSubmissionResult(BaseModel):
    user_id: str
    lab_id: str
    flag_name: str
    correct: bool
    submitted_at: datetime


class LabFlagPrompt(BaseModel):
    name: str
    prompt: str
    validator: Literal["exact", "regex", "file_exists"]
    pattern: Optional[str] = None


class LabStatus(BaseModel):
    id: str
    title: str
    version: str
    instructions: str
    score: int
    total_flags: int
    flags: List[LabFlagPrompt]


class QuizChoice(BaseModel):
    key: str
    label: str


class QuizQuestion(BaseModel):
    id: str
    prompt: str
    type: Literal["multiple_choice", "short_answer"]
    choices: List[QuizChoice] = Field(default_factory=list)
    answer: str
    points: int = 1


class QuizDefinition(BaseModel):
    id: str
    title: str
    version: str
    questions: List[QuizQuestion]


class QuizSubmissionAnswer(BaseModel):
    question_id: str
    answer: str


class QuizSubmission(BaseModel):
    user_id: str
    answers: List[QuizSubmissionAnswer]


class QuizSubmissionResult(BaseModel):
    user_id: str
    quiz_id: str
    score: int
    max_score: int
    submitted_at: datetime


class ExamStageDefinition(BaseModel):
    id: str
    title: str
    description: str
    max_score: int = 10


class ExamDefinition(BaseModel):
    id: str
    title: str
    version: str
    stages: List[ExamStageDefinition]


class ExamSubmission(BaseModel):
    user_id: str
    stage_id: str
    answers: Dict[str, str]


class ExamSubmissionResult(BaseModel):
    user_id: str
    exam_id: str
    stage_id: str
    score: int
    max_score: int
    submitted_at: datetime


class GoogleSyncResult(BaseModel):
    status: Literal["success", "skipped", "error"]
    spreadsheet_id: Optional[str] = None
    updated_ranges: List[str] = Field(default_factory=list)
    rows_written: int = 0
    message: Optional[str] = None


class DashboardSummary(BaseModel):
    labs: List[LabStatus]
    quizzes: List[QuizSubmissionResult]
    exams: List[ExamSubmissionResult]


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    user_id: str
    role: Role
    token: str


class SignupRequest(BaseModel):
    email: str
    password: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetPerform(BaseModel):
    token: str
    new_password: str


class MeResponse(BaseModel):
    email: str
    role: Role
    student_id: Optional[str] = None


class StudentIdUpdateRequest(BaseModel):
    student_id: str


class ExportResponse(BaseModel):
    labs: List[FlagSubmissionResult]
    quizzes: List[QuizSubmissionResult]
    exams: List[ExamSubmissionResult]
    google_sync: Optional[GoogleSyncResult] = None


class SyncResponse(BaseModel):
    labs: int
    quizzes: int
    exams: int
    version: str
    content_source: Optional[str] = None
    repo_branch: Optional[str] = None
    refresh_status: Optional[str] = None
    refresh_schedule: Optional[str] = None
    backup_schedule: Optional[str] = None
    refreshed_at: Optional[datetime] = None
