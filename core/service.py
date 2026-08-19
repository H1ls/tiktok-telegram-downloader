from __future__ import annotations

import asyncio
import random
from typing import Callable

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import (
    TelegramConflictError,
    TelegramNetworkError,
    TelegramServerError,
    TelegramUnauthorizedError,
)

from core.config import AppConfig, load_config
from core.flush_service import FlushService
from core.flusher import FolderFlusher
from core.job_processor import JobProcessor, error_summary
from core.job_queue import JobQueueService, QueueState
from core.jobs import Job
from core.sender import TelegramSender
from core.user_settings import UserSettingsService

FOOD_EMOJIS = [
    "🍕", "🍔", "🍟", "🌭", "🍿", "🥪", "🥙", "🌮", "🌯",
    "🍜", "🍝", "🍛", "🍣", "🍱", "🥟", "🍤", "🥗", "🍲",
    "🥘", "🍞", "🥐", "🥖", "🧀", "🍖", "🍗", "🥩",
    "🍩", "🍪", "🎂", "🍰", "🧁", "🍫", "🍬",
    "🍎", "🍓", "🍉", "🍍", "🥭", "🍒",
    "☕", "🍵", "🥤", "🍹",
]

LogFn = Callable[[str], None]
HandlersRegistrar = Callable[[Dispatcher, "TikTokBotService"], None]

POLLING_RETRY_INITIAL_SECONDS = 2.0
POLLING_RETRY_MAX_SECONDS = 60.0


def make_bot(token: str) -> Bot:
    try:
        return Bot(token, session=AiohttpSession(timeout=300))
    except TypeError:
        return Bot(token, session=AiohttpSession())


