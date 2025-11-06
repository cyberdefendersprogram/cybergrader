"""A tiny in-memory data store to back the MVP FastAPI service."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from . import schemas


class InMemoryStore:
    """Stores synced content and user submissions in memory."""

    def __init__(self, content_root: Path) -> None:
        self.content_root = content_root
        self.labs: Dict[str, schemas.LabDefinition] = {}
        self.quizzes: Dict[str, schemas.QuizDefinition] = {}
        self.exams: Dict[str, schemas.ExamDefinition] = {}
        self.lab_attempts: Dict[Tuple[str, str, str], List[schemas.FlagSubmissionResult]] = defaultdict(list)
        self.quiz_attempts: Dict[str, List[schemas.QuizSubmissionResult]] = defaultdict(list)
        self.exam_attempts: Dict[str, List[schemas.ExamSubmissionResult]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Content management
    def set_labs(self, labs: Iterable[schemas.LabDefinition]) -> None:
        self.labs = {lab.id: lab for lab in labs}

    def set_quizzes(self, quizzes: Iterable[schemas.QuizDefinition]) -> None:
        self.quizzes = {quiz.id: quiz for quiz in quizzes}

    def set_exams(self, exams: Iterable[schemas.ExamDefinition]) -> None:
        self.exams = {exam.id: exam for exam in exams}

    # ------------------------------------------------------------------
    # Lab submissions
    def record_flag_submission(
        self, lab_id: str, flag: schemas.FlagDefinition, submission: schemas.FlagSubmission
    ) -> schemas.FlagSubmissionResult:
        correct = self._validate_flag(flag, submission.submission)
        result = schemas.FlagSubmissionResult(
            user_id=submission.user_id,
            lab_id=lab_id,
            flag_name=flag.name,
            correct=correct,
            submitted_at=datetime.utcnow(),
        )
        key = (submission.user_id, lab_id, flag.name)
        self.lab_attempts[key].append(result)
        return result

    def lab_status_for_user(self, user_id: str) -> List[schemas.LabStatus]:
        statuses: List[schemas.LabStatus] = []
        for lab in self.labs.values():
            instructions_path = self.content_root / lab.instructions_path
            instructions = instructions_path.read_text() if instructions_path.exists() else "Instructions not found"
            score = self._lab_score(user_id, lab.id)
            statuses.append(
                schemas.LabStatus(
                    id=lab.id,
                    title=lab.title,
                    version=lab.version,
                    instructions=instructions,
                    score=score,
                    total_flags=len(lab.flags),
                    flags=[
                        schemas.LabFlagPrompt(
                            name=flag.name,
                            prompt=flag.prompt,
                            validator=flag.validator,
                            pattern=flag.pattern,
                        )
                        for flag in lab.flags
                    ],
                )
            )
        return statuses

    def _lab_score(self, user_id: str, lab_id: str) -> int:
        correct_flags = set()
        for flag in self.labs[lab_id].flags:
            key = (user_id, lab_id, flag.name)
            attempts = self.lab_attempts.get(key, [])
            if any(attempt.correct for attempt in attempts):
                correct_flags.add(flag.name)
        return len(correct_flags)

    # ------------------------------------------------------------------
    # Quiz submissions
    def record_quiz_submission(self, quiz: schemas.QuizDefinition, submission: schemas.QuizSubmission) -> schemas.QuizSubmissionResult:
        max_score = sum(question.points for question in quiz.questions)
        answer_map = {answer.question_id: answer.answer for answer in submission.answers}
        score = 0
        for question in quiz.questions:
            submitted_answer = answer_map.get(question.id, "")
            if question.type == "multiple_choice":
                if submitted_answer == question.answer:
                    score += question.points
            elif submitted_answer.strip().lower() == question.answer.strip().lower():
                score += question.points
        result = schemas.QuizSubmissionResult(
            user_id=submission.user_id,
            quiz_id=quiz.id,
            score=score,
            max_score=max_score,
            submitted_at=datetime.utcnow(),
        )
        self.quiz_attempts[submission.user_id].append(result)
        return result

    def quiz_history_for_user(self, user_id: str) -> List[schemas.QuizSubmissionResult]:
        return list(self.quiz_attempts.get(user_id, []))

    # ------------------------------------------------------------------
    # Exams
    def record_exam_submission(self, exam: schemas.ExamDefinition, submission: schemas.ExamSubmission) -> schemas.ExamSubmissionResult:
        stage = next((stage for stage in exam.stages if stage.id == submission.stage_id), None)
        if stage is None:
            raise ValueError("Unknown exam stage")
        # For the MVP we give full credit when any answer is provided.
        answered = any(answer.strip() for answer in submission.answers.values())
        score = stage.max_score if answered else 0
        result = schemas.ExamSubmissionResult(
            user_id=submission.user_id,
            exam_id=exam.id,
            stage_id=stage.id,
            score=score,
            max_score=stage.max_score,
            submitted_at=datetime.utcnow(),
        )
        self.exam_attempts[submission.user_id].append(result)
        return result

    def exam_history_for_user(self, user_id: str) -> List[schemas.ExamSubmissionResult]:
        return list(self.exam_attempts.get(user_id, []))

    # ------------------------------------------------------------------
    # Exporting & dashboard
    def export_all(self) -> schemas.ExportResponse:
        lab_results = [attempt for attempts in self.lab_attempts.values() for attempt in attempts]
        quiz_results = [attempt for attempts in self.quiz_attempts.values() for attempt in attempts]
        exam_results = [attempt for attempts in self.exam_attempts.values() for attempt in attempts]
        return schemas.ExportResponse(labs=lab_results, quizzes=quiz_results, exams=exam_results)

    def dashboard_for_user(self, user_id: str) -> schemas.DashboardSummary:
        return schemas.DashboardSummary(
            labs=self.lab_status_for_user(user_id),
            quizzes=self.quiz_history_for_user(user_id),
            exams=self.exam_history_for_user(user_id),
        )

    # ------------------------------------------------------------------
    def _validate_flag(self, flag: schemas.FlagDefinition, submission: str) -> bool:
        if flag.validator == "exact":
            return submission.strip() == (flag.value or "").strip()
        if flag.validator == "regex" and flag.pattern:
            import re

            return re.fullmatch(flag.pattern, submission.strip()) is not None
        if flag.validator == "file_exists":
            target_path = self.content_root / submission
            return target_path.exists()
        return False

