"""
Adaptive ETA estimation for processing progress.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


TERMINAL_STATUSES = {"COMPLETED", "NO_ATTACHMENTS", "PARTIAL", "SUCCESS", "FAILED", "ERROR"}


@dataclass(frozen=True)
class ETAState:
    """Immutable snapshot returned to consumers."""

    dynamic_rate_per_minute: float
    eta_seconds: Optional[float]
    eta_display: str
    stability_score: float
    confidence_state: str


class ETAStrategy(ABC):
    """Strategy interface for ETA estimation."""

    @abstractmethod
    def record_completion(self, timestamp: float) -> None:
        """Record a completed item event."""

    @abstractmethod
    def build_state(
        self,
        *,
        now: float,
        start_time: Optional[float],
        total_items: int,
        processed_items: int,
        active_items: int,
    ) -> ETAState:
        """Build the current ETA snapshot."""


class SimpleAverageEtaStrategy(ETAStrategy):
    """Baseline strategy using only global average throughput."""

    def record_completion(self, timestamp: float) -> None:
        return None

    def build_state(
        self,
        *,
        now: float,
        start_time: Optional[float],
        total_items: int,
        processed_items: int,
        active_items: int,
    ) -> ETAState:
        elapsed_seconds = max(0.0, now - start_time) if start_time is not None else 0.0
        remaining = max(total_items - processed_items, 0)
        rate = 0.0
        if elapsed_seconds > 0 and processed_items > 0:
            rate = processed_items / (elapsed_seconds / 60.0)

        if remaining == 0 and total_items > 0:
            return ETAState(rate, 0.0, "0s", 1.0, "stable")

        if processed_items == 0 or rate <= 0.0:
            return ETAState(rate, None, "calculating", 0.0, "warming_up")

        if active_items == 0 and remaining > 0:
            return ETAState(rate, None, "waiting", 0.0, "volatile")

        eta_seconds = (remaining / rate) * 60.0
        return ETAState(rate, eta_seconds, format_eta_seconds(eta_seconds), 1.0, "stable")


class AdaptiveEwmaEtaStrategy(ETAStrategy):
    """Adaptive ETA based on recent throughput and global throughput."""

    def __init__(
        self,
        *,
        alpha: float = 0.3,
        warmup_completions: int = 5,
        recent_weight: float = 0.65,
        global_weight: float = 0.35,
        volatile_threshold: float = 0.35,
        clamp_ratio: float = 0.25,
        volatile_hold_seconds: float = 3.0,
        idle_grace_seconds: float = 8.0,
    ) -> None:
        self.alpha = alpha
        self.warmup_completions = warmup_completions
        self.recent_weight = recent_weight
        self.global_weight = global_weight
        self.volatile_threshold = volatile_threshold
        self.clamp_ratio = clamp_ratio
        self.volatile_hold_seconds = volatile_hold_seconds
        self.idle_grace_seconds = idle_grace_seconds

        self._completion_count = 0
        self._last_completion_ts: Optional[float] = None
        self._recent_rate_per_minute: Optional[float] = None
        self._ewma_abs_error: float = 0.0
        self._last_eta_seconds: Optional[float] = None
        self._volatile_hold_until: float = 0.0

    def record_completion(self, timestamp: float) -> None:
        self._completion_count += 1

        if self._last_completion_ts is not None:
            interval_seconds = max(timestamp - self._last_completion_ts, 1e-6)
            instant_rate = 60.0 / interval_seconds

            if self._recent_rate_per_minute is None:
                self._recent_rate_per_minute = instant_rate
            else:
                previous_rate = self._recent_rate_per_minute
                updated_rate = (self.alpha * instant_rate) + ((1.0 - self.alpha) * previous_rate)
                abs_error = abs(instant_rate - updated_rate)
                self._ewma_abs_error = (self.alpha * abs_error) + ((1.0 - self.alpha) * self._ewma_abs_error)
                self._recent_rate_per_minute = updated_rate

        self._last_completion_ts = timestamp

    def build_state(
        self,
        *,
        now: float,
        start_time: Optional[float],
        total_items: int,
        processed_items: int,
        active_items: int,
    ) -> ETAState:
        elapsed_seconds = max(0.0, now - start_time) if start_time is not None else 0.0
        elapsed_minutes = elapsed_seconds / 60.0 if elapsed_seconds > 0 else 0.0
        remaining = max(total_items - processed_items, 0)

        global_rate = (processed_items / elapsed_minutes) if elapsed_minutes > 0 and processed_items > 0 else 0.0
        recent_rate = self._recent_rate_per_minute or 0.0

        if remaining == 0 and total_items > 0:
            self._last_eta_seconds = 0.0
            return ETAState(
                dynamic_rate_per_minute=max(global_rate, recent_rate),
                eta_seconds=0.0,
                eta_display="0s",
                stability_score=1.0,
                confidence_state="stable",
            )

        if processed_items == 0:
            return ETAState(0.0, None, "calculating", 0.0, "warming_up")

        if active_items == 0 and remaining > 0:
            if (
                self._last_eta_seconds is not None
                and self._last_completion_ts is not None
                and (now - self._last_completion_ts) <= self.idle_grace_seconds
            ):
                return ETAState(
                    dynamic_rate_per_minute=global_rate or recent_rate,
                    eta_seconds=self._last_eta_seconds,
                    eta_display=format_eta_seconds(self._last_eta_seconds),
                    stability_score=max(self._calculate_stability_score(recent_rate), 0.4),
                    confidence_state="volatile",
                )
            return ETAState(global_rate or recent_rate, None, "waiting", 0.0, "volatile")

        if self._completion_count < self.warmup_completions:
            return ETAState(global_rate, None, "calculating", 0.0, "warming_up")

        effective_rate = self._select_effective_rate(global_rate, recent_rate)
        if effective_rate <= 0.0:
            return ETAState(global_rate, None, "calculating", 0.0, "warming_up")

        raw_eta_seconds = (remaining / effective_rate) * 60.0
        stability_score = self._calculate_stability_score(recent_rate)
        confidence_state = "stable" if stability_score >= (1.0 - self.volatile_threshold) else "volatile"

        if confidence_state == "volatile":
            if self._last_eta_seconds is not None and now < self._volatile_hold_until:
                return ETAState(
                    dynamic_rate_per_minute=effective_rate,
                    eta_seconds=self._last_eta_seconds,
                    eta_display=format_eta_seconds(self._last_eta_seconds),
                    stability_score=stability_score,
                    confidence_state=confidence_state,
                )
            self._volatile_hold_until = now + self.volatile_hold_seconds

        eta_seconds = self._clamp_eta(raw_eta_seconds)
        self._last_eta_seconds = eta_seconds

        return ETAState(
            dynamic_rate_per_minute=effective_rate,
            eta_seconds=eta_seconds,
            eta_display=format_eta_seconds(eta_seconds),
            stability_score=stability_score,
            confidence_state=confidence_state,
        )

    def _select_effective_rate(self, global_rate: float, recent_rate: float) -> float:
        if recent_rate <= 0.0:
            return global_rate
        if global_rate <= 0.0:
            return recent_rate
        return (self.global_weight * global_rate) + (self.recent_weight * recent_rate)

    def _calculate_stability_score(self, recent_rate: float) -> float:
        if recent_rate <= 0.0:
            return 0.0
        relative_error = min(self._ewma_abs_error / recent_rate, 1.0)
        return max(0.0, 1.0 - relative_error)

    def _clamp_eta(self, raw_eta_seconds: float) -> float:
        if self._last_eta_seconds is None:
            return raw_eta_seconds

        lower_bound = self._last_eta_seconds * (1.0 - self.clamp_ratio)
        upper_bound = self._last_eta_seconds * (1.0 + self.clamp_ratio)
        if raw_eta_seconds < lower_bound:
            return lower_bound
        if raw_eta_seconds > upper_bound:
            return upper_bound
        return raw_eta_seconds


class ETAEstimator:
    """Central ETA estimator driven by processing events."""

    def __init__(self, strategy: Optional[ETAStrategy] = None) -> None:
        self._strategy = strategy or AdaptiveEwmaEtaStrategy()
        self._total_items = 0
        self._start_time: Optional[float] = None

    def configure_total_items(self, total_items: int) -> None:
        self._total_items = max(0, int(total_items))

    def record_completion(self, timestamp: float) -> None:
        if self._start_time is None:
            self._start_time = timestamp
        self._strategy.record_completion(timestamp)

    def set_start_time_if_missing(self, timestamp: float) -> None:
        if self._start_time is None:
            self._start_time = timestamp

    def build_state(self, *, processed_items: int, active_items: int, now: Optional[float] = None) -> ETAState:
        current_time = now if now is not None else self._start_time
        if current_time is None:
            current_time = 0.0
        return self._strategy.build_state(
            now=current_time,
            start_time=self._start_time,
            total_items=self._total_items,
            processed_items=processed_items,
            active_items=active_items,
        )


def is_terminal_status(status: str) -> bool:
    """Check whether a worker status marks a terminal PO outcome."""
    return status.upper() in TERMINAL_STATUSES


def format_eta_seconds(seconds: float) -> str:
    """Format ETA in compact human-readable form."""
    whole_seconds = max(0, int(round(seconds)))
    if whole_seconds < 60:
        return f"{whole_seconds}s"
    if whole_seconds < 3600:
        minutes, secs = divmod(whole_seconds, 60)
        return f"{minutes}m {secs}s"
    hours, remainder = divmod(whole_seconds, 3600)
    minutes = remainder // 60
    return f"{hours}h {minutes}m"
