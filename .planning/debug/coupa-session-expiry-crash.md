# Debug Session: coupa-session-expiry-crash

**Status**: DEBUG_COMPLETE  
**Created**: 2025-07-21  
**Slug**: coupa-session-expiry-crash  

## Symptoms

### Expected Behavior
- Processar todos os POs do input.csv com 8 workers paralelos
- ~40% dos POs retornando "not found" no Coupa é normal e aceitável
- 100% de falha com "Oops" é inaceitável — indica problema sistêmico, não POs faltantes

### Actual Behavior
- **~100% Coupa "Oops" error pages** em todos os POs processados (falha muito rápida, 0.02-0.04s)
- **worker-2 browser crash** → cascade de "Failed to create tab" para ~50+ POs
- **Profile limit exceeded: 8/8** ao tentar escalar workers
- **Processo terminou abruptamente** antes de concluir

### Error Messages (confirmed from terminal)
```
Coupa displayed an error page: Oops! We couldn't find what you wanted
Error closing tab: Message: unknown error: failed to close window in 20 seconds  
Failed to create tab: Failed to create new tab
Failed to start worker: Profile limit exceeded: 8/8
Error in resource scaling monitor error=Profile limit exceeded: 8/8
```

### Timeline
- Funcionou antes, parou recentemente
- Reprodução: `uv run python -m src.Core_main` com 8 workers e input.csv atual

## Root Cause Hypotheses

| # | Hypothesis | Confidence | Notes |
|---|-----------|-----------|-------|
| H1 | Coupa session expired mid-run; no detection/recovery | HIGH | Falhas em 0.02-0.04s = redirect imediato sem autenticação |
| H2 | Browser crash no worker-2 sem graceful recovery | HIGH | Confirmado no stacktrace do msedgedriver |
| H3 | Profile limit capped impede scaling quando necessário | MEDIUM | Comportamento esperado mas pode agravar H2 |

## Investigation Log

### Cycle 1 — Initial Analysis
- [x] Inspecionar código de detecção de sessão Coupa  
- [x] Verificar recovery logic quando `Oops` page é detectada  
- [x] Analisar worker crash/recovery flow  
- [x] Verificar profile limit config vs. intended worker count  

## Findings

### Finding 1 — Session Expiry: No Detection, No Recovery

**Files involved**: `src/lib/downloader.py`, `src/workers/browser_session.py`, `src/workers/verifiers/auth_verifier.py`, `src/core/exceptions.py`

When Coupa session expires mid-run, it redirects the browser to a session-error or login page that contains "Oops!" text. `downloader.py:download_attachments_for_po()` (line ~951) calls `_detect_error_page('early')` immediately after navigation. This fires in 0.02–0.04 seconds (the redirect speed), finds "Oops!" in the page, and returns `status_code='PO_NOT_FOUND'`. No session check. No recovery. Move on.

**The gap**: The code cannot distinguish between:
- **Legitimate PO not found** (Coupa found the session but not the PO)
- **Session expired redirect** (Coupa redirected to a session error page with "Oops!")

The telltale sign is the URL after redirect. A PO-not-found stays at `/order_headers/{id}` with an Oops overlay. A session expiry redirects to `/sessions/new` or `/login` or similar.

**Existing infrastructure — never wired up**:
- `SessionExpiredError` — defined in `src/core/exceptions.py:242`, never raised from the downloader path
- `recover_session()` — fully implemented in `src/workers/browser_session.py:581`, never called from `downloader.py`
- `AuthVerifier` — `src/workers/verifiers/auth_verifier.py` is a **stub** that always returns `success=True` (line 17), never does real auth verification
- `src/core/retry.py:337` has `retryable_exceptions=(BrowserInitError, SessionExpiredError, ...)` — but `SessionExpiredError` is never raised from the Oops detection path, so retry never triggers

### Finding 2 — Worker Crash Cascade: `create_tab` Failure Silently Absorbed

**Files involved**: `src/workers/worker_process.py`, `src/workers/browser_session.py`, `src/workers/persistent_pool.py`

After worker-2's browser crashes (msedgedriver "failed to close window in 20 seconds"), every subsequent `create_tab()` call fails with `RuntimeError("Failed to create new tab")` (`browser_session.py:318, 337`).

