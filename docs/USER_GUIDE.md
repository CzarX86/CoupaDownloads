# CoupaDownloads — User Guide

Single entry point for installation, configuration, daily usage, outputs, and troubleshooting.

## Overview
- Automates discovery and download of attachments for Purchase Orders (POs) from Coupa using Microsoft Edge and Selenium.
- Works with CSV or Excel input, updates rows with status and metadata, and organizes downloads into a structured folder hierarchy.
- Supports Windows and macOS; offline Windows bundle available for constrained networks.

## Requirements
- Python 3.12+
- Microsoft Edge installed and launchable
- Permissions to create folders and write files under the project’s `data/` and download directories

## Installation

### Option A — Windows Offline Bundle
For fully offline installation and driver bundling, follow:
- docs/howto/README_Offline.md

### Option B — From Source (Poetry)
1) Install Poetry and Python 3.12+
2) In the repository root:
   - poetry install
3) (Optional) Activate the virtualenv created by Poetry:
   - poetry shell

You can also run commands without activating the shell by prefixing with `poetry run`.

## Running the Application

### Quick Start
- With Poetry:
  - poetry run python -m src.Core_main
- With a plain virtualenv:
  - python -m src.Core_main

Notes:
- Some distributions may expose a CLI alias (e.g., `coupa-downloader`), but the canonical entry is `python -m src.Core_main`.
- On first run, an interactive wizard asks for essential settings (see next section).

## Configuration (Interactive Wizard)
The wizard guides runtime choices and sets environment variables for the current process:

- Input file path
  - Default: auto-detected by the app (`data/input/input.csv` if present, otherwise `data/input/input.xlsx`).
  - Env override: `EXCEL_FILE_PATH` (or `INPUT_CSV`/`INPUT_XLSX`).

- Execution model
  - In‑process (sequential, single WebDriver) — simpler, lower resource usage.
  - Process pool (one WebDriver per process) — parallelism with safe cap.
  - Env: `USE_PROCESS_POOL` (`true|false`), `PROC_WORKERS` (suggest 1–3), `PROC_WORKERS_CAP` (hard cap, default 3).

- Headless mode
  - Default: enabled.
  - Env: `HEADLESS=true|false`.

- EdgeDriver selection
  - Auto‑detects local driver and may auto‑download if allowed.
  - On failure, you can provide a manual path.
  - Env: `DRIVER_AUTO_DOWNLOAD=true|false`, `EDGE_DRIVER_PATH`.

- Download folder base
  - Choose where files are saved; the app creates per‑PO subfolders.

- Edge profile usage (cookies/login)
  - Default: enabled; you may set profile directory/name.
  - If the profile is busy, the app falls back to a clean session.

- Pre‑start cleanup
  - Optionally close any running Edge processes before launching.
  - Helpful if profiles are locked by another Edge instance.

## Input Formats

### CSV
- Auto‑detects delimiter (comma/semicolon) and handles UTF‑8 with BOM.
- Required column: `PO_NUMBER`.
- Optional columns that the app reads/updates when present:
  - `STATUS`, `SUPPLIER`, `ATTACHMENTS_FOUND`, `ATTACHMENTS_DOWNLOADED`, `AttachmentName`, `LAST_PROCESSED`, `ERROR_MESSAGE`, `DOWNLOAD_FOLDER`, `COUPA_URL`
- CSV writes preserve detected delimiter, use UTF‑8 BOM (`utf-8-sig`), `lineterminator="\n"`, and `csv.QUOTE_MINIMAL`.

### Excel
- Only the `PO_Data` sheet is read/updated; other sheets are not touched.
- The same columns as above apply.

## What Happens When You Run
1) The app scans your input sheet and validates PO numbers.
2) It creates a folder for each PO (using hierarchy columns when available, otherwise fallback Supplier/PO).
3) It launches Microsoft Edge (headless by default) and navigates to Coupa to fetch attachments.
4) It waits for downloads to complete and renames the PO folder with a status suffix.
5) It updates the CSV/Excel row with status, counts, attachment names, error message (if any), download folder, and PO URL.

## Outputs

- Folder structure
  - Default fallback: `Supplier/PO...` (or a deeper hierarchy if your sheet provides hierarchy columns).

- Status suffix on folders
  - `_COMPLETED` — all expected attachments downloaded
  - `_PARTIAL` — some attachments downloaded
  - `_NO_ATTACHMENTS` — no attachments were available
  - `_FAILED` — an error occurred during processing

- Spreadsheet updates
  - Columns updated: `STATUS`, `SUPPLIER`, `ATTACHMENTS_FOUND`, `ATTACHMENTS_DOWNLOADED`, `AttachmentName`, `LAST_PROCESSED`, `ERROR_MESSAGE`, `DOWNLOAD_FOLDER`, `COUPA_URL`.
  - CSV column order is normalized to keep these fields together; encoding is UTF‑8 with BOM.

## Troubleshooting

- Python not found
  - Install Python 3.12+ and ensure it is on your PATH.

- Edge or driver issues
  - If auto‑selection fails, download a matching EdgeDriver for your Edge version.
  - Provide its path via the wizard or `EDGE_DRIVER_PATH`.
  - If you see "user data directory is already in use", close all Edge windows or disable profile usage for this run.

- Network constraints / corporate environments
  - See: platform/NETWORK_ISSUE_SOLUTION.md

- Fully offline usage
  - See: howto/README_Offline.md

## Advanced Workflows

- Human‑in‑the‑Loop (HITL) feedback loop
  - docs/HITL_FEEDBACK_WORKFLOW.md

- Model management and A/B review
  - docs/MODEL_MANAGEMENT.md

## Appendix — Components & Data Flow

- Orchestration
  - `src/Core_main.py` — interactive setup, PO dispatch (sequential or via a process pool), final reporting.

- Browser & Driver
  - `src/core/browser.py` — WebDriver lifecycle, options (headless/profile), download directory management, cleanup.
  - `src/core/driver_manager.py` — detects local EdgeDriver, version checks, verification.

- Downloading
  - `src/core/downloader.py` — navigates Coupa and triggers attachment downloads for each PO.

- Input/Output Processing
  - `src/core/excel_processor.py` — reads CSV/Excel, validates POs, updates rows with status/metadata, writes CSV (with BOM and stable column order) or Excel (`PO_Data`).
  - `src/core/csv_processor.py` — CSV helpers (when used standalone).
  - `src/core/folder_hierarchy.py` — maps row data to hierarchical folder paths; formats attachment names field.

- Configuration & Utilities
  - `src/core/config.py` — central settings and defaults (honors env vars set by the wizard).
  - `src/core/progress_manager.py`, `src/core/download_control.py`, `src/core/update_manager.py` — auxiliary coordination and progress utilities.

- Visual reference
  - High‑level process diagram: reports/E2E_FLOW_DIAGRAM.md

## Success Indicators
- Edge WebDriver launches without profile or version errors.
- Output folders contain the expected files and status suffix.
- The spreadsheet shows updated `STATUS`, counts, and `LAST_PROCESSED` timestamps.

