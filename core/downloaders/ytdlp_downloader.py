from __future__ import annotations

import time
from pathlib import Path

from yt_dlp import YoutubeDL

from core.config import AppConfig
from core.downloaders.base import ProgressFn
from core.downloaders.common import cookies_path, expand_url, has_audio_stream, user_max_height
from core.paths import get_user_dir


class YtDlpTikTokDownloader:
    name = "yt_dlp"

    def download(self, url: str, cfg: AppConfig, user_id: int, progress: ProgressFn | None = None) -> Path:
        if not url:
            raise ValueError("Empty url")

        if progress:
            progress("expanding short URL")
        expanded = expand_url(url)
        user_dir = get_user_dir(cfg, user_id)
        options = self._base_options(user_dir, progress)

        if progress:
            progress("reading available formats")
        info = self._extract_info(expanded, options)
        candidates = self._format_candidates(info.get("formats") or [], cfg, user_id)
        tried: list[str] = []

        for format_id in candidates[:8]:
            tried.append(format_id)
            path = self._download_format(expanded, options, format_id)
            if has_audio_stream(path):
                return path

        path = self._download_format(expanded, options, "download/best")
        if path.exists():
            return path
        raise RuntimeError(f"No valid yt_dlp file. Tried formats: {tried}")

    def _base_options(self, user_dir: Path, progress: ProgressFn | None) -> dict:
        options = {
            "sleep_interval": 1,
            "max_sleep_interval": 2,
            "outtmpl": str(user_dir / "%(uploader)s_%(id)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": 4,
            "merge_output_format": "mp4",
            "prefer_ffmpeg": True,
            "socket_timeout": 60,
        }
        cookie_file = cookies_path()
        if cookie_file.exists():
            options["cookiefile"] = str(cookie_file)
        if progress:
            options["progress_hooks"] = [self._progress_hook(progress)]
        return options

    def _extract_info(self, url: str, options: dict) -> dict:
        for attempt in range(3):
            try:
                with YoutubeDL({**options, "format": "best"}) as ydl:
                    return ydl.extract_info(url, download=False)
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(0.5)
        raise RuntimeError("Could not extract TikTok metadata")

    def _format_candidates(self, formats: list[dict], cfg: AppConfig, user_id: int) -> list[str]:
        candidates = []
        for item in formats:
            acodec = (item.get("acodec") or "none").lower()
            vcodec = (item.get("vcodec") or "none").lower()
            ext = (item.get("ext") or "").lower()
            format_id = item.get("format_id")
            if not format_id or acodec == "none" or vcodec == "none" or ext != "mp4":
                continue
            video_preference = 2 if "h264" in vcodec or "avc" in vcodec else 1
            height = int(item.get("height") or 0)
            bitrate = float(item.get("tbr") or 0.0)
            candidates.append((video_preference, height, bitrate, format_id))

        max_height = user_max_height(cfg, user_id)
        if max_height:
            filtered = [item for item in candidates if int(item[1] or 0) <= max_height]
            if filtered:
                candidates = filtered

        candidates.sort(reverse=True)
        return [format_id for _, __, ___, format_id in candidates]

    def _download_format(self, url: str, options: dict, format_id: str) -> Path:
        with YoutubeDL({**options, "format": format_id}) as ydl:
            info = ydl.extract_info(url, download=True)
            raw_path = Path(ydl.prepare_filename(info))
        if raw_path.exists():
            return raw_path
        mp4_path = raw_path.with_suffix(".mp4")
        if mp4_path.exists():
            return mp4_path
        return raw_path

    def _progress_hook(self, progress: ProgressFn):
        last_report = {"at": 0.0}

        def hook(data: dict) -> None:
            status = data.get("status")
            now = time.monotonic()
            if status == "finished":
                filename = data.get("filename")
                progress(f"download finished: {Path(filename).name if filename else 'file'}")
                return
            if status != "downloading" or now - last_report["at"] < 1.0:
                return
            last_report["at"] = now
            downloaded = int(data.get("downloaded_bytes") or 0)
            total = int(data.get("total_bytes") or data.get("total_bytes_estimate") or 0)
            speed = float(data.get("speed") or 0.0)
            eta = data.get("eta")
            downloaded_mb = downloaded / (1024 * 1024)
            speed_mb = speed / (1024 * 1024) if speed else 0.0
            if total:
                total_mb = total / (1024 * 1024)
                percent = downloaded / total * 100
                progress(f"download {percent:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB), {speed_mb:.2f} MB/s, eta {eta or '?'}s")
            else:
                progress(f"download {downloaded_mb:.1f} MB, {speed_mb:.2f} MB/s, eta {eta or '?'}s")

        return hook
