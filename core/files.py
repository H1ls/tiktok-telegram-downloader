# core/files.py
from __future__ import annotations
from pathlib import Path
from typing import Iterable

VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def list_media_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    files = []
    for p in folder.iterdir():
        if p.is_file() and p.suffix.lower() in (VIDEO_EXT | IMAGE_EXT):
            files.append(p)
    # старые первыми, чтобы порядок был стабильным
    files.sort(key=lambda x: x.stat().st_mtime)
    return files