class TikTokBotService:
    def __init__(
        self,
        token: str,
        log: LogFn | None = None,
        register_handlers: HandlersRegistrar | None = None,
    ):
        self.token = token
        self.log: LogFn = log or (lambda _: None)
        self._register_handlers = register_handlers

        self.cfg: AppConfig = load_config()
        self.user_settings = UserSettingsService(self.cfg)
        self.job_queue = JobQueueService(self.cfg, self.log)

        self._bot: Bot | None = None
        self._dp: Dispatcher | None = None
        self._tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self._started = False
        self._user_locks: dict[int, asyncio.Lock] = {}
        self._download_pool = asyncio.Semaphore(4)

        self.sender: TelegramSender | None = None
        self.flusher: FolderFlusher | None = None
        self.processor: JobProcessor | None = None
        self.flush_service: FlushService | None = None

    @property
    def state(self) -> QueueState:
        return self.job_queue.state

    def user_lock(self, user_id: int) -> asyncio.Lock:
        self._user_locks.setdefault(user_id, asyncio.Lock())
        return self._user_locks[user_id]

    def enqueue(self, job: Job) -> int:
        return self.job_queue.enqueue(job)

    def pending_count(self, user_id: int) -> int:
        return self.job_queue.pending_count(user_id)

    def _user_cfg(self, user_id: int) -> dict:
        return self.user_settings.for_user(user_id)

    def reload_config(self) -> None:
        self._reload_config()

    def _food_caption(self) -> str:
        return f"{random.choice(FOOD_EMOJIS)} Еда готова"

    async def _send_progress(self, chat_id: int, text: str) -> None:
        if not self._bot:
            return
        try:
            await self._bot.send_message(chat_id, text)
        except Exception:
            pass

    async def start(self) -> None:
        if self._started:
            self.log("[SERVICE] Already started")
            return

        self.log("[SERVICE] Starting...")
        self._reload_config()
        self._bot = make_bot(self.token)
        self._dp = Dispatcher()
        self.sender = TelegramSender(self._bot)
        self.flusher = FolderFlusher(cfg=self.cfg, sender=self.sender)
        self._build_runtime_services()

        if self._register_handlers:
            self._register_handlers(self._dp, self)

        self._stop_event.clear()
        self._tasks = [
            asyncio.create_task(self._worker_loop(), name="worker"),
            asyncio.create_task(self._polling_loop(), name="polling"),
            asyncio.create_task(self._startup_flush_loop(), name="startup_flush"),
        ]
        self._started = True
        self.log("[SERVICE] Started")

    async def stop(self) -> None:
        if not self._started:
            self.log("[SERVICE] Already stopped")
            return

        self.log("[SERVICE] Stopping...")
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        if self._bot:
            try:
                await self._bot.session.close()
            except Exception:
                pass

        self._bot = None
        self._dp = None
        self.sender = None
        self.flusher = None
        self.processor = None
        self.flush_service = None
        self._started = False
        self._user_locks.clear()
        self.log("[SERVICE] Stopped")

    async def flush_user(self, user_id: int, target_chat_id: int, notify_chat_id: int | None = None) -> None:
        if not self.flush_service:
            return
        await self.flush_service.flush_user(user_id, target_chat_id, notify_chat_id)

    def _reload_config(self) -> None:
        self.cfg = load_config()
        self.user_settings = UserSettingsService(self.cfg)
        self.job_queue.update_config(self.cfg)

    def _build_runtime_services(self) -> None:
        assert self._bot is not None
        assert self.sender is not None
        assert self.flusher is not None

        self.flush_service = FlushService(
            flusher=self.flusher,
            user_settings=self.user_settings,
            lock_for_user=self.user_lock,
            pending_count=self.pending_count,
            food_caption=self._food_caption,
            send_progress=self._send_progress,
            log=self.log,
        )
        self.processor = JobProcessor(
            cfg=self.cfg,
            bot=self._bot,
            sender=self.sender,
            flusher=self.flusher,
            user_settings=self.user_settings,
            download_pool=self._download_pool,
            lock_for_user=self.user_lock,
            pending_count=self.pending_count,
            food_caption=self._food_caption,
            send_progress=self._send_progress,
            log=self.log,
        )

    async def _startup_flush_loop(self) -> None:
        if not self.flush_service:
            return
        await self.flush_service.flush_ready_batches_on_startup()

    async def _polling_loop(self) -> None:
        assert self._dp is not None and self._bot is not None
        retry_delay = POLLING_RETRY_INITIAL_SECONDS
        attempt = 0

        while not self._stop_event.is_set():
            try:
                self.log("[POLLING] Connecting..." if attempt == 0 else "[POLLING] Reconnecting...")
                await self._dp.start_polling(
                    self._bot,
                    handle_signals=False,
                    close_bot_session=False,
                )
                return
            except asyncio.CancelledError:
                self.log("[POLLING] Cancelled")
                raise
            except TelegramUnauthorizedError:
                self.log("[POLLING] Stopped: invalid bot token")
                return
            except TelegramConflictError:
                self.log("[POLLING] Stopped: the bot is running in another process")
                return
            except (TelegramNetworkError, TelegramServerError, OSError) as exc:
                attempt += 1
                delay = min(retry_delay, POLLING_RETRY_MAX_SECONDS)
                self.log(f"[POLLING] Telegram unavailable ({type(exc).__name__}). Retry in {delay:.0f} s")
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
                    return
                except asyncio.TimeoutError:
                    pass
                retry_delay = min(delay * 2, POLLING_RETRY_MAX_SECONDS)
            except Exception as exc:
                self.log(f"[POLLING] Stopped: {error_summary(exc)}")
                return

    async def _worker_loop(self) -> None:
        self.log("[WORKER] Start")
        while not self._stop_event.is_set():
            try:
                job = await self.job_queue.get()
            except asyncio.CancelledError:
                self.log("[WORKER] Cancelled")
                raise

            self.job_queue.mark_started(job)
            try:
                if not self.processor:
                    raise RuntimeError("Job processor is not initialized")
                await self.processor.process(job)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.log(f"[WORKER] Error: {error_summary(exc)}")
            finally:
                self.job_queue.mark_finished(job)
                self.job_queue.task_done()

        self.log("[WORKER] End")
