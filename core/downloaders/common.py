from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from curl_cffi import requests

from core.app_paths import app_dir
from core.config import AppConfig

TIKTOK_RE = re.compile(
    r"(https?://(?:www\.|m\.)?tiktok\.com/[^\s]+|https?://vt\.tiktok\.com/[^\s]+)",
    re.IGNORECASE,
)

TIKTOK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


def cookies_path() -> Path:
    return app_dir() / "cookies.txt"


def extract_tiktok_url(text: str) -> str | None:
    if not text:
        return None
    match = TIKTOK_RE.search(text.strip())
    if not match:
        return None
    return match.group(1).rstrip(").,;\"'<>]}")


def expand_url(url: str, attempts: int = 5, timeout: float = 60) -> str:
    url = (url or "").strip()
    if not url:
        return url

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                url,
                headers=TIKTOK_HEADERS,
                allow_redirects=True,
                timeout=timeout,
                impersonate="chrome",
            )
            if response.url:
                return response.url
        except Exception as exc:
            last_error = exc
            time.sleep(2 * attempt)

    if last_error:
        raise RuntimeError(f"Could not expand TikTok URL: {last_error}") from last_error
    return url


def is_tiktok_photo(url: str) -> bool:
    value = (url or "").lower()
    return "/photo/" in value or ("photo" in value and "/video/" not in value)


def has_audio_stream(path: str | Path) -> bool:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
            check=False,
            **subprocess_kwargs_hidden(),
        )
        return bool((result.stdout or "").strip())
    except Exception:
        return False


def subprocess_kwargs_hidden() -> dict:
    if not hasattr(subprocess, "STARTUPINFO"):
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {"startupinfo": startupinfo, "creationflags": subprocess.CREATE_NO_WINDOW}


def user_max_height(cfg: AppConfig, user_id: int) -> int | None:
    user = (cfg.users or {}).get(str(user_id), {})
    defaults = cfg.defaults or {}
    value = user.get("max_height", defaults.get("max_height"))
    try:
        return int(value) if value is not None else None
    except Exception:
        return None
