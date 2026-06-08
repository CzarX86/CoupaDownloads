# Quick Task: Integrate PoC Code into CoupaTurboDownloader

**Source:** poc_downloader.py (465 lines), test_po_fetch.py (44 lines)
**Goal:** Extrair codigo dos PoCs e integrar nos modulos existentes

## Changes

### 1. parser.py — Two-pass HTML parser
- Add `data-url` attribute scan in `<span>` elements (pass 1)
- Add `href` scan in `<a>` tags with attachment/download patterns (pass 2)
- Add URL joining with `httpx.URL().join()`
- Keep existing `extract_pr_link` and `deduplicate_attachments`

### 2. crawler.py — Real HTTP fetch + concurrent semaphore
- Replace `_fetch_po_html` NotImplementedError with real httpx GET
- Replace `_download_attachment` NotImplementedError with real httpx stream download
- Add `asyncio.Semaphore` for concurrency control
- Add rate limiting delay between requests
- Add 429 detection and auth failure detection
- Add cookies and headers support
- Fix Circuit Breaker: threshold check `> 0` → `>= 3`
- Make `process_po` accept async client parameter

### 3. benchmarker.py — NEW: Genetic algorithm port
- Port `Chromosome` class from PoC
- Port `evaluate_individual` function
- Port `run_genetic_tuning` function
- API: `async def benchmark(urls: list[str]) -> dict`

### 4. rate_limiter.py — NEW: Adaptive rate limiting
- 429 detection with exponential backoff
- Configurable base delay (default 0.03s)
- Cooldown windows for batches >500 POs
- Integration point for benchmarker recommendations

### 5. authenticator.py — NEW: Selenium Edge → cookies
- Open Edge via Selenium for manual login
- Extract cookies after user completes login
- Return cookies dict for httpx engine
- API: `async def get_coupa_cookies() -> dict`

### 6. updater.py — NEW: GitHub Releases self-updater
- Check GitHub Releases API for new versions
- Download new binary in background
- Atomic replace via batch/shell script
- UI notification integration point

### 7. api.py — Concurrent processing fix
- Replace sequential `for row in rows` with `asyncio.gather` + semaphore
- Maintain pause/stop/resume runtime checks

### 8. session_db.py — attachment_count tracking
- Add `attachment_count` column to po_downloads

## Bugs Fixed
- Circuit Breaker: `stats['processed'] > 0` → `stats['processed'] >= 3`
- Sequential processing → concurrent with configurable semaphore
