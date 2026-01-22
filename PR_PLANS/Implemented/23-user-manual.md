# PR 23 — User Manual (single-entry guide consolidating setup, usage, and troubleshooting)

## Objective
Create a clear, English user manual that consolidates setup, configuration, daily usage, data flow overview, output fields, and troubleshooting into a single, discoverable document. It should reference existing docs (HITL, Model Management, Offline, Network Issues) and be safe to ship without changing runtime behavior.

## Scope
- Add a single, primary manual at `docs/USER_GUIDE.md` (English, user‑facing).
- Keep implementation strictly additive: no code changes, no behavior changes.
- Cross‑link to existing content:
  - `docs/HITL_FEEDBACK_WORKFLOW.md`
  - `docs/MODEL_MANAGEMENT.md`
  - `docs/howto/README_Offline.md`
  - `docs/platform/NETWORK_ISSUE_SOLUTION.md`
  - `docs/reports/E2E_FLOW_DIAGRAM.md`
- Minimal README change: add a “User Guide” link near Quick Start.
- Optional: small TOC section in `docs/` README if present (additive only). No reorg of folders in this PR.

Out of scope:
- Any code refactor or defaults change.
- UI string rewrites, except if we directly quote current messages for clarity.
- Deep architecture docs beyond a compact “Components & Data Flow” appendix.

## Affected files
- Add: `docs/USER_GUIDE.md`
- Update: `README.md` (insert link to the user guide)

## Pseudodiff
```
+++ docs/USER_GUIDE.md
# CoupaDownloads — User Guide

> Single entry point for installation, configuration, usage, outputs, and troubleshooting.

## Overview
- What it does; supported platform; offline bundle note
- Entry points: `python -m src.Core_main` (interactive), `poetry run coupa-downloader` (if available)

## Requirements
- Python 3.12+, Microsoft Edge installed; Windows/macOS
- Permissions (Windows: run CMD as Admin if needed)

## Installation
- Windows offline bundle (link to `docs/howto/README_Offline.md`)
- From source (Poetry): `poetry install`, activate env

## Configuration (Interactive wizard)
- Input file path detection and override (`EXCEL_FILE_PATH`)
- Process model: in‑process vs process pool (`USE_PROCESS_POOL`, `PROC_WORKERS`, caps)
- Headless mode (default Yes)
- Driver auto‑download and manual path (`EDGE_DRIVER_PATH`)
- Download folder base; Edge profile usage; pre‑start cleanup

## Input formats
- CSV: auto‑detect delimiter; UTF‑8 BOM; required/optional columns
- Excel: `PO_Data` sheet only; backup note
- Columns explained: `PO_NUMBER`, `STATUS`, `SUPPLIER`, `ATTACHMENTS_FOUND`, `ATTACHMENTS_DOWNLOADED`, `AttachmentName`, `LAST_PROCESSED`, `ERROR_MESSAGE`, `DOWNLOAD_FOLDER`, `COUPA_URL`

## Running the app
- Quick steps with `venv`/Poetry
- Headless vs visible; process pool limits
- Progress messages (English UI) and success indicators

## Outputs
- Folder structure (Supplier/PO; hierarchy if provided)
- Status suffix on folders: `_COMPLETED`, `_FAILED`, `_NO_ATTACHMENTS`, `_PARTIAL`
- CSV/Excel updates and column ordering rules

## Troubleshooting
- Python not found; Edge issues; driver selection failures
- Network constraints (link to `docs/platform/NETWORK_ISSUE_SOLUTION.md`)
- Offline usage (link to `docs/howto/README_Offline.md`)

## Advanced
- Human‑in‑the‑Loop feedback (link)
- Model management and A/B review (link)

## Appendix — Components & Data Flow
- Entry point: `src/Core_main.py` (interactive wizard, orchestration)
- Core modules: `core/config.py`, `core/browser.py`, `core/driver_manager.py`, `core/downloader.py`, `core/folder_hierarchy.py`, `core/excel_processor.py`, `core/csv_processor.py`, `core/download_control.py`, `core/progress_manager.py`
- Dependency highlights (Selenium, pandas/openpyxl, Rich, etc.) and how they contribute at runtime

---

@@ README.md (near Quick Start)
+ ## 📚 User Guide
+ See the complete manual here: `docs/USER_GUIDE.md`
```

## Acceptance criteria
- A single `docs/USER_GUIDE.md` exists, written in English, covering:
  - Installation paths (offline bundle and from source) and prerequisites
  - Interactive setup wizard options and corresponding environment variables
  - Supported input formats with the required/optional columns and how the app updates them
  - How to run (sequential vs process pool), headless mode defaults, and limits
  - Output folder naming conventions and status suffix meanings
  - Troubleshooting for common issues, with links to existing targeted docs
  - Pointers to advanced workflows (HITL, model management)
  - Compact appendix describing core components and data flow
- No code changes; only additive docs and a README link.
- All internal links resolve locally in the repository.
- Language Policy respected: user‑facing doc in English; no changes to runtime UI strings.

## Manual tests
- Open `docs/USER_GUIDE.md` and validate headings/TOC.
- Click all cross‑links: they open existing docs.
- Follow “Running the app” steps on a clean env using a sample `data/input/input.csv`; confirm:
  - Interactive prompts match the manual
  - Output folders are created with status suffixes
  - CSV/Excel columns update as documented with UTF‑8 BOM for CSV
- Verify README shows a “User Guide” link.

## Suggested branch and commit
- Plan branch: `plan/23-user-manual`
- Impl branch: `docs/23-user-manual`
- Plan commit: `docs(pr-plan): PR 23 — user manual (single-entry guide)`
- Impl commit: `docs(user-manual): PR 23 — add USER_GUIDE and README link`

## Notes
- This PR is purely additive and safe; it consolidates existing knowledge into a single entry point.
- If scope later expands to include screenshots or a small CLI help reference, it will be proposed as a follow‑up plan.
