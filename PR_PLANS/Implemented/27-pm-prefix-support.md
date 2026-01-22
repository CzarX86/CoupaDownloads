# PR 27 — Support PM‑Prefixed PO Numbers

## Objective
Ensure the system accepts and correctly processes Coupa PO identifiers with the `PM` prefix (e.g., `PM15492200`) the same way as `PO` prefixes, by stripping the prefix when building URLs and validating numeric IDs.

## Scope
- Handle `PM` in addition to `PO` when cleaning PO numbers across the core download and CSV code paths.
- Keep behavior unchanged for already supported cases; do not alter unrelated timeouts, flows, or UI.
- Minimal, targeted edits; no architectural changes.

Out of scope:
- Broader refactors or moving logic into new shared helper modules.
- Changes to Excel processing beyond parity (Excel already accepts `PM`).

## Affected Files
- Update: `src/core/downloader.py` (strip `PM` when building Coupa URL)
- Update: `src/core/csv_processor.py` (accept `PM` in cleaning/validation and invalid URL build)
- Update: `src/utils/parallel_test/downloader.py` (mirror `PM` handling)
- Tests: `src/utils/GeminiTests/test_downloader_simplification.py` (add PM case)
- Tests: Add `src/utils/GeminiTests/test_csv_processor_pm_prefix.py` (CSVProcessor PM acceptance)

## Pseudodiff (representative)
```diff
--- src/core/downloader.py
+++ src/core/downloader.py
@@ def download_attachments_for_po(self, po_number: str) -> dict:
-        # Remove "PO" prefix if present to get the correct order number
-        order_number = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
+        # Remove "PO" or "PM" prefix (case-insensitive) to get the correct order number
+        up = (po_number or "").upper()
+        order_number = po_number[2:] if up.startswith(("PO", "PM")) else po_number
         url = f"{Config.BASE_URL}/order_headers/{order_number}"

--- src/core/csv_processor.py
+++ src/core/csv_processor.py
@@ class CSVProcessor:
     def process_po_numbers(po_entries: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
@@
-            # Clean PO number (remove PO prefix if present)
-            display_po = po_number
-            clean_po = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
+            # Clean PO number (remove PO or PM prefix if present; case-insensitive)
+            display_po = po_number
+            up = (po_number or '').upper()
+            clean_po = po_number[2:] if up.startswith(("PO", "PM")) else po_number
@@
-                clean_po_attempt = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
+                up = (po_number or '').upper()
+                clean_po_attempt = po_number[2:] if up.startswith(("PO", "PM")) else po_number
                 invalid_url = Config.BASE_URL.format(clean_po_attempt)

--- src/utils/parallel_test/downloader.py
+++ src/utils/parallel_test/downloader.py
@@ def download_attachments_for_po(self, po_number: str, tab_id: str = "MAIN", hierarchical_folder: str = None) -> Tuple[bool, str]:
-            # Remove "PO" prefix if present to get the correct order number
-            order_number = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
+            # Remove "PO" or "PM" prefix (case-insensitive) to get the correct order number
+            up = (po_number or '').upper()
+            order_number = po_number[2:] if up.startswith(("PO", "PM")) else po_number
             url = f"{Config.BASE_URL}/order_headers/{order_number}"

--- src/utils/GeminiTests/test_downloader_simplification.py
+++ src/utils/GeminiTests/test_downloader_simplification.py
@@
 def test_download_workflow_success(downloader, mock_browser_manager):
@@
     mock_driver.get.assert_called_once_with(f"{Config.BASE_URL}/order_headers/12345")

+def test_download_workflow_success_pm_prefix(downloader, mock_browser_manager):
+    """Downloader should accept PM-prefixed input by stripping the prefix."""
+    mock_manager, mock_driver = mock_browser_manager
+    po_number = "PM98765"
+    # Minimal attachment stubs
+    mock_attachment = MagicMock()
+    mock_attachment.text = "file.pdf"
+    mock_attachment.get_attribute.return_value = "file.pdf"
+    mock_driver.find_elements.return_value = [mock_attachment]
+
+    success, message = downloader.download_attachments_for_po(po_number)
+
+    assert success is True
+    mock_driver.get.assert_called_once_with(f"{Config.BASE_URL}/order_headers/98765")

--- src/utils/GeminiTests/test_csv_processor_pm_prefix.py (new)
+++ src/utils/GeminiTests/test_csv_processor_pm_prefix.py
+import os, sys
+project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
+sys.path.insert(0, project_root)
+from src.core.csv_processor import CSVProcessor
+
+def test_csv_processor_accepts_pm_prefix():
+    entries = [
+        {'po_number': 'PM15492200', 'status': 'PENDING'},
+        {'po_number': 'PO123456', 'status': 'PENDING'},
+    ]
+    result = CSVProcessor.process_po_numbers(entries)
+    assert ('PM15492200', '15492200') in result
+    assert ('PO123456', '123456') in result
```

## Acceptance Criteria
- Given `PM15492200`, downloader navigates to `…/order_headers/15492200` and proceeds normally.
- `CSVProcessor.process_po_numbers` returns a valid tuple for `PM...` values just like `PO...`.
- Parallel test downloader mirrors the same behavior for consistency.
- Existing behavior for `PO...` inputs remains unchanged; no regressions.

## Minimal Manual Tests
1) Enter a PM-prefixed PO (e.g., `PM15492200`) in the input and run a small batch. Verify the URL printed uses `…/order_headers/15492200` and early error detection/attachment discovery still work.
2) Enter an invalid PM (e.g., `PMABC123`) and verify it is rejected as invalid with correct status update.
3) Smoke a PO-prefixed input to confirm no regression.

## Suggested Commit Message and Branch
- Plan branch: `plan/27-pm-prefix-support`
- Impl branch: `fix/27-pm-prefix-support`
- Plan commit: `docs(pr-plan): PR 27 — support PM-prefixed PO numbers`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff (small, readable, representative) provided.
- [x] Acceptance criteria and minimal manual tests.
- [x] Suggested commit message and branch name.
