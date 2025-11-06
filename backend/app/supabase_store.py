"""Supabase-backed data store that mirrors the in-memory store."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List, Optional

from supabase import Client, create_client

from . import schemas
from .store import InMemoryStore

logger = logging.getLogger(__name__)


class SupabaseStore(InMemoryStore):
    """A store that persists content and submissions to Supabase."""

    def __init__(self, url: str, key: str, content_root) -> None:
        super().__init__(content_root)
        self.url = url
        self.key = key
        self.client: Optional[Client]
        try:
            self.client = create_client(url, key)
        except Exception:  # pragma: no cover - defensive guard for runtime issues
            logger.exception("Failed to create Supabase client; falling back to memory-only mode")
            self.client = None
        if self.client:
            self._hydrate_from_supabase()

    # ------------------------------------------------------------------
    # Content management
    def set_labs(self, labs: Iterable[schemas.LabDefinition]) -> None:  # type: ignore[override]
        super().set_labs(labs)
        self._upsert_many("labs", [self._lab_to_row(lab) for lab in labs])

    def set_quizzes(self, quizzes: Iterable[schemas.QuizDefinition]) -> None:  # type: ignore[override]
        super().set_quizzes(quizzes)
        self._upsert_many("quizzes", [self._quiz_to_row(quiz) for quiz in quizzes])

    def set_exams(self, exams: Iterable[schemas.ExamDefinition]) -> None:  # type: ignore[override]
        super().set_exams(exams)
        self._upsert_many("exams", [self._exam_to_row(exam) for exam in exams])

    # ------------------------------------------------------------------
    # Lab submissions
    def record_flag_submission(
        self, lab_id: str, flag: schemas.FlagDefinition, submission: schemas.FlagSubmission
    ) -> schemas.FlagSubmissionResult:  # type: ignore[override]
        result = super().record_flag_submission(lab_id, flag, submission)
        self._insert("lab_submissions", self._flag_result_to_row(result))
        return result

    # ------------------------------------------------------------------
    # Quiz submissions
    def record_quiz_submission(
        self, quiz: schemas.QuizDefinition, submission: schemas.QuizSubmission
    ) -> schemas.QuizSubmissionResult:  # type: ignore[override]
        result = super().record_quiz_submission(quiz, submission)
        self._insert("quiz_submissions", self._quiz_result_to_row(result))
        return result

    # ------------------------------------------------------------------
    # Exams
    def record_exam_submission(
        self, exam: schemas.ExamDefinition, submission: schemas.ExamSubmission
    ) -> schemas.ExamSubmissionResult:  # type: ignore[override]
        result = super().record_exam_submission(exam, submission)
        self._insert("exam_submissions", self._exam_result_to_row(result))
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    def _hydrate_from_supabase(self) -> None:
        """Populate in-memory caches from Supabase."""

        assert self.client is not None

        def fetch_rows(table: str) -> List[dict]:
            try:
                response = self.client.table(table).select("*").execute()
                return list(response.data or [])
            except Exception:
                logger.exception("Failed to fetch %s from Supabase", table)
                return []

        labs = [self._lab_from_row(row) for row in fetch_rows("labs")]
        quizzes = [self._quiz_from_row(row) for row in fetch_rows("quizzes")]
        exams = [self._exam_from_row(row) for row in fetch_rows("exams")]

        super().set_labs(labs)
        super().set_quizzes(quizzes)
        super().set_exams(exams)

        for row in fetch_rows("lab_submissions"):
            result = self._flag_result_from_row(row)
            key = (result.user_id, result.lab_id, result.flag_name)
            self.lab_attempts[key].append(result)

        for row in fetch_rows("quiz_submissions"):
            result = self._quiz_result_from_row(row)
            self.quiz_attempts[result.user_id].append(result)

        for row in fetch_rows("exam_submissions"):
            result = self._exam_result_from_row(row)
            self.exam_attempts[result.user_id].append(result)

    # Conversion helpers -------------------------------------------------
    def _lab_to_row(self, lab: schemas.LabDefinition) -> dict:
        return {
            "id": lab.id,
            "title": lab.title,
            "version": lab.version,
            "instructions_path": lab.instructions_path,
            "flags": [flag.dict() for flag in lab.flags],
        }

    def _quiz_to_row(self, quiz: schemas.QuizDefinition) -> dict:
        return {
            "id": quiz.id,
            "title": quiz.title,
            "version": quiz.version,
            "questions": [question.dict() for question in quiz.questions],
        }

    def _exam_to_row(self, exam: schemas.ExamDefinition) -> dict:
        return {
            "id": exam.id,
            "title": exam.title,
            "version": exam.version,
            "stages": [stage.dict() for stage in exam.stages],
        }

    def _flag_result_to_row(self, result: schemas.FlagSubmissionResult) -> dict:
        return {
            "user_id": result.user_id,
            "lab_id": result.lab_id,
            "flag_name": result.flag_name,
            "correct": result.correct,
            "submitted_at": result.submitted_at.isoformat(),
        }

    def _quiz_result_to_row(self, result: schemas.QuizSubmissionResult) -> dict:
        return {
            "user_id": result.user_id,
            "quiz_id": result.quiz_id,
            "score": result.score,
            "max_score": result.max_score,
            "submitted_at": result.submitted_at.isoformat(),
        }

    def _exam_result_to_row(self, result: schemas.ExamSubmissionResult) -> dict:
        return {
            "user_id": result.user_id,
            "exam_id": result.exam_id,
            "stage_id": result.stage_id,
            "score": result.score,
            "max_score": result.max_score,
            "submitted_at": result.submitted_at.isoformat(),
        }

    def _lab_from_row(self, row: dict) -> schemas.LabDefinition:
        flags = [schemas.FlagDefinition(**flag) for flag in row.get("flags", [])]
        return schemas.LabDefinition(
            id=row["id"],
            title=row.get("title", row["id"]),
            version=row.get("version", "0.0.0"),
            instructions_path=row.get("instructions_path", ""),
            flags=flags,
        )

    def _quiz_from_row(self, row: dict) -> schemas.QuizDefinition:
        questions = [schemas.QuizQuestion(**question) for question in row.get("questions", [])]
        return schemas.QuizDefinition(
            id=row["id"],
            title=row.get("title", row["id"]),
            version=row.get("version", "0.0.0"),
            questions=questions,
        )

    def _exam_from_row(self, row: dict) -> schemas.ExamDefinition:
        stages = [schemas.ExamStage(**stage) for stage in row.get("stages", [])]
        return schemas.ExamDefinition(
            id=row["id"],
            title=row.get("title", row["id"]),
            version=row.get("version", "0.0.0"),
            stages=stages,
        )

    def _flag_result_from_row(self, row: dict) -> schemas.FlagSubmissionResult:
        return schemas.FlagSubmissionResult(
            user_id=row["user_id"],
            lab_id=row["lab_id"],
            flag_name=row["flag_name"],
            correct=bool(row.get("correct", False)),
            submitted_at=self._parse_datetime(row.get("submitted_at")),
        )

    def _quiz_result_from_row(self, row: dict) -> schemas.QuizSubmissionResult:
        return schemas.QuizSubmissionResult(
            user_id=row["user_id"],
            quiz_id=row["quiz_id"],
            score=int(row.get("score", 0)),
            max_score=int(row.get("max_score", 0)),
            submitted_at=self._parse_datetime(row.get("submitted_at")),
        )

    def _exam_result_from_row(self, row: dict) -> schemas.ExamSubmissionResult:
        return schemas.ExamSubmissionResult(
            user_id=row["user_id"],
            exam_id=row["exam_id"],
            stage_id=row.get("stage_id", ""),
            score=int(row.get("score", 0)),
            max_score=int(row.get("max_score", 0)),
            submitted_at=self._parse_datetime(row.get("submitted_at")),
        )

    def _parse_datetime(self, value: Optional[str]) -> datetime:
        if not value:
            return datetime.utcnow()
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Unable to parse datetime value %s; defaulting to now", value)
            return datetime.utcnow()

    # Supabase operations -----------------------------------------------
    def _upsert_many(self, table: str, rows: Iterable[dict]) -> None:
        if not self.client:
            return
        rows = [row for row in rows]
        if not rows:
            return
        try:
            self.client.table(table).upsert(rows).execute()
        except Exception:
            logger.exception("Failed to upsert rows into %s", table)

    def _insert(self, table: str, row: dict) -> None:
        if not self.client:
            return
        try:
            self.client.table(table).insert(row).execute()
        except Exception:
            logger.exception("Failed to insert row into %s", table)

