from __future__ import annotations

from pathlib import Path

from core.config import AppConfig, DEFAULT_DOWNLOAD_ROOT


def get_download_root(cfg: AppConfig) -> Path:
    root = Path(cfg.download_root).expanduser() if cfg.download_root else DEFAULT_DOWNLOAD_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def get_user_dir(cfg: AppConfig, user_id: int) -> Path:
    if not isinstance(user_id, int):
        raise TypeError("user_id must be an integer")

    root = get_download_root(cfg)
    user_dir = (root / str(user_id)).resolve()
    if root != user_dir and root not in user_dir.parents:
        raise ValueError(f"Invalid user_id path: {user_id}")
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir
