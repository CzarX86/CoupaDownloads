import time
import asyncio
from typing import Optional


class RateLimiter:
    """Adaptive rate limiter with 429 backoff and cooldown for large batches."""

    def __init__(self, base_delay: float = 0.03, cooldown_threshold: int = 500):
        self.base_delay = base_delay
        self.cooldown_threshold = cooldown_threshold
        self._consecutive_429s = 0
        self._backoff_until: float = 0.0
        self._request_count = 0

    @property
    def current_delay(self) -> float:
        if time.monotonic() < self._backoff_until:
            return self._effective_delay
        return self.base_delay

    @property
    def _effective_delay(self) -> float:
        return min(self.base_delay * (2 ** self._consecutive_429s), 5.0)

    def report_429(self) -> None:
        self._consecutive_429s += 1
        backoff = self._effective_delay
        self._backoff_until = time.monotonic() + backoff

    def report_success(self) -> None:
        self._consecutive_429s = max(0, self._consecutive_429s - 1)

    @staticmethod
    async def _sleep_at_least(duration: float) -> None:
        """Sleep for at least ``duration`` on low-resolution Windows clocks."""
        deadline = time.monotonic() + max(0.0, duration)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            await asyncio.sleep(remaining)

    async def wait(self) -> None:
        now = time.monotonic()
        if now < self._backoff_until:
            await self._sleep_at_least(self._backoff_until - now)
            return
        delay = self.base_delay
        self._request_count += 1
        if self._request_count > self.cooldown_threshold:
            delay = self.base_delay * 3
        if delay > 0:
            await self._sleep_at_least(delay)

    def reset(self) -> None:
        self._consecutive_429s = 0
        self._backoff_until = 0.0
        self._request_count = 0
