"""
Profile-specific error handling and a lightweight circuit breaker.

This module centralizes handling for profile operations (create/clone/cleanup)
and provides a minimal circuit breaker to avoid cascading failures when the
base profile is corrupted or the filesystem is unstable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Callable, Any


@dataclass
class CircuitBreakerState:
    failure_threshold: int = 3
    recovery_time_window: float = 30.0
    consecutive_failures: int = 0
    opened_at: Optional[float] = None

    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        # If still in open window, remain open; else half-open
        return (time.time() - self.opened_at) < self.recovery_time_window

    def record_success(self):
        self.consecutive_failures = 0
        self.opened_at = None

    def record_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.opened_at = time.time()


class ProfileOperationHandler:
    """Executes profile operations with basic circuit breaker semantics."""

    def __init__(self, failure_threshold: int = 3, recovery_time_window: float = 30.0):
        self._breaker = CircuitBreakerState(
            failure_threshold=failure_threshold,
            recovery_time_window=recovery_time_window,
        )

    def run(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Run operation with circuit breaker; raise RuntimeError if open.

        The caller decides whether to gracefully degrade or propagate.
        """
        # If breaker is open, refuse execution until window passes
        if self._breaker.is_open():
            raise RuntimeError("Circuit breaker open for profile operations")

        try:
            result = func(*args, **kwargs)
            self._breaker.record_success()
            return result
        except Exception:
            self._breaker.record_failure()
            raise

    def can_attempt(self) -> bool:
        return not self._breaker.is_open()
