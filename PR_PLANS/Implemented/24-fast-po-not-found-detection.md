# PR 24 — Fast “PO Not Found/No Access” Detection and Early Exit

## Objective
Detect Coupa “not found/no access” pages immediately and skip waits/retries when confident the PO page cannot be accessed. This reduces wasted time and improves throughput when POs are invalid or the user lacks access to a company code.

## Scope
- Centralize error page detection markers in config and reuse across modules.
- Add a short, early check after navigation to fast‑fail before attachment waits.
- Apply in both the downloader path and the multi‑tab inventory path.
- Keep defaults/additive; do not change unrelated timeouts or the pipeline.

Out of scope:
- No broader refactors to tab/window orchestration.
- No UI text changes.

## Affected Files
- Update: `src/core/config.py` (error markers + short timeout flag)
- Update: `src/core/downloader.py` (use markers; early exit already present → make robust)
- Update: `MyScript/browser_tab_manager.py` (early check right after `get(url)`; reuse markers)

## Pseudodiff (representative)
```diff
--- src/core/config.py
+++ src/core/config.py
@@ class Config:
     # Timeouts
     PAGE_LOAD_TIMEOUT = 15
     ATTACHMENT_WAIT_TIMEOUT = 15
     DOWNLOAD_WAIT_TIMEOUT = 30
+
+    # Error page detection (Coupa “Oops/No Access” markers)
+    ERROR_PAGE_MARKERS = [
+        "Oops! We couldn't find what you wanted",
+        "You are not authorized",
+        "Access denied",
+        "The page you were looking for doesn't exist",
+    ]
+    ERROR_PAGE_CHECK_TIMEOUT = int(os.environ.get("ERROR_PAGE_CHECK_TIMEOUT", "4"))
+    EARLY_ERROR_CHECK_BEFORE_READY = os.environ.get("EARLY_ERROR_CHECK_BEFORE_READY", "true").lower() == "true"

--- src/core/downloader.py
+++ src/core/downloader.py
@@ def download_attachments_for_po(self, po_number: str) -> dict:
-        # Check for error page, a useful feature from the recent changes
-        if "Oops! We couldn't find what you wanted" in self.driver.page_source:
+        # Early error page detection (fast‑fail)
+        page = self.driver.page_source.lower()
+        if any(m.lower() in page for m in Config.ERROR_PAGE_MARKERS):
             msg = "PO not found or page error detected."
             print(f"   ❌ {msg}")
             return {
                 'success': False,
                 'message': msg,
                 'supplier_name': '',
                 'attachments_found': 0,
                 'attachments_downloaded': 0,
                 'coupa_url': url,
                 'attachment_names': [],
             }

--- MyScript/browser_tab_manager.py
+++ MyScript/browser_tab_manager.py
@@ class BaseTabManager(ITabManager):
     def create_tab_for_url(self, url_index: int, url: str, 
                           window_id: str, window_name: str) -> Optional[TabInfo]:
@@
-            self.driver.get(url)
-            
-            # Aguardar carregamento
-            wait = WebDriverWait(self.driver, 10)
-            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
+            self.driver.get(url)
+
+            # Early error detection before full readyState wait (optional)
+            try:
+                from src.core.config import Config as _Cfg
+                if _Cfg.EARLY_ERROR_CHECK_BEFORE_READY:
+                    t0 = time.time()
+                    found = False
+                    while time.time() - t0 < _Cfg.ERROR_PAGE_CHECK_TIMEOUT:
+                        page = (self.driver.page_source or '').lower()
+                        if any(m.lower() in page for m in _Cfg.ERROR_PAGE_MARKERS):
+                            found = True
+                            break
+                        time.sleep(0.1)
+                    if found:
+                        print(f"🚫 [" + threading.current_thread().name + f"] Error page detected early for URL {url_index+1}")
+                        return None
+            except Exception:
+                pass
+
+            # Proceed to normal load wait
+            wait = WebDriverWait(self.driver, 10)
+            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

@@
     def _is_error_page(self, tab_id: str) -> bool:
@@
-            page_source = self.driver.page_source
-            error_detected = "Oops! We couldn't find what you wanted" in page_source
+            page_source = (self.driver.page_source or '').lower()
+            try:
+                from src.core.config import Config as _Cfg
+                error_detected = any(m.lower() in page_source for m in _Cfg.ERROR_PAGE_MARKERS)
+            except Exception:
+                error_detected = "oops! we couldn't find what you wanted" in page_source
             
             if error_detected:
                 print(f"🚫 Página de erro detectada para aba {tab_id}")
             
             return error_detected
```

## Acceptance Criteria
- Invalid/inaccessible POs (e.g., “Oops! We couldn't find what you wanted”) are detected within ~4 seconds from navigation.
- When an error page is detected, the system returns early without waiting attachment timeouts.
- The detection logic is centralized via `Config.ERROR_PAGE_MARKERS` and used by both downloader and tab manager paths.
- No change to success behavior for valid POs; attachment discovery and downloads still proceed as before.

## Minimal Manual Tests
1) Invalid PO
   - Use a known non‑existent PO number or a company code you cannot access.
   - Start a run and observe that for that PO the system logs the early detection and proceeds without long waits.
2) Valid PO
   - Use a known accessible PO.
   - Confirm normal behavior (no regression); attachments are inventoried/downloaded.
3) Marker coverage
   - Temporarily add a synthetic marker to `ERROR_PAGE_MARKERS`, load a test page containing that text, and verify detection triggers.

## Suggested Commit Message and Branch
- Plan branch: `plan/24-fast-po-not-found-detection`
- Impl branch: `feat/24-fast-po-not-found-detection`
- Plan commit: `docs(pr-plan): PR 24 — fast PO not-found/no-access detection`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff (small, readable) provided.
- [x] Acceptance criteria and minimal manual tests.
- [x] Suggested commit message and branch name.
