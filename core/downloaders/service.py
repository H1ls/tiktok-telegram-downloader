from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from core.config import AppConfig
from core.downloaders.base import ProgressFn, TikTokDownloader
from core.downloaders.curl_downloader import CurlTikTokDownloader
from core.downloaders.ytdlp_downloader import YtDlpTikTokDownloader


@dataclass
class DownloadService:
    downloaders: Iterable[TikTokDownloader]

    @classmethod
    def default(cls) -> "DownloadService":
        return cls((
            CurlTikTokDownloader(),
            YtDlpTikTokDownloader(),
        ))

    def download_tiktok(self, url: str, cfg: AppConfig, user_id: int, progress: ProgressFn | None = None) -> Path:
        errors: list[str] = []
        for downloader in self.downloaders:
            try:
                if progress:
                    progress(f"{downloader.name}: started")
                path = downloader.download(url, cfg, user_id, progress=progress)
                if progress:
                    progress(f"{downloader.name}: finished")
                return path
            except Exception as exc:
                if progress:
                    progress(f"{downloader.name}: failed: {exc}")
                errors.append(f"{downloader.name}: {exc}")
        raise RuntimeError("TikTok download failed. " + " | ".join(errors))
