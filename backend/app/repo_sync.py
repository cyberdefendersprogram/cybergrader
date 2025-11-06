"""Helpers for cloning and refreshing git-backed content repositories."""
from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


RepoSyncResult = Dict[str, object]


def prepare_content_repo(repo_url: str, target_dir: Path, branch: str = "main") -> tuple[Path, RepoSyncResult]:
    """Ensure ``target_dir`` is a clone of ``repo_url`` and return its status."""

    target_dir = target_dir.expanduser().resolve()
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    if (target_dir / ".git").exists():
        status = refresh_repo(target_dir, branch, repo_url)
        return target_dir, status

    if target_dir.exists():
        logger.warning("Target directory %s exists but is not a git repository", target_dir)

    clone_cmd = [
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        branch,
        repo_url,
        str(target_dir),
    ]
    status: RepoSyncResult = {"status": "cloned", "branch": branch, "source": repo_url}
    try:
        subprocess.run(clone_cmd, check=True, capture_output=True)
        status["refreshed_at"] = datetime.utcnow()
    except subprocess.CalledProcessError as exc:  # pragma: no cover - runtime safety
        logger.exception("Failed to clone content repository: %s", exc.stderr.decode("utf-8", "ignore"))
        status["status"] = "error"
        status["message"] = exc.stderr.decode("utf-8", "ignore")
    return target_dir, status


def refresh_repo(target_dir: Path, branch: str = "main", repo_url: Optional[str] = None) -> RepoSyncResult:
    """Pull the latest changes for ``target_dir``."""

    target_dir = target_dir.expanduser().resolve()
    result: RepoSyncResult = {
        "status": "skipped",
        "branch": branch,
        "source": repo_url or str(target_dir),
    }

    if not (target_dir / ".git").exists():
        result["status"] = "missing"
        result["message"] = "Repository has not been cloned yet"
        return result

    commands = [
        ["git", "fetch", "origin", branch],
        ["git", "checkout", branch],
        ["git", "reset", "--hard", f"origin/{branch}"],
    ]

    for command in commands:
        try:
            subprocess.run(command, cwd=target_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:  # pragma: no cover - runtime safety
            logger.exception("Git command failed: %s", " ".join(command))
            result["status"] = "error"
            result["message"] = exc.stderr.decode("utf-8", "ignore")
            return result

    result["status"] = "updated"
    result["refreshed_at"] = datetime.utcnow()
    return result
