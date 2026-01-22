# PR 25 — Single‑Session Profile Bootstrap + Multi‑Window Workers (Ctrl+N/New Window)
- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: TBD
- Observações:


## Estado da revisão (2025-09-25)

- [ ] Implementado no código-base. `src/core/browser.py` não possui helper `open_new_window` e `src/Core_main.py` continua utilizando apenas `ProcessPoolExecutor` sem lógica de multi-janela quando `USE_EDGE_PROFILE=true`, evidenciando que o plano não foi aplicado.


## Objective
Enable stable multi‑window automation when an Edge profile is required by:
- Loading the Edge profile once in a single WebDriver session.
- Spawning additional windows in the same session (Ctrl+N / `new_window`) so all windows share the loaded profile.
- Routing away from process‑based workers when `USE_EDGE_PROFILE=true` to avoid profile lock errors.
- Preserving headless compatibility and careful PO pipeline management.

## Scope
- Add helper in `BrowserManager` to open additional windows in the same session, compatible with headless.
- In `MainApp.run()`, when `USE_EDGE_PROFILE=true` and concurrency > 1, automatically use an in‑process multi‑window path instead of multiple processes.
- Implement a small window pool with locking and round‑robin assignment so each PO runs in one window at a time.
- Keep downloads, folder naming, and Excel/CSV updates exactly as they are.

Out of scope:
- No large refactor of the downloader or tab inventory modules.
- No change to existing defaults unless `USE_EDGE_PROFILE=true` and concurrency > 1.

## Affected Files
- Update: `src/core/browser.py` (helper: `open_new_window` with headless fallback; optional `ensure_window_focus`)
- Update: `src/Core_main.py` (introduce multi‑window pipeline path guarded by `USE_EDGE_PROFILE` and concurrency; window pool + locking)

