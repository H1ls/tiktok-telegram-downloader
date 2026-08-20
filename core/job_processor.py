from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Awaitable, Callable

from aiogram import Bot

from core.config import AppConfig
from core.downloader import download_tiktok, has_audio_stream
from core.flusher import FolderFlusher
from core.jobs import Job
from core.sender import TelegramSender
from core.user_settings import UserSettingsService

LogFn = Callable[[str], None]
AsyncProgressFn = Callable[[int, str], Awaitable[None]]


def error_summary(exc: BaseException, max_length: int = 240) -> str:
    message = " ".join(str(exc).split())
    summary = f"{type(exc).__name__}: {message}" if message else type(exc).__name__
    if len(summary) <= max_length:
        return summary
    return summary[: max_length - 1].rstrip() + "..."


class JobProcessor:
    def __init__(
        self,
        *,
        cfg: AppConfig,
        bot: Bot,
        sender: TelegramSender,
        flusher: FolderFlusher,
        user_settings: UserSettingsService,
        download_pool: asyncio.Semaphore,
        lock_for_user: Callable[[int], asyncio.Lock],
        pending_count: Callable[[int], int],
        food_caption: Callable[[], str],
        send_progress: AsyncProgressFn,
        log: LogFn,
    ):
        self.cfg = cfg
        self.bot = bot
        self.sender = sender
        self.flusher = flusher
        self.user_settings = user_settings
        self.download_pool = download_pool
        self.lock_for_user = lock_for_user
        self.pending_count = pending_count
        self.food_caption = food_caption
        self.send_progress = send_progress
        self.log = log

    async def process(self, job: Job) -> None:
        path = await self._download(job)
        await self._warn_if_no_audio(job, path)

        if job.target_chat_id is not None:
            await self._send_requested_chat(job, path)
            return

        user_cfg = self.user_settings.for_user(job.user_id)
        mode = (user_cfg.get("delivery_mode") or "dm").lower()
        if mode == "dm":
            await self._send_dm(job, path)
            return

        await self._handle_group_batch(job, path, user_cfg)

    async def _download(self, job: Job) -> Path:
        self.log(f"[DOWNLOAD] Started: user={job.user_id}, url={job.source_url or job.url}")
        async with self.download_pool:
            try:
                path_str = await asyncio.to_thread(
                    download_tiktok,
                    job.url,
                    self.cfg,
                    job.user_id,
                    lambda text: self.log(f"[DOWNLOAD] {text}"),
                )
            except Exception as exc:
                self.log(
                    f"[DOWNLOAD] Failed: user={job.user_id}, "
                    f"url={job.source_url or job.url}, error={error_summary(exc)}"
                )
                raise
        path = Path(path_str)
        self.log(f"[DOWNLOAD] Finished: {path}")
        return path

    async def _warn_if_no_audio(self, job: Job, path: Path) -> None:
        try:
            if not has_audio_stream(path):
                await self.send_progress(
                    job.chat_id,
                    "Видео скачалось без звука. Возможна проблема TikTok/авторизации/региона.",
                )
        except Exception as exc:
            self.log(f"[TELEGRAM] Audio warning failed: {error_summary(exc)}")

    async def _send_requested_chat(self, job: Job, path: Path) -> None:
        try:
            await self.sender.send_paths(chat_id=int(job.target_chat_id), paths=[path])
            self.log(f"[TELEGRAM] Sent video to requested chat: {job.target_chat_id}")
        except Exception as exc:
            self.log(f"[TELEGRAM] Requested chat send failed: {error_summary(exc)}")
            raise
        self._delete_file(path)

    async def _send_dm(self, job: Job, path: Path) -> None:
        try:
            await self.sender.send_paths(chat_id=int(job.user_id), paths=[path])
        except Exception as exc:
            self.log(f"[TELEGRAM] DM send failed: {error_summary(exc)}")
            try:
                await self.sender.send_paths(chat_id=int(job.chat_id), paths=[path])
            except Exception as exc:
                self.log(f"[TELEGRAM] Missing target chat message failed: {error_summary(exc)}")
        self._delete_file(path)

    async def _handle_group_batch(self, job: Job, path: Path, user_cfg: dict) -> None:
        batch_size = max(1, min(10, int(user_cfg.get("batch_size") or 5)))
        target_chat_id = user_cfg.get("target_chat_id")

        try:
            nfiles = self.pending_count(job.user_id)
            await self.send_progress(job.chat_id, f"Загрузил {nfiles}/{batch_size}\n{job.source_url or job.url}")
        except Exception as exc:
            self.log(f"[TELEGRAM] Batch progress message failed: {error_summary(exc)}")
            try:
                await self.send_progress(job.chat_id, f"Не скачано:\n{job.source_url or job.url}\n{exc}")
            except Exception as send_exc:
                self.log(f"[TELEGRAM] Batch failure message failed: {error_summary(send_exc)}")

        if self.pending_count(job.user_id) < batch_size:
            return

        if not target_chat_id:
            try:
                await self.send_progress(job.chat_id, "Укажи чат для пачек: /bind или /bind_id -100...")
            except Exception as exc:
                self.log(f"[TELEGRAM] Missing target chat message failed: {error_summary(exc)}")
            return

        try:
            await self.send_progress(
                job.chat_id,
                f"В процессе отправки\nЧат: {target_chat_id}\nФайлов: {self.pending_count(job.user_id)}/{batch_size}",
            )
        except Exception as exc:
            self.log(f"[TELEGRAM] Flush start message failed: {error_summary(exc)}")

        try:
            async with self.lock_for_user(job.user_id):
                sent = await self.flusher.flush_all(
                    user_id=job.user_id,
                    chat_id=int(target_chat_id),
                    caption=self.food_caption(),
                    progress=lambda text: self.send_progress(job.chat_id, text),
                )
        except Exception as exc:
            self.log(f"[TELEGRAM] Auto flush failed: {error_summary(exc)}")
            try:
                await self.send_progress(
                    job.chat_id,
                    f"Не смог отправить пачку. Файлы не удалял.\nПричина: {error_summary(exc)}",
                )
            except Exception as send_exc:
                self.log(f"[TELEGRAM] Auto flush failure message failed: {error_summary(send_exc)}")
            return

        try:
            left = self.pending_count(job.user_id)
            await self.send_progress(
                job.chat_id,
                f"Отправил в чат {target_chat_id}\nФайлов: {sent}\nОсталось в папке: {left}",
            )
        except Exception as exc:
            self.log(f"[TELEGRAM] Flush result message failed: {error_summary(exc)}")

    def _delete_file(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
