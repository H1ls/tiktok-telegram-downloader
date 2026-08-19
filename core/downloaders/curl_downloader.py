from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path

from curl_cffi import requests

from core.config import AppConfig
from core.downloaders.base import ProgressFn
from core.downloaders.common import TIKTOK_HEADERS, expand_url, is_tiktok_photo
from core.paths import get_user_dir


class CurlTikTokDownloader:
    name = "curl_cffi"

    def download(self, url: str, cfg: AppConfig, user_id: int, progress: ProgressFn | None = None) -> Path:
        if not url:
            raise ValueError("Empty url")

        if progress:
            progress("expanding short URL")
        expanded = expand_url(url)
        if is_tiktok_photo(expanded):
            raise RuntimeError("TikTok photo posts are not supported")

        user_dir = get_user_dir(cfg, user_id)
        if progress:
            progress("loading TikTok page")
        session, page = self._get_page(expanded)
        if progress:
            progress("extracting direct video URL")
        video_url = self._extract_video_url(page)

        video_id_match = re.search(r"/video/(\d+)", expanded)
        video_id = video_id_match.group(1) if video_id_match else str(int(time.time()))
        output_path = user_dir / f"tiktok_{video_id}.mp4"
        if output_path.exists():
            if progress:
                progress(f"file already exists: {output_path.name}")
            return output_path

        self._download_video(session, video_url, output_path, expanded, progress)
        self._validate_file(output_path)
        return output_path

    def _get_page(self, url: str):
        session = requests.Session(impersonate="chrome")
        session.headers.update(TIKTOK_HEADERS)
        session.headers.update({
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })
        response = session.get(url, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"TikTok HTTP error: {response.status_code}")
        if len(response.text) < 10_000:
            raise RuntimeError(f"TikTok returned unexpected page ({len(response.text)} bytes)")
        return session, response.text

    def _extract_video_url(self, page: str) -> str:
        match = (
            re.search(r'"playAddr":"([^"]+)"', page)
            or re.search(r'"downloadAddr":"([^"]+)"', page)
            or re.search(r'"playUrl":"([^"]+)"', page)
        )
        if not match:
            raise RuntimeError("Could not find TikTok video URL in webpage")

        raw_url = match.group(1)
        video_url = html.unescape(raw_url)
        try:
            video_url = json.loads(f'"{raw_url}"')
        except Exception:
            pass
        video_url = (
            video_url.replace(r"\u002F", "/")
            .replace(r"\/", "/")
            .replace(r"\u0026", "&")
        )
        if not video_url.startswith("http"):
            raise RuntimeError("Extracted TikTok video URL is invalid")
        return video_url

    def _download_video(
        self,
        session,
        video_url: str,
        output_path: Path,
        referer: str,
        progress: ProgressFn | None,
    ) -> None:
        response = session.get(
            video_url,
            headers={
                "Accept": "*/*",
                "Referer": referer,
                "Origin": "https://www.tiktok.com",
                "Sec-Fetch-Dest": "video",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
            },
            stream=True,
            timeout=60,
        )
        try:
            if response.status_code != 200:
                raise RuntimeError(f"Video download failed: HTTP {response.status_code}")
            total = int(response.headers.get("content-length") or 0)
            downloaded = 0
            started_at = time.monotonic()
            last_report_at = 0.0
            with output_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        now = time.monotonic()
                        if progress and (now - last_report_at >= 1.0):
                            last_report_at = now
                            progress(self._format_progress(downloaded, total, started_at))
            if progress:
                progress(self._format_progress(downloaded, total, started_at))
        finally:
            response.close()

    def _format_progress(self, downloaded: int, total: int, started_at: float) -> str:
        elapsed = max(0.001, time.monotonic() - started_at)
        speed = downloaded / elapsed / (1024 * 1024)
        downloaded_mb = downloaded / (1024 * 1024)
        if total:
            total_mb = total / (1024 * 1024)
            percent = downloaded / total * 100
            return f"download {percent:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB), {speed:.2f} MB/s, {elapsed:.0f}s"
        return f"download {downloaded_mb:.1f} MB, {speed:.2f} MB/s, {elapsed:.0f}s"

    def _validate_file(self, output_path: Path) -> None:
        if not output_path.exists():
            raise RuntimeError("TikTok video file was not created")
        if output_path.stat().st_size < 10_000:
            output_path.unlink(missing_ok=True)
            raise RuntimeError("Downloaded TikTok file is too small")
