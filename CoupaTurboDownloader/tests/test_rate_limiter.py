import asyncio
import time
import pytest
from src.engine.rate_limiter import RateLimiter


def test_initial_delay():
    rl = RateLimiter(base_delay=0.03)
    assert rl.current_delay == 0.03


def test_default_values():
    rl = RateLimiter()
    assert rl.base_delay == 0.03
    assert rl.cooldown_threshold == 500


@pytest.mark.asyncio
async def test_wait_applies_base_delay():
    rl = RateLimiter(base_delay=0.01)
    start = time.monotonic()
    await rl.wait()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.005  # ~0.01s, allow small variance


def test_report_429_increases_backoff():
    rl = RateLimiter(base_delay=0.03)
    rl.report_429()
    assert rl.current_delay >= 0.06  # 0.03 * 2^1


def test_report_429_exponential():
    rl = RateLimiter(base_delay=0.03)
    rl.report_429()
    rl.report_429()
    assert rl.current_delay >= 0.12  # 0.03 * 2^2


def test_report_success_reduces_backoff():
    rl = RateLimiter(base_delay=0.03)
    rl.report_429()
    rl.report_429()
    assert rl._consecutive_429s == 2
    rl.report_success()
    assert rl._consecutive_429s == 1


def test_backoff_capped_at_5_seconds():
    rl = RateLimiter(base_delay=0.03)
    for _ in range(20):
        rl.report_429()
    assert rl.current_delay <= 5.0


def test_reset():
    rl = RateLimiter(base_delay=0.03)
    rl.report_429()
    rl.report_429()
    rl.reset()
    assert rl.current_delay == 0.03
    assert rl._consecutive_429s == 0
    assert rl._request_count == 0


@pytest.mark.asyncio
async def test_wait_cooldown_for_large_batches():
    rl = RateLimiter(base_delay=0.01, cooldown_threshold=3)
    # First 3 requests normal delay
    await rl.wait()
    await rl.wait()
    await rl.wait()
    # 4th should have cooldown delay (3x base)
    start = time.monotonic()
    await rl.wait()
    elapsed = time.monotonic() - start
    # 3x 0.01 = 0.03s
    assert elapsed >= 0.02