In `worker_process.py:_process_po_task()` (line 849), `create_tab()` is inside a `try/except Exception` block (line ~901). The `RuntimeError` is caught, formatted as `status_code='FAILED'`, and **returned as a normal result dict**. No exception propagates.

Back in `persistent_pool.py`, `process_task()` returns that dict without raising — so the thread-level `except Exception` at line ~996 never fires, and `asyncio.run_coroutine_threadsafe(self._restart_worker(...))` is never called.

Result: the worker loop keeps receiving tasks, `create_tab` keeps failing, 50+ tasks are marked FAILED — and the pool never restarts the worker. The worker appears "alive" (heartbeat runs, `is_healthy()` may still pass if `browser_session.driver` is not None), but it can't process anything.

### Finding 3 — Profile Limit: No Headroom During Crash/Restart Overlap

**Files involved**: `src/workers/persistent_pool.py`, `src/workers/profile_manager.py`

`persistent_pool.py:136`:
```python
profile_cap = max(config.worker_count, 8)  # = 8 when worker_count=8
ProfileManager(..., max_profiles=profile_cap)
```

With 8 workers and a cap of 8, there is zero headroom. When worker-2 crashes and `_do_restart_worker()` starts:
1. `old_worker.stop()` → `_cleanup_browser_session()` triggers a 20-second msedgedriver hang
2. During that hang, the profile slot for worker-2 **is still counted** in `temp_profiles` (8/8)
3. The resource scaling monitor (`line ~1245`) detects the crashed worker and tries `_restart_worker` → internally calls `create_profile(worker_id)` → hits `Profile limit exceeded: 8/8`

The `create_profile()` method does `self.temp_profiles.pop(worker_id, None)` at the top (line ~198), which *would* free the slot — but only when called for the same `worker_id`. The race occurs because `release_profile()` is never explicitly called before the 20-second hang window.

## Fix Plan

### Priority 1 (CRITICAL) — Session Expiry Detection + Recovery

**File**: `src/lib/downloader.py`, method `download_attachments_for_po()` (~line 951)

After `error_info` is returned by `_detect_error_page()`, add a URL check **before** returning `PO_NOT_FOUND`:

```python
if error_info:
    # NEW: Check if the current URL indicates a session redirect (not a PO-specific error)
    try:
        current_url = self.driver.current_url.lower()
        session_redirect_signals = ['/sessions/new', '/login', 'session_expired', 'sso', '/auth/']
        is_session_redirect = any(sig in current_url for sig in session_redirect_signals)
    except Exception:
        is_session_redirect = False

    if is_session_redirect:
        # Raise SessionExpiredError so the retry layer can call recover_session()
        from ..core.exceptions import SessionExpiredError
        raise SessionExpiredError(f"Session expired — redirected to: {current_url}")
    
    # existing PO_NOT_FOUND return here...
```

**File**: `src/workers/worker_process.py`, method `_process_po_task()`

Wrap the `process_single_po` call to catch `SessionExpiredError` and attempt `browser_session.recover_session()`:

```python
from ..core.exceptions import SessionExpiredError
try:
    result_entry = process_single_po(...)
except SessionExpiredError:
    logger.warning("Session expired during PO processing; attempting recovery", worker_id=self.worker_id)
    if self.browser_session.recover_session():
        result_entry = process_single_po(...)  # one retry after recovery
    else:
        raise  # propagate to trigger worker restart
```

**File**: `src/workers/verifiers/auth_verifier.py`

Replace the stub with a real URL-check-based verification. The simplest approach: navigate to a known authenticated URL and check if the current URL contains a login redirect.

### Priority 2 (HIGH) — Worker Crash Self-Detection via Consecutive Tab Failure

**File**: `src/workers/worker_process.py`

Add a consecutive `create_tab` failure counter to `WorkerProcess.__init__`:
```python
self._consecutive_tab_failures: int = 0
self._max_consecutive_tab_failures: int = 3
```

