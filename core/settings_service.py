from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core import autostart
from core.config import DEFAULT_DOWNLOAD_ROOT, app_data_dir, load_config, save_config, set_app_data_dir
from core.paths import get_download_root


@dataclass(frozen=True)
class SettingsSnapshot:
    bot_token: str
    data_dir: str
    download_root: str
    autostart: bool


class SettingsService:
    def load(self) -> SettingsSnapshot:
        cfg = load_config()
        return SettingsSnapshot(
            bot_token=cfg.bot_token,
            data_dir=str(app_data_dir()),
            download_root=str(get_download_root(cfg)),
            autostart=autostart.is_enabled() or cfg.autostart,
        )

    def save(self, *, bot_token: str, data_dir: str, download_root: str | None, autostart_enabled: bool) -> SettingsSnapshot:
        target_download_root = Path((download_root or "").strip() or data_dir.strip() or DEFAULT_DOWNLOAD_ROOT)
        target_download_root = target_download_root.expanduser().resolve()
        set_app_data_dir(target_download_root)
        cfg = load_config()
        cfg.bot_token = bot_token.strip()
        cfg.download_root = str(target_download_root)
        cfg.autostart = autostart_enabled
        save_config(cfg)
        autostart.set_enabled(cfg.autostart)
        return self.load()
