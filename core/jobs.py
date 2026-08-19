# core/jobs.py
from __future__ import annotations
from dataclasses import dataclass


@dataclass(slots=True)
class Job:
    chat_id: int
    user_id: int
    url: str
    msg_id: int | None = None
    source_url: str | None = None
    target_chat_id: int | None = None
