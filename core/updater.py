from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.app_paths import app_dir
from core.version import CURRENT_VERSION


GITHUB_REPO = "H1ls/tiktok-telegram-downloader"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
EXE_ASSET_NAME = "tiktok-telegram-downloader.exe"
SHA256_ASSET_NAME = "sha256.txt"
ProgressFn = Callable[[str], None]


@dataclass(frozen=True)
class UpdateResult:
    ok: bool
    message: str
    should_exit: bool = False


def _emit_progress(progress: ProgressFn | None, message: str) -> None:
    if progress:
        progress(message)


def find_git_repo(start_dir: Path | None = None) -> Path | None:
    start = (start_dir or app_dir()).resolve()

    for directory in (start, *start.parents):
        if (directory / ".git").exists():
            return directory

    return None


def git_update(repo_dir: Path | None = None, progress: ProgressFn | None = None) -> UpdateResult:
    start = (repo_dir or app_dir()).resolve()
    repo = find_git_repo(start)
    if repo is None:
        return UpdateResult(
            False,
            f"Git repository was not found near the application. Start path: {start}",
        )

    try:
        _emit_progress(progress, "[UPDATE] Fetching Git changes...")
        fetch = subprocess.run(
            ["git", "-C", str(repo), "fetch", "--prune"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if fetch.returncode != 0:
            return UpdateResult(False, (fetch.stderr or fetch.stdout or "git fetch failed").strip())

        _emit_progress(progress, "[UPDATE] Pulling latest Git revision...")
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


def release_update(current_exe: Path | None = None, progress: ProgressFn | None = None) -> UpdateResult:
    if not getattr(sys, "frozen", False) and current_exe is None:
        return UpdateResult(False, "Release update is available only for the packaged .exe.")

    exe_path = (current_exe or Path(sys.executable)).resolve()
    try:
        _emit_progress(progress, "[UPDATE] Checking latest GitHub Release...")
        release = _latest_release()
        latest_version = _normalize_version(str(release.get("tag_name", "")))
        current_version = _normalize_version(CURRENT_VERSION)

        if latest_version and _version_key(latest_version) <= _version_key(current_version):
            return UpdateResult(True, f"Already up to date. Current: {CURRENT_VERSION}, latest: {latest_version}")

        asset = _find_exe_asset(release)
        if asset is None:
            return UpdateResult(False, f"Release asset was not found: {EXE_ASSET_NAME}")

        download_url = asset.get("browser_download_url")
        if not download_url:
            return UpdateResult(False, "Release asset download URL is empty.")

        _emit_progress(progress, f"[UPDATE] Downloading version {latest_version or 'latest'}...")
        downloaded_exe = _download_asset(str(download_url), latest_version or "latest", progress=progress)
        checksum_asset = _find_asset_by_name(release, SHA256_ASSET_NAME)
        if checksum_asset is None:
            return UpdateResult(False, f"Release checksum asset was not found: {SHA256_ASSET_NAME}")

        checksum_url = checksum_asset.get("browser_download_url")
        if not checksum_url:
            return UpdateResult(False, "Release checksum download URL is empty.")

        _emit_progress(progress, "[UPDATE] Verifying downloaded file...")
        expected_hash = _download_expected_sha256(str(checksum_url), EXE_ASSET_NAME)
        actual_hash = _sha256_file(downloaded_exe)
        if actual_hash.lower() != expected_hash.lower():
            downloaded_exe.unlink(missing_ok=True)
            return UpdateResult(False, "Downloaded update hash does not match sha256.txt.")

        _emit_progress(progress, "[UPDATE] Preparing installer script...")
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
    except ValueError as exc:
        return UpdateResult(False, f"Update verification failed: {exc}")
    except OSError as exc:
        return UpdateResult(False, f"Update failed: {exc}")


def update_application(progress: ProgressFn | None = None) -> UpdateResult:
    if getattr(sys, "frozen", False):
        return release_update(progress=progress)

    return git_update(progress=progress)


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
    asset = _find_asset_by_name(release, EXE_ASSET_NAME)
    if asset is not None:
        return asset

    assets = release.get("assets") or []
    for asset in assets:
        name = str(asset.get("name", "")).lower()
        if name.endswith(".exe"):
            return asset
    return None


def _find_asset_by_name(release: dict, asset_name: str) -> dict | None:
    for asset in release.get("assets") or []:
        if asset.get("name") == asset_name:
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


def _download_asset(download_url: str, version: str, progress: ProgressFn | None = None) -> Path:
    target_dir = Path(tempfile.gettempdir()) / "tiktok-telegram-downloader-update"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{EXE_ASSET_NAME}.{version}.download"

    request = Request(download_url, headers={"User-Agent": "tiktok-telegram-downloader"})
    with urlopen(request, timeout=120) as response:
        total_bytes = int(response.headers.get("Content-Length") or 0)
        downloaded_bytes = 0
        last_percent = -1
        with target.open("wb") as file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                file.write(chunk)
                downloaded_bytes += len(chunk)

                if total_bytes > 0:
                    percent = int(downloaded_bytes * 100 / total_bytes)
                    if percent >= last_percent + 10 or percent == 100:
                        last_percent = percent
                        _emit_progress(progress, f"[UPDATE] Downloaded {percent}%")

    return target


def _download_expected_sha256(download_url: str, file_name: str) -> str:
    request = Request(download_url, headers={"User-Agent": "tiktok-telegram-downloader"})
    with urlopen(request, timeout=30) as response:
        content = response.read().decode("utf-8")

    return _parse_sha256(content, file_name)


def _parse_sha256(content: str, file_name: str) -> str:
    fallback_hash = ""
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.replace("*", " ").split()
        candidate = parts[0].lower()
        if len(candidate) == 64 and all(char in "0123456789abcdef" for char in candidate):
            if len(parts) == 1:
                fallback_hash = candidate
                continue
            if any(part.strip() == file_name for part in parts[1:]):
                return candidate

    if fallback_hash:
        return fallback_hash

    raise ValueError(f"sha256 hash for {file_name} was not found")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _write_windows_updater(current_exe: Path, downloaded_exe: Path) -> Path:
    script = downloaded_exe.with_suffix(".bat")
    script.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal",
                "set attempts=0",
                ":retry",
                "set /a attempts+=1",
                f'move /Y "{downloaded_exe}" "{current_exe}" >nul 2>nul',
                "if errorlevel 1 (",
                "  if %attempts% geq 30 exit /b 1",
                "  timeout /t 1 /nobreak >nul",
                "  goto retry",
                ")",
                f'start "" "{current_exe}"',
                f'del "%~f0"',
            ]
        ),
        encoding="utf-8",
    )
    return script
