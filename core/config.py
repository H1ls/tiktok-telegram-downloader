from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from core.app_paths import app_dir


APP_NAME = "TikTokDownloader"
DEFAULT_DOWNLOAD_ROOT = Path(r"D:\TikTok")
BOOTSTRAP_FILE = "storage.json"
CONFIG_FILE = "config.json"


def _default_data_dir() -> Path:
    if (app_dir() / CONFIG_FILE).exists():
        return app_dir()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_NAME
    return app_dir()


def _bootstrap_path() -> Path:
    return app_dir() / BOOTSTRAP_FILE


def _read_bootstrap_data_dir() -> Path | None:
    path = _bootstrap_path()
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("data_dir")
    except Exception:
        return None
    if not value:
        return None
    return Path(str(value)).expanduser()


def app_data_dir() -> Path:
    path = _read_bootstrap_data_dir() or _default_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def set_app_data_dir(path: str | Path) -> Path:
    target = Path(path).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    current_cfg = config_path()
    next_cfg = target / CONFIG_FILE
    if current_cfg.exists() and current_cfg.resolve() != next_cfg.resolve() and not next_cfg.exists():
        next_cfg.write_text(current_cfg.read_text(encoding="utf-8"), encoding="utf-8")
    _bootstrap_path().write_text(
        json.dumps({"data_dir": str(target)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def config_path() -> Path:
    return app_data_dir() / CONFIG_FILE


@dataclass
class AppConfig:
    batch_size: int = 10
    bot_token: str = ""
    download_root: str | None = None
    autostart: bool = False
    defaults: dict[str, Any] = field(default_factory=lambda: {
        "delivery_mode": "dm",
        "target_chat_id": None,
        "batch_size": 5,
        "queue_keep_max": 50,
        "max_height": None,
    })
    admin_ids: list[int] = field(default_factory=list)
    users: dict[str, dict[str, Any]] = field(default_factory=dict)

    MAX_FILE_SIZE_BYTES: ClassVar[int] = 50 * 1024 * 1024
    MAX_ALBUM_SIZE_BYTES: ClassVar[int] = 45 * 1024 * 1024
    MAX_ALBUM_ITEMS: ClassVar[int] = 10
    DOWNLOAD_WORKERS: ClassVar[int] = 4

    def validate(self) -> None:
        self.batch_size = max(1, min(100, int(self.batch_size or 10)))
        self.bot_token = (self.bot_token or "").strip()
        self.download_root = (self.download_root or "").strip() or None

        if self.download_root:
            Path(self.download_root).expanduser().mkdir(parents=True, exist_ok=True)

        defaults = dict(self.defaults or {})
        defaults["delivery_mode"] = (defaults.get("delivery_mode") or "dm").lower()
        defaults["batch_size"] = max(1, min(10, int(defaults.get("batch_size") or 5)))
        defaults["queue_keep_max"] = max(1, int(defaults.get("queue_keep_max") or 50))
        self.defaults = defaults


def _load_raw_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_config() -> AppConfig:
    data = _load_raw_config(config_path())
    env_download_root = (os.environ.get("DOWNLOAD_ROOT") or "").strip() or None

    users = dict(data.get("users", {}) or {})
    defaults = dict(data.get("defaults", {}) or {})

    routes = dict(data.get("routes", {}) or {})
    for uid, mode in routes.items():
        uid = str(uid)
        users.setdefault(uid, {})
        normalized = (mode or "").lower()
        users[uid].setdefault("delivery_mode", "group_batch" if normalized in ("group", "group_batch") else "dm")

    group_chat_id = data.get("group_chat_id", None)
    if group_chat_id is not None and defaults.get("target_chat_id") is None:
        try:
            defaults["target_chat_id"] = int(group_chat_id)
        except Exception:
            pass

    cfg = AppConfig(
        bot_token=str(data.get("bot_token", "")).strip(),
        batch_size=int(data.get("batch_size", 10) or 10),
        download_root=env_download_root or (data.get("download_root") or None),
        autostart=bool(data.get("autostart", False)),
        defaults=defaults,
        admin_ids=[int(x) for x in (data.get("admin_ids", []) or [])],
        users=users,
    )
    cfg.validate()
    save_config(cfg)
    return cfg


def save_config(cfg: AppConfig) -> None:
    cfg.validate()
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
