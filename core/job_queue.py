from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable

from core.config import AppConfig
from core.files import list_media_files
from core.jobs import Job
from core.paths import get_user_dir

LogFn = Callable[[str], None]


@dataclass
class QueueState:
    in_progress: int = 0
    queued_by_user: dict[int, int] = field(default_factory=dict)
    in_progress_by_user: dict[int, int] = field(default_factory=dict)


class JobQueueService:
    def __init__(self, cfg: AppConfig, log: LogFn):
        self.cfg = cfg
        self.log = log
        self.queue: asyncio.Queue[Job] = asyncio.Queue()
        self.state = QueueState()

    def update_config(self, cfg: AppConfig) -> None:
        self.cfg = cfg

    def enqueue(self, job: Job) -> int:
        self.state.queued_by_user[job.user_id] = self.state.queued_by_user.get(job.user_id, 0) + 1
        position = (
            self.pending_count(job.user_id)
            + self.state.in_progress_by_user.get(job.user_id, 0)
            + self.state.queued_by_user.get(job.user_id, 0)
        )
        self.queue.put_nowait(job)
        self.log(f"[QUEUE] Queued download #{position}: user={job.user_id}, chat={job.chat_id}, url={job.source_url or job.url}")
        return position

    def pending_count(self, user_id: int) -> int:
        return len(list_media_files(get_user_dir(self.cfg, user_id)))

    async def get(self) -> Job:
        return await self.queue.get()

    def task_done(self) -> None:
        self.queue.task_done()

    def mark_started(self, job: Job) -> None:
        self.state.in_progress += 1
        self.state.queued_by_user[job.user_id] = max(0, self.state.queued_by_user.get(job.user_id, 0) - 1)
        self.state.in_progress_by_user[job.user_id] = self.state.in_progress_by_user.get(job.user_id, 0) + 1

    def mark_finished(self, job: Job) -> None:
        self.state.in_progress = max(0, self.state.in_progress - 1)
        self.state.in_progress_by_user[job.user_id] = max(
            0,
            self.state.in_progress_by_user.get(job.user_id, 0) - 1,
        )
