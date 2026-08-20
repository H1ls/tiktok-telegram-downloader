from __future__ import annotations

import asyncio
import time
from collections import deque


class AsyncRateLimiter:
    def __init__(self, max_calls: int, window_seconds: float):
        if max_calls < 1:
            raise ValueError("max_calls must be greater than zero")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero")

        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                expires_before = now - self.window_seconds
                while self._calls and self._calls[0] <= expires_before:
                    self._calls.popleft()

                if len(self._calls) < self.max_calls:
                    self._calls.append(now)
                    return

                wait_seconds = self.window_seconds - (now - self._calls[0])

            await asyncio.sleep(max(wait_seconds, 0.0))
