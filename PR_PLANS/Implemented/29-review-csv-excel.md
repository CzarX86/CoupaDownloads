# PR 29 — Excel-Friendly Review CSV

## Objective
Ensure the CSV produced by `feedback_cli.py prepare` opens column-aligned in Microsoft Excel with a simple double-click while keeping ingestion and downstream tooling unchanged.

## Scope
- Update `make_review_csv` to embed Excel-friendly metadata without altering column content or delimiter semantics.
- Teach the reader utilities (used by ingestion and other commands) to tolerate the new metadata line transparently.
- Refresh user-facing documentation so analysts know the CSV now opens cleanly in Excel with no extra steps.

Out of scope:
- Any change to the CSV schema, field names, or sampling logic.
- Generating XLSX files or altering other report writers.

## Affected Files
- Update: `tools/feedback_utils.py`
- Update: `tools/feedback_cli.py` (only if minor wiring is required)
- Update: `docs/USER_GUIDE.md`

## Pseudodiff (representative)
```diff
--- tools/feedback_utils.py
+++ tools/feedback_utils.py
@@
-import pandas as pd
+import io
+import pandas as pd
@@ def make_review_csv(...):
-    df.to_csv(out_path, index=False, encoding="utf-8-sig", lineterminator="\n")
+    buffer = io.StringIO()
+    df.to_csv(buffer, index=False, lineterminator="\n")
+    out_path.write_text("sep=,\n" + buffer.getvalue(), encoding="utf-8-sig")
     return str(out_path)
@@ def ingest_review_csv(...):
-    df = pd.read_csv(review_csv)
+    first_line = Path(review_csv).read_text(encoding="utf-8-sig").splitlines()[:1]
+    skiprows = 1 if first_line and first_line[0].lower().startswith("sep=") else 0
+    df = pd.read_csv(review_csv, encoding="utf-8-sig", skiprows=skiprows)
```

## Acceptance Criteria
- `feedback_cli.py prepare` generates a CSV whose first line is `sep=,`, followed by the usual header and rows.
- Opening the CSV via Excel double-click honors column boundaries on a Windows locale that defaults to semicolon delimiters.
- `feedback_cli.py ingest` and other readers still parse the CSV without manual intervention or regressions.
- Documentation reflects the Excel-friendly behavior and remains in English for UI strings.

## Manual Tests
- Run `python tools/feedback_cli.py prepare --pred-csv reports/advanced_*.csv --out reports/feedback/review.csv` and confirm the first line is `sep=,`.
- Open the generated file with `pandas.read_csv("reports/feedback/review.csv", encoding="utf-8-sig")` to ensure row counts match the input.
- Execute `python tools/feedback_cli.py ingest --review-csv reports/feedback/review.csv --out-dir /tmp/review-test` to verify ingestion still succeeds.

## Mermaid Diagram
```mermaid
flowchart TD
    A[Pipeline CSV
(reports/advanced_*.csv)] --> B[make_review_csv
(embed sep=,)]
    B --> C[review.csv
UTF-8 BOM + sep line]
    C --> D[Excel Double-Click
columns aligned]
    C --> E[ingest_review_csv
skip sep hint]
```

## Plain-language Summary
We will add a tiny note at the very top of the review CSV telling Excel “this file uses commas.” Excel will then split the data into columns automatically. The code that reads the CSV will just ignore that note so nothing else changes.

## Suggested Commit Message
`docs(pr-plan): PR 29 — Excel-friendly review CSV`

## Suggested Branch Name
`plan/29-review-csv-excel`

## Checklist
- [ ] Objective and Scope are clear and limited.
- [ ] Affected files listed.
- [ ] Pseudodiff (small, readable, representative of the approach).
- [ ] Acceptance criteria and minimal manual tests.
- [ ] Suggested commit message and branch name.
