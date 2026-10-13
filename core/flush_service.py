from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from core.flusher import FolderFlusher
from core.job_processor import error_summary
from core.user_settings import UserSettingsService

LogFn = Callable[[str], None]
AsyncProgressFn = Callable[..., Awaitable[None]]


class FlushService:
    def __init__(
        self,
        *,
        flusher: FolderFlusher,
        user_settings: UserSettingsService,
        lock_for_user: Callable[[int], asyncio.Lock],
        pending_count: Callable[[int], int],
        food_caption: Callable[[], str],
        send_progress: AsyncProgressFn,
        log: LogFn,
    ):
        self.flusher = flusher
        self.user_settings = user_settings
        self.lock_for_user = lock_for_user
        self.pending_count = pending_count
        self.food_caption = food_caption
        self.send_progress = send_progress
        self.log = log

    async def flush_user(self, user_id: int, target_chat_id: int, notify_chat_id: int | None = None) -> None:
        async with self.lock_for_user(user_id):
            try:
                sent = await self.flusher.flush_all(
                    user_id=user_id,
                    chat_id=int(target_chat_id),
                    caption=self.food_caption(),
                    progress=(lambda text: self.send_progress(notify_chat_id, text)) if notify_chat_id else None,
                )
            except Exception as exc:
                if notify_chat_id:
                    await self.send_progress(
                        notify_chat_id,
                        f"Не смог отправить альбом одним блоком. Ничего не удалял.\nПричина: {error_summary(exc)}",
                    )
                raise

        if notify_chat_id:
            await self.send_progress(
                notify_chat_id,
                f"Отправлено: {sent}. Осталось в папке: {self.pending_count(user_id)}.",
            )

    async def flush_ready_batches_on_startup(self) -> None:
        await asyncio.sleep(1)
        for raw_user_id in list((self.user_settings.cfg.users or {}).keys()):
            try:
                user_id = int(raw_user_id)
            except (TypeError, ValueError):
                continue

            user_cfg = self.user_settings.for_user(user_id)
            if (user_cfg.get("delivery_mode") or "dm").lower() != "group_batch":
                continue

            target_chat_id = user_cfg.get("target_chat_id")
            if not target_chat_id:
                self.log(f"[FLUSH] Startup skipped for user {user_id}: target_chat_id is not set")
                continue

            batch_size = max(1, min(10, int(user_cfg.get("batch_size") or 5)))
            if self.pending_count(user_id) < batch_size:
                continue

            self.log(f"[FLUSH] Startup: user={user_id}, files={self.pending_count(user_id)}/{batch_size}")
            try:
                await self.flush_user(user_id, target_chat_id=int(target_chat_id), notify_chat_id=user_id)
            except Exception as exc:
                self.log(f"[FLUSH] Startup failed for user {user_id}: {error_summary(exc)}")
