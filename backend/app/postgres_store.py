"""PostgreSQL-backed data store supporting Aurora and Hetzner deployments."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Iterable

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from . import schemas
from .store import InMemoryStore

logger = logging.getLogger("uvicorn.error")


class PostgresStore(InMemoryStore):
    """A store that mirrors the in-memory behaviour while persisting to Postgres."""

    def __init__(self, dsn: str, content_root, schema: str = "public") -> None:
        super().__init__(content_root)
        self.dsn = dsn
        self.schema = schema
        self.enabled = False

        try:
            self._ensure_schema()
            labs, quizzes, exams = self._hydrate_from_postgres()
            self.enabled = True
            logger.info(
                "Postgres store enabled (schema=%s); hydrated labs=%d, quizzes=%d, exams=%d",
                self.schema,
                len(labs),
                len(quizzes),
                len(exams),
            )
        except Exception:  # pragma: no cover - defensive guard for runtime issues
            logger.exception("Postgres store initialisation failed; operating in-memory only")

    # ------------------------------------------------------------------
    # Content management
    def set_labs(self, labs: Iterable[schemas.LabDefinition]) -> None:  # type: ignore[override]
        super().set_labs(labs)
        if not self.enabled:
            return
        self._upsert_many(
            "labs",
            [
                (
                    lab.id,
                    lab.title,
                    lab.version,
                    lab.instructions_path,
                    json.dumps([flag.dict() for flag in lab.flags]),
                )
                for lab in labs
            ],
            columns=("id", "title", "version", "instructions_path", "flags"),
        )

    def set_quizzes(self, quizzes: Iterable[schemas.QuizDefinition]) -> None:  # type: ignore[override]
        super().set_quizzes(quizzes)
        if not self.enabled:
            return
        self._upsert_many(
            "quizzes",
            [
                (
                    quiz.id,
                    quiz.title,
                    quiz.version,
                    json.dumps([question.dict() for question in quiz.questions]),
                )
                for quiz in quizzes
            ],
            columns=("id", "title", "version", "questions"),
        )

    def set_exams(self, exams: Iterable[schemas.ExamDefinition]) -> None:  # type: ignore[override]
        super().set_exams(exams)
        if not self.enabled:
            return
        self._upsert_many(
            "exams",
            [
                (
                    exam.id,
                    exam.title,
                    exam.version,
                    json.dumps([stage.dict() for stage in exam.stages]),
                )
                for exam in exams
            ],
            columns=("id", "title", "version", "stages"),
        )

    # ------------------------------------------------------------------
    # Lab submissions
    def record_flag_submission(
        self, lab_id: str, flag: schemas.FlagDefinition, submission: schemas.FlagSubmission
    ) -> schemas.FlagSubmissionResult:  # type: ignore[override]
        result = super().record_flag_submission(lab_id, flag, submission)
        if not self.enabled:
            return result
        self._insert(
            "lab_submissions",
            (
                result.user_id,
                result.lab_id,
                result.flag_name,
                result.correct,
                self._ensure_timezone(result.submitted_at),
            ),
            columns=("user_id", "lab_id", "flag_name", "correct", "submitted_at"),
        )
        return result

    # ------------------------------------------------------------------
    # Quiz submissions
    def record_quiz_submission(
        self, quiz: schemas.QuizDefinition, submission: schemas.QuizSubmission
    ) -> schemas.QuizSubmissionResult:  # type: ignore[override]
        result = super().record_quiz_submission(quiz, submission)
        if not self.enabled:
            return result
        self._insert(
            "quiz_submissions",
            (
                result.user_id,
                result.quiz_id,
                result.score,
                result.max_score,
                self._ensure_timezone(result.submitted_at),
            ),
            columns=("user_id", "quiz_id", "score", "max_score", "submitted_at"),
        )
        return result

    # ------------------------------------------------------------------
    # Exams
    def record_exam_submission(
        self, exam: schemas.ExamDefinition, submission: schemas.ExamSubmission
    ) -> schemas.ExamSubmissionResult:  # type: ignore[override]
        result = super().record_exam_submission(exam, submission)
        if not self.enabled:
            return result
        self._insert(
            "exam_submissions",
            (
                result.user_id,
                result.exam_id,
                result.stage_id,
                result.score,
                result.max_score,
                self._ensure_timezone(result.submitted_at),
            ),
            columns=("user_id", "exam_id", "stage_id", "score", "max_score", "submitted_at"),
        )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    def _ensure_schema(self) -> None:
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE SCHEMA IF NOT EXISTS {}" ).format(sql.Identifier(self.schema))
                )
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {} (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            version TEXT NOT NULL,
                            instructions_path TEXT NOT NULL,
                            flags JSONB NOT NULL
                        )
                        """
                    ).format(self._qualified("labs"))
                )
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {} (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            version TEXT NOT NULL,
                            questions JSONB NOT NULL
                        )
                        """
                    ).format(self._qualified("quizzes"))
                )
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {} (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            version TEXT NOT NULL,
                            stages JSONB NOT NULL
                        )
                        """
                    ).format(self._qualified("exams"))
                )
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {} (
                            id BIGSERIAL PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            lab_id TEXT NOT NULL,
                            flag_name TEXT NOT NULL,
                            correct BOOLEAN NOT NULL,
                            submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    ).format(self._qualified("lab_submissions"))
                )
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {} (
                            id BIGSERIAL PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            quiz_id TEXT NOT NULL,
                            score INTEGER NOT NULL,
                            max_score INTEGER NOT NULL,
                            submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    ).format(self._qualified("quiz_submissions"))
                )
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {} (
                            id BIGSERIAL PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            exam_id TEXT NOT NULL,
                            stage_id TEXT NOT NULL,
                            score INTEGER NOT NULL,
                            max_score INTEGER NOT NULL,
                            submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    ).format(self._qualified("exam_submissions"))
                )
                # Users and password reset tokens for authentication
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {} (
                            id TEXT PRIMARY KEY,
                            email TEXT UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            role TEXT NOT NULL DEFAULT 'student',
                            student_id TEXT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    ).format(self._qualified("users"))
                )
                # Ensure uniqueness of non-null student_id values
                cur.execute(
                    sql.SQL(
                        "CREATE UNIQUE INDEX IF NOT EXISTS {} ON {} (student_id) WHERE student_id IS NOT NULL"
                    ).format(
                        sql.Identifier(f"{self.schema}_users_student_id_unique"),
                        self._qualified("users"),
                    )
                )
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {} (
                            id BIGSERIAL PRIMARY KEY,
                            user_id TEXT NOT NULL REFERENCES {}(id) ON DELETE CASCADE,
                            token TEXT UNIQUE NOT NULL,
                            expires_at TIMESTAMPTZ NOT NULL,
                            used_at TIMESTAMPTZ NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    ).format(self._qualified("password_reset_tokens"), self._qualified("users"))
                )

    def _hydrate_from_postgres(self) -> tuple[list[schemas.LabDefinition], list[schemas.QuizDefinition], list[schemas.ExamDefinition]]:
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SELECT * FROM {}" ).format(self._qualified("labs")))
                labs = [self._lab_from_row(row) for row in cur.fetchall()]

                cur.execute(sql.SQL("SELECT * FROM {}" ).format(self._qualified("quizzes")))
                quizzes = [self._quiz_from_row(row) for row in cur.fetchall()]

                cur.execute(sql.SQL("SELECT * FROM {}" ).format(self._qualified("exams")))
                exams = [self._exam_from_row(row) for row in cur.fetchall()]

            super().set_labs(labs)
            super().set_quizzes(quizzes)
            super().set_exams(exams)

            with conn.cursor() as cur:
                cur.execute(sql.SQL("SELECT * FROM {} ORDER BY submitted_at" ).format(self._qualified("lab_submissions")))
                for row in cur.fetchall():
                    result = self._flag_result_from_row(row)
                    key = (result.user_id, result.lab_id, result.flag_name)
                    self.lab_attempts[key].append(result)

                cur.execute(sql.SQL("SELECT * FROM {} ORDER BY submitted_at" ).format(self._qualified("quiz_submissions")))
                for row in cur.fetchall():
                    result = self._quiz_result_from_row(row)
                    self.quiz_attempts[result.user_id].append(result)

                cur.execute(sql.SQL("SELECT * FROM {} ORDER BY submitted_at" ).format(self._qualified("exam_submissions")))
                for row in cur.fetchall():
                    result = self._exam_result_from_row(row)
                    self.exam_attempts[result.user_id].append(result)
        return labs, quizzes, exams

    def _upsert_many(self, table: str, rows: Iterable[tuple], columns: tuple[str, ...]) -> None:
        rows = list(rows)
        if not rows:
            return

        assignments = sql.SQL(", ").join(
            sql.SQL("{0} = EXCLUDED.{0}").format(sql.Identifier(column)) for column in columns[1:]
        )

        insert_sql = sql.SQL(
            "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT (id) DO UPDATE SET {}"
        ).format(
            self._qualified(table),
            sql.SQL(", ").join(sql.Identifier(column) for column in columns),
            sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            assignments,
        )

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                for row in rows:
                    cur.execute(insert_sql, row)
            conn.commit()
        logger.info("Upserted %d row(s) into %s", len(rows), table)

    def _insert(self, table: str, row: tuple, columns: tuple[str, ...]) -> None:
        insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            self._qualified(table),
            sql.SQL(", ").join(sql.Identifier(column) for column in columns),
            sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        )
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(insert_sql, row)
            conn.commit()
        logger.debug("Inserted row into %s", table)

    # Conversion helpers -------------------------------------------------
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
        stages = [schemas.ExamStageDefinition(**stage) for stage in row.get("stages", [])]
        return schemas.ExamDefinition(
            id=row["id"],
            title=row.get("title", row["id"]),
            version=row.get("version", "0.0.0"),
            stages=stages,
        )

    def _flag_result_from_row(self, row: dict) -> schemas.FlagSubmissionResult:
        submitted_at = row.get("submitted_at")
        if isinstance(submitted_at, datetime):
            submitted = submitted_at.replace(tzinfo=submitted_at.tzinfo or timezone.utc)
        else:
            submitted = datetime.utcnow().replace(tzinfo=timezone.utc)
        return schemas.FlagSubmissionResult(
            user_id=row["user_id"],
            lab_id=row["lab_id"],
            flag_name=row["flag_name"],
            correct=bool(row.get("correct", False)),
            submitted_at=submitted,
        )

    def _quiz_result_from_row(self, row: dict) -> schemas.QuizSubmissionResult:
        submitted_at = row.get("submitted_at")
        if isinstance(submitted_at, datetime):
            submitted = submitted_at.replace(tzinfo=submitted_at.tzinfo or timezone.utc)
        else:
            submitted = datetime.utcnow().replace(tzinfo=timezone.utc)
        return schemas.QuizSubmissionResult(
            user_id=row["user_id"],
            quiz_id=row["quiz_id"],
            score=int(row.get("score", 0)),
            max_score=int(row.get("max_score", 0)),
            submitted_at=submitted,
        )

    def _exam_result_from_row(self, row: dict) -> schemas.ExamSubmissionResult:
        submitted_at = row.get("submitted_at")
        if isinstance(submitted_at, datetime):
            submitted = submitted_at.replace(tzinfo=submitted_at.tzinfo or timezone.utc)
        else:
            submitted = datetime.utcnow().replace(tzinfo=timezone.utc)
        return schemas.ExamSubmissionResult(
            user_id=row["user_id"],
            exam_id=row["exam_id"],
            stage_id=row.get("stage_id", ""),
            score=int(row.get("score", 0)),
            max_score=int(row.get("max_score", 0)),
            submitted_at=submitted,
        )

    def _qualified(self, table: str) -> sql.Composed:
        return sql.SQL("{}.{}" ).format(sql.Identifier(self.schema), sql.Identifier(table))

    def _ensure_timezone(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
