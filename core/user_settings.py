from __future__ import annotations

from typing import Any

from core.config import AppConfig


class UserSettingsService:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg

    def for_user(self, user_id: int) -> dict[str, Any]:
        uid = str(user_id)
        self.cfg.users.setdefault(uid, {})
        user = self.cfg.users[uid]
        defaults = self.cfg.defaults or {}

        user.setdefault("delivery_mode", defaults.get("delivery_mode", "dm"))
        user.setdefault("target_chat_id", defaults.get("target_chat_id"))
        user["batch_size"] = max(1, min(10, int(user.get("batch_size") or 5)))
        user["queue_keep_max"] = max(1, int(user.get("queue_keep_max") or 50))
        user.setdefault("max_height", defaults.get("max_height"))
        return user
