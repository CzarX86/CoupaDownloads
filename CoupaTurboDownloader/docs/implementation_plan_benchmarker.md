# Implementation Plan – Benchmarker Module

## Goal
Create `src/engine/benchmarker.py` that measures network latency and throughput to Coupa endpoints, suggesting optimal concurrency and delay settings for the downloader.

## Design Overview
- Provide a simple async function `async def benchmark(urls: list[str]) -> dict` that:
  1. Performs `httpx.AsyncClient` HEAD requests to each URL concurrently (default 5 workers).
  2. Measures round‑trip time and download speed for a small payload (e.g., a 1 KB request).
  3. Returns statistics: min/avg/max latency, suggested `concurrency` (capped at 12) and `delay` (in seconds) based on observed latency.
- Expose a CLI entry point `python -m src.engine.benchmarker` that reads URLs from a file or stdin and prints a JSON summary.
- Include a small utility to map latency → concurrency heuristics (e.g., low latency → higher concurrency, high latency → lower).

## Implementation Steps
1. Import `asyncio`, `httpx`, `statistics`.
2. Define helper `_measure(url: str) -> float` returning latency in seconds.
3. Implement `async def benchmark(urls, max_workers=5)` that gathers latencies.
4. Derive suggestions:
   - `concurrency = min(12, max(2, int(1 / (avg_latency + 0.05)))`
   - `delay = min(0.1, avg_latency / 2)`
5. Add `if __name__ == "__main__":` block for CLI.
6. Add type hints, docstrings, and robust error handling (timeouts, retries).

## Verification Plan
- **Unit Test**: Mock `httpx.AsyncClient` to return controlled latencies and assert the returned suggestion dictionary matches expectations.
- **Integration Test**: Run the CLI against a mock server (e.g., httpbin.org/bytes/1024) and verify JSON output.
- **Manual Test**: Execute `python -m src.engine.benchmarker https://example.com/api` and ensure reasonable suggestions appear.

---
*Prepared by Antigravity – please review and approve.*