## Pseudodiff (representative)
```diff
--- src/core/browser.py
+++ src/core/browser.py
@@ class BrowserManager:
+    def open_new_window(self) -> str:
+        """Open a new top‑level window in the same WebDriver session and return its handle."""
+        if not self.driver:
+            raise RuntimeError("Driver not initialized")
+        try:
+            # Works in headless/new Chromium
+            self.driver.switch_to.new_window('window')
+            return self.driver.current_window_handle
+        except Exception:
+            # Fallback for non‑headless only: try Ctrl+N
+            try:
+                from selenium.webdriver.common.keys import Keys
+                from selenium.webdriver.common.action_chains import ActionChains
+                actions = ActionChains(self.driver)
+                actions.key_down(Keys.CONTROL).send_keys('n').key_up(Keys.CONTROL).perform()
+                time.sleep(0.2)
+                return self.driver.window_handles[-1]
+            except Exception as e:
+                raise RuntimeError(f"Could not open a new window: {e}")

--- src/Core_main.py
+++ src/Core_main.py
@@ class MainApp:
+    def _open_additional_windows(self, count: int) -> list[str]:
+        """Open N‑1 additional windows (keeping current as first) and return all window handles."""
+        with self.lock:
+            if self.driver is None:
+                raise RuntimeError("Driver is not initialized")
+            handles = [self.driver.current_window_handle]
+            for _ in range(max(0, count - 1)):
+                hid = self.browser_manager.open_new_window()
+                handles.append(hid)
+            return handles
+
+    def _process_po_on_window(self, window_id: str, po_data: dict) -> dict:
+        """Switch to a specific window and run the existing single‑PO logic (downloader path)."""
+        with self.lock:
+            try:
+                self.driver.switch_to.window(window_id)
+            except Exception:
+                pass
+        # Reuse current process_single_po internals in a window‑scoped manner
+        # (download dir per PO, downloader invocation, wait for downloads, status/CSV update)
+        # Returns the same result dict used in the current sequential path
+        return {
+            'ok': self.process_single_po(po_data, self.folder_hierarchy.analyze_excel_structure(pd.DataFrame())[1], False, 0, 1)
+        }
+
+    def _run_multi_window_pipeline(self, po_data_list: list[dict], windows: int, max_workers: int) -> None:
+        """Run multiple POs in parallel across multiple windows within one session (shared profile)."""
+        with self.lock:
+            if self.driver is None:
+                self.initialize_browser_once()
+        window_ids = self._open_additional_windows(windows)
+        print(f"🪟 Opened {len(window_ids)} window(s) in single session with profile")
+
+        # simple window pool (one task per window at a time)
+        import queue
+        window_pool: "queue.Queue[str]" = queue.Queue()
+        for wid in window_ids:
+            window_pool.put(wid)
+
+        def task(po):
+            wid = window_pool.get()
+            try:
+                return self._process_po_on_window(wid, po)
+            finally:
+                window_pool.put(wid)
+
+        from concurrent.futures import ThreadPoolExecutor, as_completed
+        workers = max(1, min(max_workers, len(window_ids)))
+        with ThreadPoolExecutor(max_workers=workers) as executor:
+            futures = [executor.submit(task, po) for po in po_data_list]
+            for _ in as_completed(futures):
+                pass
+
@@ def run(self) -> None:
-        if use_process_pool:
+        if use_process_pool:
             # Real parallelism: one Edge driver per process
             # Limit concurrency to reduce Edge rate-limits and memory pressure
             default_workers = min(2, len(po_data_list))
             env_procs = int(os.environ.get("PROC_WORKERS", str(default_workers)))
             hard_cap = int(os.environ.get("PROC_WORKERS_CAP", "3"))
             proc_workers = max(1, min(env_procs, hard_cap, len(po_data_list)))
-            print(f"📊 Using {proc_workers} process worker(s), one WebDriver per process")
+            # Avoid profile locks: if profile is enabled and asking for >1 process, route to multi‑window
+            if Config.USE_PROFILE and proc_workers > 1:
+                print("⚠️ Edge profile enabled with multiple workers; switching to single‑session multi‑window mode")
+                windows = int(os.environ.get('WINDOWS_PER_SESSION', '2'))
+                max_threads = int(os.environ.get('THREAD_WORKERS', str(min(2, windows))))
+                self.initialize_browser_once()
+                self._run_multi_window_pipeline(po_data_list, windows=windows, max_workers=max_threads)
+            else:
+                print(f"📊 Using {proc_workers} process worker(s), one WebDriver per process")
+                # (existing ProcessPoolExecutor path unchanged)
         else:
             # Legacy in-process mode (single WebDriver, sequential)
             print("📊 Using in-process mode (single WebDriver, sequential)")
             self.initialize_browser_once()
             for i, po_data in enumerate(po_data_list):
                 ok = self.process_single_po(po_data, hierarchy_cols, has_hierarchy_data, i, len(po_data_list))
                 if ok:
                     successful += 1
                 else:
                     failed += 1
```

Notes:
- The representative snippet shows where the routing and helpers are added, not the full implementations. The sequential `process_single_po` is reused to preserve download folder logic and CSV updates.
- Headless compatibility is provided by defaulting to `switch_to.new_window('window')`. The Ctrl+N fallback is only attempted in non‑headless sessions.

## Acceptance Criteria
- When `USE_EDGE_PROFILE=true` and the user requests more than 1 worker, the app logs a notice and switches to a single‑session multi‑window mode automatically.
- Two or more windows open in the same session; all windows operate with the loaded profile (cookies/extensions available).
- Headless mode works (windows created via `new_window`).
- No profile lock errors occur; the pipeline processes multiple POs concurrently across windows and updates CSV/Excel exactly as before.

## Minimal Manual Tests
+ Profile multi‑window (non‑headless):
 1) Set `USE_EDGE_PROFILE=true`, `WINDOWS_PER_SESSION=2`, and attempt multiple workers.
 2) Observe the log message about switching to single‑session multi‑window.
 3) Verify two windows open, profile cookies/extensions are present in both.
 4) Run on a small list of POs; confirm downloads and CSV updates are correct.

+ Headless:
 5) Set `HEADLESS=true`, `WINDOWS_PER_SESSION=2` and repeat; confirm windows are created and processing succeeds.

## Suggested Commit Message and Branch
- Plan branch: `plan/25-single-session-profile-multi-window-workers`
- Impl branch: `feat/25-single-session-profile-multi-window-workers`
- Plan commit: `docs(pr-plan): PR 25 — single-session profile + multi-window workers`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff (small/representative) included.
- [x] Acceptance criteria and minimal manual tests.
- [x] Suggested commit message and branch name.

