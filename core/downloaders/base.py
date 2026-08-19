from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from core.config import AppConfig

ProgressFn = Callable[[str], None]


class TikTokDownloader(Protocol):
    name: str

    def download(self, url: str, cfg: AppConfig, user_id: int, progress: ProgressFn | None = None) -> Path:
        ...
