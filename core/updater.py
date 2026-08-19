from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.app_paths import app_dir
from core.version import CURRENT_VERSION


GITHUB_REPO = "H1ls/tiktok-telegram-downloader"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
EXE_ASSET_NAME = "tiktok-telegram-downloader.exe"


@dataclass(frozen=True)
class UpdateResult:
    ok: bool
    message: str
    should_exit: bool = False


def find_git_repo(start_dir: Path | None = None) -> Path | None:
    start = (start_dir or app_dir()).resolve()

    for directory in (start, *start.parents):
        if (directory / ".git").exists():
            return directory

    return None


def git_update(repo_dir: Path | None = None) -> UpdateResult:
    start = (repo_dir or app_dir()).resolve()
    repo = find_git_repo(start)
    if repo is None:
        return UpdateResult(
            False,
            f"Git repository was not found near the application. Start path: {start}",
        )

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


def release_update(current_exe: Path | None = None) -> UpdateResult:
    if not getattr(sys, "frozen", False) and current_exe is None:
        return UpdateResult(False, "Release update is available only for the packaged .exe.")

    exe_path = (current_exe or Path(sys.executable)).resolve()
    try:
        release = _latest_release()
        latest_version = _normalize_version(str(release.get("tag_name", "")))
        current_version = _normalize_version(CURRENT_VERSION)

        if latest_version and _version_key(latest_version) <= _version_key(current_version):
            return UpdateResult(True, f"Already up to date: {CURRENT_VERSION}")

        asset = _find_exe_asset(release)
        if asset is None:
            return UpdateResult(False, f"Release asset was not found: {EXE_ASSET_NAME}")

        download_url = asset.get("browser_download_url")
        if not download_url:
            return UpdateResult(False, "Release asset download URL is empty.")

        downloaded_exe = _download_asset(str(download_url), latest_version or "latest")
        updater_script = _write_windows_updater(exe_path, downloaded_exe)
        subprocess.Popen(
            ["cmd", "/c", str(updater_script)],
            cwd=str(exe_path.parent),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        version_text = latest_version or str(release.get("tag_name", "latest"))
        return UpdateResult(
            True,
            f"Update {version_text} downloaded. Application will restart to finish installation.",
            should_exit=True,
        )
    except HTTPError as exc:
        return UpdateResult(False, f"GitHub release request failed: HTTP {exc.code}")
    except URLError as exc:
        return UpdateResult(False, f"GitHub release request failed: {exc.reason}")
    except OSError as exc:
        return UpdateResult(False, f"Update failed: {exc}")


def update_application() -> UpdateResult:
    if getattr(sys, "frozen", False):
        return release_update()

    return git_update()


def _latest_release() -> dict:
    request = Request(
        LATEST_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "tiktok-telegram-downloader",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _find_exe_asset(release: dict) -> dict | None:
    assets = release.get("assets") or []
    for asset in assets:
        if asset.get("name") == EXE_ASSET_NAME:
            return asset
    for asset in assets:
        name = str(asset.get("name", "")).lower()
        if name.endswith(".exe"):
            return asset
    return None


def _normalize_version(version: str) -> str:
    return version.strip().lstrip("vV")


def _version_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in _normalize_version(version).split("."):
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts)


def _download_asset(download_url: str, version: str) -> Path:
    target_dir = Path(tempfile.gettempdir()) / "tiktok-telegram-downloader-update"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{EXE_ASSET_NAME}.{version}.download"

    request = Request(download_url, headers={"User-Agent": "tiktok-telegram-downloader"})
    with urlopen(request, timeout=120) as response:
        with target.open("wb") as file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                file.write(chunk)

    return target


def _write_windows_updater(current_exe: Path, downloaded_exe: Path) -> Path:
    script = downloaded_exe.with_suffix(".bat")
    script.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal",
                "timeout /t 2 /nobreak >nul",
                f'move /Y "{downloaded_exe}" "{current_exe}" >nul',
                f'start "" "{current_exe}"',
                f'del "%~f0"',
            ]
        ),
        encoding="utf-8",
    )
    return script
