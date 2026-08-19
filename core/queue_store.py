# core/queue_store.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from core.config import AppConfig, save_config

@dataclass
class QueueStore:
    cfg: AppConfig

    def _u(self, user_id: int) -> dict[str, Any]:
        uid = str(user_id)
        self.cfg.users.setdefault(uid, {})
        self.cfg.users[uid].setdefault("queue", [])
        return self.cfg.users[uid]

    def add(self, user_id: int, filepath: str) -> None:
        u = self._u(user_id)
        u["queue"].append(filepath)
        save_config(self.cfg)

    def peek_batch(self, user_id: int, limit: int) -> list[str]:
        u = self._u(user_id)
        q = u.get("queue", [])
        return q[:max(0, limit)]

    def pop_batch(self, user_id: int, n: int) -> list[str]:
        u = self._u(user_id)
        q = u.get("queue", [])
        n = max(0, min(len(q), n))
        batch = q[:n]
        u["queue"] = q[n:]
        save_config(self.cfg)
        return batch

    def clear(self, user_id: int) -> None:
        u = self._u(user_id)
        u["queue"] = []
        save_config(self.cfg)

    def size(self, user_id: int) -> int:
        u = self._u(user_id)
        return len(u.get("queue", []))