In `_process_po_task()`, around line 849:
```python
try:
    tab_handle = self.browser_session.create_tab(task.task_id)
    self._consecutive_tab_failures = 0  # reset on success
except RuntimeError as e:
    self._consecutive_tab_failures += 1
    if self._consecutive_tab_failures >= self._max_consecutive_tab_failures:
        # Browser is dead — propagate so the pool restarts the worker
        raise  # RuntimeError bubbles through process_task() to pool thread
    # Otherwise return a normal FAILED result
    return {
        'success': False, 'error': str(e), 'task_id': task.task_id,
        'status_code': 'FAILED', 'po_number': po_number,
    }
```

When `RuntimeError` propagates out of `process_task()`, the pool's thread exception handler at `persistent_pool.py:996` catches it and calls `_restart_worker()`.

### Priority 3 (MEDIUM) — Profile Limit Headroom

**File**: `src/workers/persistent_pool.py`, line 136

Change:
```python
profile_cap = max(config.worker_count, 8)
```
To:
```python
# +2 headroom: one spare slot during crash recovery overlap + one for scale-up
profile_cap = max(config.worker_count + 2, 10)
```

This ensures that during worker-N crash + 20-second hang, there's always room to issue the restart's `create_profile()` call.

Alternatively (more surgical): in `_do_restart_worker()` at line ~1057, call `self.profile_manager.release_profile(worker_id)` **before** `old_worker.stop()`, so the slot is freed before the potential hang.

## Risk Assessment

| Fix | Risk | Notes |
|-----|------|-------|
| Session URL check | LOW | Read-only URL inspection; conservative signal list |
| `recover_session()` call | MEDIUM | Re-authentication flow adds latency (~5-10s per recovery); must not block other workers |
| `SessionExpiredError` raising | LOW | Existing exception type; existing retry plumbing |
| Consecutive tab failure counter | LOW | Purely additive counter; no behavior change for 1-2 failures |
| Propagating `RuntimeError` on crash | MEDIUM | Changes what pool sees; verify `_release_reserved_worker_tasks()` is called before restart |
| Profile cap +2 | LOW | Increases max RAM slightly; well within `max_profiles ≤ 16` guard |
| `release_profile()` before stop | MEDIUM | Profile dir freed before browser cleanly closes — verify cleanup sequence doesn't double-free |

## Current Focus

- hypothesis: Confirmed. The crash pattern is a compound failure: session-expiry redirect misclassified as PO_NOT_FOUND, tab creation failures absorbed as normal FAILED tasks, and zero profile headroom during overlap restart.
- next_action: Completed implementation and verification for P1/P2/P3.

## Evidence

- timestamp: 2026-05-19T23:50:00-03:00
    action: implemented P1 in downloader with session-redirect URL detection and SessionExpiredError escalation
    files: src/lib/downloader.py
- timestamp: 2026-05-19T23:50:00-03:00
    action: implemented P2 in worker process with consecutive create_tab failure escalation and fatal propagation to pool restart path
    files: src/workers/worker_process.py
- timestamp: 2026-05-19T23:50:00-03:00
    action: implemented auth verification URL redirect check instead of unconditional stub success
    files: src/workers/verifiers/auth_verifier.py
- timestamp: 2026-05-19T23:50:00-03:00
    action: implemented P3 profile cap headroom (+2, min 10)
    files: src/workers/persistent_pool.py
- timestamp: 2026-05-19T23:50:00-03:00
    action: added/updated targeted tests for session redirect, worker fatal escalation/recovery, and profile cap headroom
    files: tests/unit/test_downloader_session_redirect.py, tests/unit/test_worker_process_recovery_escalation.py, tests/unit/test_persistent_pool_scaling.py
- timestamp: 2026-05-19T23:50:00-03:00
    action: validation run passed (17/17)
    command: uv run pytest tests/unit/test_worker_process_recovery_escalation.py tests/unit/test_downloader_session_redirect.py tests/unit/test_persistent_pool_scaling.py

## Resolution

- root_cause: Session-expiry redirects and dead-browser tab failures were treated as ordinary PO/task failures, preventing recovery and worker restart; restart overlap also had no profile-slot headroom.
- fix: Added redirect-based SessionExpiredError signaling, worker-fatal escalation with restart propagation after repeated tab failures and unrecoverable session recovery, plus profile-cap headroom and targeted regression tests.
- verification: Targeted unit suite passed with all new scenarios green.
