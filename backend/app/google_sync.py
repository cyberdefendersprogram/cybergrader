"""Utility helpers for synchronizing exports to Google Sheets."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List

from . import schemas

try:  # pragma: no cover - optional dependency path
    from google.oauth2.service_account import Credentials  # type: ignore
    from googleapiclient.discovery import build  # type: ignore
    from googleapiclient.errors import HttpError  # type: ignore
except Exception:  # pragma: no cover - import guard for environments without Google SDK
    Credentials = None  # type: ignore[assignment]
    build = None  # type: ignore[assignment]
    HttpError = Exception  # type: ignore[assignment]


SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
LAB_HEADER = ["user_id", "lab_id", "flag_name", "correct", "submitted_at"]
QUIZ_HEADER = ["user_id", "quiz_id", "score", "max_score", "submitted_at"]
EXAM_HEADER = ["user_id", "exam_id", "stage_id", "score", "max_score", "submitted_at"]


def _load_service_account() -> Credentials | None:
    """Load a Google service account from environment configuration."""

    if Credentials is None:
        return None

    raw_credentials = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw_credentials:
        return None

    credentials_payload = None
    if raw_credentials.startswith("{"):
        credentials_payload = json.loads(raw_credentials)
    else:
        candidate_path = Path(raw_credentials)
        if candidate_path.exists():
            credentials_payload = json.loads(candidate_path.read_text())
        else:
            raise FileNotFoundError(
                "GOOGLE_SERVICE_ACCOUNT_JSON must be a JSON string or a path to a JSON file"
            )

    return Credentials.from_service_account_info(credentials_payload, scopes=[SHEETS_SCOPE])


def _build_rows(export: schemas.ExportResponse) -> tuple[List[List[str]], List[List[str]], List[List[str]]]:
    labs = [LAB_HEADER]
    for record in export.labs:
        labs.append(
            [
                record.user_id,
                record.lab_id,
                record.flag_name,
                "TRUE" if record.correct else "FALSE",
                record.submitted_at.isoformat(),
            ]
        )

    quizzes = [QUIZ_HEADER]
    for record in export.quizzes:
        quizzes.append(
            [
                record.user_id,
                record.quiz_id,
                str(record.score),
                str(record.max_score),
                record.submitted_at.isoformat(),
            ]
        )

    exams = [EXAM_HEADER]
    for record in export.exams:
        exams.append(
            [
                record.user_id,
                record.exam_id,
                record.stage_id,
                str(record.score),
                str(record.max_score),
                record.submitted_at.isoformat(),
            ]
        )

    return labs, quizzes, exams


def sync_scores_to_sheet(export: schemas.ExportResponse) -> schemas.GoogleSyncResult:
    """Push the export payload to the configured Google Sheet."""

    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip()
    if not spreadsheet_id:
        return schemas.GoogleSyncResult(
            status="skipped",
            message="GOOGLE_SHEETS_SPREADSHEET_ID is not configured",
        )

    credentials = _load_service_account()
    if credentials is None:
        return schemas.GoogleSyncResult(
            status="skipped",
            spreadsheet_id=spreadsheet_id,
            message="Google credentials not available; install google-api-python-client and set GOOGLE_SERVICE_ACCOUNT_JSON",
        )

    if build is None:
        return schemas.GoogleSyncResult(
            status="skipped",
            spreadsheet_id=spreadsheet_id,
            message="google-api-python-client is not installed",
        )

    labs_rows, quiz_rows, exam_rows = _build_rows(export)
    timestamp = datetime.utcnow().isoformat(timespec="seconds")

    try:
        service = build("sheets", "v4", credentials=credentials)
        values_service = service.spreadsheets().values()
        body = {
            "valueInputOption": "RAW",
            "data": [
                {"range": "Labs!A1", "values": labs_rows},
                {"range": "Quizzes!A1", "values": quiz_rows},
                {"range": "Exams!A1", "values": exam_rows},
                {
                    "range": "Meta!A1",
                    "values": [["last_synced_at", timestamp]],
                },
            ],
        }
        response = values_service.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    except HttpError as exc:  # pragma: no cover - depends on remote service
        return schemas.GoogleSyncResult(
            status="error",
            spreadsheet_id=spreadsheet_id,
            message=f"Google Sheets API error: {exc}",
        )
    except Exception as exc:  # pragma: no cover - defensive
        return schemas.GoogleSyncResult(
            status="error",
            spreadsheet_id=spreadsheet_id,
            message=f"Failed to sync to Google Sheets: {exc}",
        )

    total_rows = sum(len(rows) - 1 for rows in (labs_rows, quiz_rows, exam_rows))
    updated_ranges = response.get("responses", [])
    rendered_ranges = [entry.get("updatedRange", "") for entry in updated_ranges]

    return schemas.GoogleSyncResult(
        status="success",
        spreadsheet_id=spreadsheet_id,
        updated_ranges=[rng for rng in rendered_ranges if rng],
        rows_written=total_rows,
        message=f"Synced {total_rows} rows to Google Sheets",
    )
