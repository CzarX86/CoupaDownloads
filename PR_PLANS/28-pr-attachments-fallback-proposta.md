# PR 28 — Fallback to PR (Requisition) Attachments When PO Has None
- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: TBD
- Observações: 


## Objective
When a PO page has zero attachments, automatically navigate to the originating PR (Requisition) page and attempt to find/download attachments there, saving files into the same PO folder. Keep existing behavior unchanged when PO has attachments.

## Scope
- Add a conditional fallback path in the downloader flow: if no attachments on the PO page, try the PR page.
- Detect and navigate to the PR page from the PO header (typical Coupa link labeled “Requisition” with anchor text like “PR123456”).
- Reuse the current attachment discovery and download logic on the PR page.
- Preserve all existing folder hierarchy and CSV updates; downloads must land in the same PO folder.

Out of scope:
- No changes to how we compute folder names or status suffixes.
- No concurrency model changes and no driver/profile defaults changes.

## Affected Files
- Update: `src/core/downloader.py` (fallback flow + navigation to PR)
- Update: `src/core/config.py` (add PR link selectors + optional toggle)

## Pseudodiff (representative)
```diff
--- src/core/config.py
+++ src/core/config.py
@@ class Config:
     # MSG processing controls
     FILTER_MSG_ARTIFACTS = os.environ.get("FILTER_MSG_ARTIFACTS", "true").lower() == "true"
     MSG_ARTIFACT_MIN_SIZE = int(os.environ.get("MSG_ARTIFACT_MIN_SIZE", "1024"))
     MSG_IMAGE_MIN_SIZE = int(os.environ.get("MSG_IMAGE_MIN_SIZE", "5120"))
 
     # Folder naming controls
     ADD_STATUS_SUFFIX = os.environ.get("ADD_STATUS_SUFFIX", "false").lower() == "true"
 
     # Profile usage and startup behavior
     USE_PROFILE = os.environ.get("USE_EDGE_PROFILE", "true").lower() == "true"
     CLOSE_EDGE_PROCESSES = os.environ.get("CLOSE_EDGE_PROCESSES", "true").lower() == "true"
 
+    # Fallback behavior (enabled by default)
+    PR_FALLBACK_ENABLED = os.environ.get("PR_FALLBACK_ENABLED", "true").lower() == "true"
+
+    # PR (Requisition) link detection from PO page
+    PR_LINK_CSS_SELECTORS = [
+        "#order_header_requisition a",
+        "a[href*='requisition_headers']",
+        "a[href*='/requisitions/']",
+        "a[href*='requisition']",
+    ]
+    PR_LINK_XPATH_CANDIDATES = [
+        "//*[@id='order_header_requisition_header']//a[contains(@href,'requisition')]",
+        "//label[contains(.,'Requisition')]/following::a[contains(@href,'requisition')][1]",
+        "//a[starts-with(normalize-space(), 'PR') and contains(@href,'requisition')]",
+    ]
```
```diff
--- src/core/downloader.py
+++ src/core/downloader.py
@@ class Downloader:
     def download_attachments_for_po(self, po_number: str) -> dict:
@@
-        attachments = self._find_attachments()
-        supplier = self._extract_supplier_name()
-        if not attachments:
-            msg = "No attachments found."
-            print(f"   ✅ {msg}")
-            return {
-                'success': True,
-                'message': msg,
-                'supplier_name': supplier or '',
-                'attachments_found': 0,
-                'attachments_downloaded': 0,
-                'coupa_url': url,
-                'attachment_names': [],
-            }
+        attachments = self._find_attachments()
+        supplier = self._extract_supplier_name()
+        if not attachments and Config.PR_FALLBACK_ENABLED:
+            print("   📭 No attachments on PO; trying PR (Requisition) page…")
+            pr_url = self._navigate_to_pr_from_po()
+            if pr_url:
+                print(f"   🔗 Navigated to PR: {pr_url}")
+                attachments = self._find_attachments()
+                if attachments:
+                    url = pr_url  # report actual page where attachments were found
+                else:
+                    print("   ℹ️ No attachments on PR page either.")
+            else:
+                print("   ℹ️ Could not locate PR link from PO page.")
+
+        if not attachments:
+            msg = "No attachments found."
+            print(f"   ✅ {msg}")
+            return {
+                'success': True,
+                'message': msg,
+                'supplier_name': supplier or '',
+                'attachments_found': 0,
+                'attachments_downloaded': 0,
+                'coupa_url': url,
+                'attachment_names': [],
+            }
@@
         else:
             msg = f"Failed to download any of the {total_attachments} attachments."
             print(f"   ❌ {msg}")
             return {
                 'success': False,
                 'message': msg,
                 'supplier_name': supplier or '',
                 'attachments_found': total_attachments,
                 'attachments_downloaded': 0,
                 'coupa_url': url,
                 'attachment_names': names_list,
             }
+
+    def _navigate_to_pr_from_po(self) -> Optional[str]:
+        """Try to find and navigate to the PR (Requisition) page from a PO.
+
+        Returns the PR URL if navigation succeeded (or href discovered), otherwise None.
+        """
+        try:
+            # 1) Try CSS selectors
+            for sel in getattr(Config, 'PR_LINK_CSS_SELECTORS', []) or []:
+                try:
+                    links = self.driver.find_elements(By.CSS_SELECTOR, sel)
+                except Exception:
+                    links = []
+                for a in links:
+                    href = (a.get_attribute('href') or '').strip()
+                    if href:
+                        self.driver.get(href)
+                        return href
+
+            # 2) Try XPath candidates
+            for xp in getattr(Config, 'PR_LINK_XPATH_CANDIDATES', []) or []:
+                try:
+                    as_ = self.driver.find_elements(By.XPATH, xp)
+                except Exception:
+                    as_ = []
+                for a in as_:
+                    href = (a.get_attribute('href') or '').strip()
+                    if href:
+                        self.driver.get(href)
+                        return href
+        except Exception:
+            pass
+        return None
```

