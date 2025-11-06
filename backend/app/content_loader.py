"""Utilities for loading content definitions from the content/ folder."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml

from . import schemas


def load_labs(root: Path) -> List[schemas.LabDefinition]:
    labs: List[schemas.LabDefinition] = []
    for path in sorted((root / "labs").glob("*.yml")):
        data = _read_yaml(path)
        instructions = data.get("instructions", "")
        lab = schemas.LabDefinition(
            id=data["id"],
            title=data["title"],
            version=data.get("version", _default_version()),
            instructions_path=instructions,
            flags=[schemas.FlagDefinition(**flag) for flag in data.get("flags", [])],
        )
        labs.append(lab)
    return labs


def load_quizzes(root: Path) -> List[schemas.QuizDefinition]:
    quizzes: List[schemas.QuizDefinition] = []
    for path in sorted((root / "quizzes").glob("*.yml")):
        data = _read_yaml(path)
        quiz = schemas.QuizDefinition(
            id=data["id"],
            title=data["title"],
            version=data.get("version", _default_version()),
            questions=[schemas.QuizQuestion(**question) for question in data.get("questions", [])],
        )
        quizzes.append(quiz)
    return quizzes


def load_exams(root: Path) -> List[schemas.ExamDefinition]:
    exams: List[schemas.ExamDefinition] = []
    for path in sorted((root / "exams").glob("*.yml")):
        data = _read_yaml(path)
        exam = schemas.ExamDefinition(
            id=data["id"],
            title=data["title"],
            version=data.get("version", _default_version()),
            stages=[schemas.ExamStageDefinition(**stage) for stage in data.get("stages", [])],
        )
        exams.append(exam)
    return exams


def sync_all(
    store,
    root: Path,
    *,
    content_source: Optional[str] = None,
    repo_branch: Optional[str] = None,
    refresh_status: Optional[str] = None,
    refresh_schedule: Optional[str] = None,
    backup_schedule: Optional[str] = None,
    refreshed_at: Optional[datetime] = None,
) -> schemas.SyncResponse:
    labs = load_labs(root)
    quizzes = load_quizzes(root)
    exams = load_exams(root)
    store.set_labs(labs)
    store.set_quizzes(quizzes)
    store.set_exams(exams)
    return schemas.SyncResponse(
        labs=len(labs),
        quizzes=len(quizzes),
        exams=len(exams),
        version=_default_version(),
        content_source=content_source or str(root),
        repo_branch=repo_branch,
        refresh_status=refresh_status,
        refresh_schedule=refresh_schedule,
        backup_schedule=backup_schedule,
        refreshed_at=refreshed_at or datetime.utcnow(),
    )


def _read_yaml(path: Path) -> dict:
    with path.open("r") as handle:
        return yaml.safe_load(handle)


def _default_version() -> str:
    return datetime.utcnow().strftime("%Y.%m.%d")
