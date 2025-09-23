# PR Plan 34 — PDF Annotation Workflow for Contract Review

## Objective
Design and integrate an interactive PDF annotation workflow that replaces most of the manual edits in `reports/feedback/review.csv`, enabling reviewers to validate contract fields directly against the rendered document while keeping the existing training pipeline intact.

**Resumo em pt-BR:** Vamos criar um fluxo onde a revisão acontece olhando diretamente o PDF (com os campos pré-preenchidos) em vez de editar células no CSV. A ferramenta gera tarefas, abre uma interface de anotação e depois traz as correções de volta para o processo de treino.

## Scope
- Provide a CLI-assisted loop that converts a review CSV into PDF annotation tasks, launches a local UI, and re-ingests the curated results.
- Scaffold a Label Studio project template (config + tasks) with pre-filled predictions for each contract field we currently audit.
- Add command helpers and documentation so reviewers can start/stop the annotation session and export the reviewed data back to CSV without manual file shuffling.

Out of scope:
- Changing the downstream training/evaluation logic beyond accepting the re-ingested CSV.
- Implementing OCR or page-level auto-highlighting beyond the textual metadata already extracted.
- Hosting a shared Label Studio server; this plan only covers local (developer workstation) usage.

## Affected Files
- `tools/feedback_cli.py` — register PDF annotation commands that orchestrate export/import.
- `tools/pdf_annotation.py` — new helper module for Label Studio project scaffolding and round-trip conversions.
- `docs/USER_GUIDE.md` — add instructions for running the PDF annotation workflow.
- `docs/feedback/pdf_annotation.md` — new guide explaining setup, screenshots, and troubleshooting.
- `docs/diagrams/pdf_annotation.mmd` — Mermaid source kept with documentation assets.
- `requirements.txt` / `pyproject.toml` — add optional dependency group (`label-studio-sdk` + `PyMuPDF`) guarded behind extras.

## Approach
1. **Task preparation layer** — Parse `review.csv`, keep metadata, and emit a Label Studio task JSON where each field becomes a pre-populated textarea in the UI. Render lightweight page previews via PyMuPDF to include page numbers and thumbnail references.
2. **Project bootstrap command** — Add `python tools/feedback_cli.py annotate-pdf prepare --review-csv ...` that writes tasks/config to `reports/feedback/pdf_annotation/` and prints Docker instructions (or reuses existing local install) before launching Label Studio.
3. **Ingestion command** — Add `annotate-pdf ingest --label-studio-export ...` to merge reviewer changes back into the CSV, preserving `_gold`/`_status` triplets and noting annotator metadata.
4. **Documentation & UX** — Document the full loop (prepare → open UI → review → export → ingest), provide a Mermaid overview, and add a plain-language explanation for non-engineers.
5. **Quality guardrails** — Validate that the ingest step checks for missing required fields, warns about conflicts, and writes the updated CSV with our standard Excel hint. Include smoke tests or CLI dry-runs in the manual checklist.

```mermaid
digraph PDFReview {
  rankdir=LR
  ReviewCSV["CSV de revisão existente"] -> PrepareCmd["`annotate-pdf prepare`"] -> LSProject["Projeto Label Studio local"]
  LSProject -> Reviewer["Revisor anota PDFs"] -> ExportJSON["Exportação Label Studio"]
  ExportJSON -> IngestCmd["`annotate-pdf ingest`"] -> UpdatedCSV["CSV atualizado para treino"]
}
```

### Plain-language explainer
We will add buttons in the command-line tools that turn the spreadsheet into a set of PDF review tasks. You run one command to generate the tasks and open a point-and-click interface (Label Studio) where each document is shown next to the fields we care about. After fixing the answers, you export the results, run another command, and the CSV is updated automatically. This means reviewers stop editing spreadsheets by hand and instead work directly with the PDFs.

## Pseudodiff (representative)
```diff
+++ tools/pdf_annotation.py
+"""Utilities to bridge review.csv and Label Studio PDF projects."""
+def build_tasks(review_csv: Path, out_dir: Path) -> dict:
+    # parse CSV, render previews, write tasks.json and config.json
+
--- tools/feedback_cli.py
+++ tools/feedback_cli.py
@@
+    p_ann = sub.add_parser("annotate-pdf", help="PDF-centric review workflow")
+    ann_sub = p_ann.add_subparsers(dest="action", required=True)
+
+    p_ann_prep = ann_sub.add_parser("prepare", help="Generate Label Studio project files")
+    p_ann_prep.add_argument("--review-csv", required=True)
+    p_ann_prep.add_argument("--out-dir", default="reports/feedback/pdf_annotation")
+    p_ann_prep.set_defaults(func=cmd_annotate_pdf_prepare)
+
+    p_ann_ing = ann_sub.add_parser("ingest", help="Merge Label Studio export back into review CSV")
+    p_ann_ing.add_argument("--export-json", required=True)
+    p_ann_ing.add_argument("--review-csv", required=True)
+    p_ann_ing.set_defaults(func=cmd_annotate_pdf_ingest)
+
+++ docs/feedback/pdf_annotation.md
+# PDF annotation workflow
+- Step-by-step guide
+- Screenshots, troubleshooting, explain-like-I'm-new section
+
--- docs/USER_GUIDE.md
+++ docs/USER_GUIDE.md
@@
-### Feedback workflows
+### Feedback workflows
+- PDF annotation loop (`python tools/feedback_cli.py annotate-pdf ...`)
```

## Acceptance Criteria
- `annotate-pdf prepare` produces a self-contained folder with `tasks.json`, `config.xml`, thumbnails, and a README snippet describing how to launch Label Studio locally.
- Reviewers can open the generated project in Label Studio, see PDFs rendered alongside pre-filled field values, and edit them without editing the CSV directly.
- `annotate-pdf ingest` consumes a Label Studio export (JSON), reconciles edits into the original CSV, and preserves existing metadata (`_pred`, `_gold`, `_status`, `annotator`, `timestamp`).
- Documentation includes a Mermaid diagram and a beginner-friendly explanation of when/why to use the PDF annotation flow.
- Round-trip dry run (prepare → mock edit → ingest) succeeds without manual CSV editing, and the output CSV still passes our existing ingestion/evaluation commands.

## Manual Tests
- `python tools/feedback_cli.py annotate-pdf prepare --review-csv reports/feedback/review.csv --out-dir /tmp/ls_project`
- Launch Label Studio locally using the generated README instructions; import the project and adjust a couple of fields.
- `python tools/feedback_cli.py annotate-pdf ingest --export-json exported_tasks.json --review-csv reports/feedback/review.csv`
- `python tools/feedback_cli.py ingest --review-csv reports/feedback/review.csv --out-dir datasets/tmp` (ensure ingest still succeeds).

## Suggested commit message and branch
- Branch: `plan/34-pdf-annotation-workflow`
- Commit: `docs(pr-plan): PR 34 — PDF annotation workflow`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff (small, readable, representative of the approach).
- [x] Acceptance criteria and minimal manual tests.
- [x] Suggested commit message and branch name.