## Acceptance Criteria
- If PO has attachments: existing behavior remains unchanged (no PR navigation).
- If PO has zero attachments and PR fallback is enabled:
  - Downloader attempts to navigate to the PR page via the “Requisition” link.
  - If PR contains attachments, they are discovered and download clicks are issued using the same logic.
  - Files save into the same PO folder (unchanged download directory).
  - Result counters reflect the PR attachments (`attachments_found`/`attachments_downloaded` > 0) and `coupa_url` reports the page where attachments were found (PR URL when applicable).
- If neither PO nor PR has attachments, status remains “NO_ATTACHMENTS” with message “No attachments found.”
- If the PR link is not present or navigation fails, the tool gracefully returns “No attachments found.” without crashing.

## Minimal Manual Tests
1) PO with attachments
   - Input a PO known to have attachments in the PO page.
   - Expect: No fallback; counts > 0; folder contains downloaded files.
2) PO without attachments, PR with attachments
   - Input a PO with zero attachments but corresponding PR has files.
   - Expect: Log shows fallback to PR; counts > 0; files downloaded to the PO folder; `coupa_url` matches the PR URL.
3) PO and PR without attachments
   - Input a PO where neither PO nor PR has files.
   - Expect: “No attachments found.”, status “NO_ATTACHMENTS”, no files.
4) Missing PR link
   - Use a test PO page variant lacking the “Requisition” link.
   - Expect: Graceful message, no crash, still “No attachments found.”

## Suggested Commit Message and Branch
- Plan branch: `plan/28-pr-attachments-fallback`
- Impl branch: `feat/28-pr-attachments-fallback`
- Plan commit: `docs(pr-plan): PR 28 — fallback to PR attachments when PO has none`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff (small, readable, representative of the approach).
- [x] Acceptance criteria and minimal manual tests.
- [x] Suggested commit message and branch name.
