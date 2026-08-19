from __future__ import annotations

from core.config import AppConfig
from core.downloaders.base import ProgressFn
from core.downloaders.common import expand_url, extract_tiktok_url, has_audio_stream, is_tiktok_photo
from core.downloaders.ytdlp_downloader import YtDlpTikTokDownloader

_downloader = YtDlpTikTokDownloader()


def download_tiktok(url: str, cfg: AppConfig, user_id: int, progress: ProgressFn | None = None) -> str:
    return str(_downloader.download(url, cfg, user_id, progress=progress))


__all__ = [
    "download_tiktok",
    "expand_url",
    "extract_tiktok_url",
    "has_audio_stream",
    "is_tiktok_photo",
]
