from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from core.app_paths import app_dir


@dataclass(frozen=True)
class UpdateResult:
    ok: bool
    message: str


def git_update(repo_dir: Path | None = None) -> UpdateResult:
    repo = (repo_dir or app_dir()).resolve()
    if not (repo / ".git").exists():
        return UpdateResult(False, "Git repository was not found near the application.")

    try:
        fetch = subprocess.run(
            ["git", "-C", str(repo), "fetch", "--prune"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if fetch.returncode != 0:
            return UpdateResult(False, (fetch.stderr or fetch.stdout or "git fetch failed").strip())

        pull = subprocess.run(
            ["git", "-C", str(repo), "pull", "--ff-only"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (pull.stdout or pull.stderr or "").strip()
        if pull.returncode != 0:
            return UpdateResult(False, output or "git pull failed")
        return UpdateResult(True, output or "Already up to date.")
    except FileNotFoundError:
        return UpdateResult(False, "Git executable was not found in PATH.")
    except subprocess.TimeoutExpired:
        return UpdateResult(False, "Git update timed out.")
