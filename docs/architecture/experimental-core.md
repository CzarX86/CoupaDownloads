# Experimental Core: Objective & Architecture

This document summarizes the intent and design of the experimental pipeline under `experimental/core`.

## Objective

- End-to-end automation to download Coupa PO attachments based on a CSV/Excel input.
- Build a vendor/PO-based folder hierarchy, route browser downloads there, and rename folders with a status suffix.
- Update the spreadsheet with results (status, counts, folder, URLs, attachment names).
- Offer two execution modes:
  - Sequential in-process with a single persistent WebDriver (safer, simpler).
  - Multiprocessing with one WebDriver per process (faster, isolates failures).
- Provide an interactive setup wizard and optional interactive CLI UI showing progress, logs, metadata, and the ability to stop.

## High-level Architecture

- Orchestrator (Main)
  - `MainApp` in `main.py` coordinates configuration, input loading, processing pipeline, UI events, status updates, and cleanup.
  - `main()` creates and runs `MainApp`.

- Services (consumed from `src/core`)
  - `BrowserManager`: lifecycle and health of Selenium Edge driver, headless/profile config, download directory switching.
  - `Downloader`: navigates to Coupa and downloads attachments for a given PO number; returns a rich result payload.
  - `ExcelProcessor`: locates/reads Excel/CSV, validates PO entries, and writes back status/results.
  - `FolderHierarchyManager`: computes/creates target folder path for each PO and formats attachment names.
  - `Config`: global runtime configuration (paths, flags, limits).
  - `DriverManager`: finds or downloads a matching EdgeDriver (used by the setup wizard).

- UI layer (optional, event-driven)
  - `DownloadCLIController` and `PODescriptor` from `src/core/ui`.
  - `MainApp` emits UI events: `po_started`, `log`, `update_metadata`, and `po_completed`.
  - A stop signal (from UI) is respected mid-pipeline.

- Concurrency models
  - Sequential mode (default): single WebDriver, guarded with a lock for all Selenium operations; robust recovery if the session/window dies.
  - Process pool mode: `ProcessPoolExecutor` using "spawn"; each worker runs `process_po_worker` with its own WebDriver and isolated download directory. Edge profile is explicitly disabled in workers to avoid profile locks.

## Processing Flow

1. Interactive setup (wizard)
   - Prompts for input file path, headless mode, execution model (process pool or not), worker count (capped), EdgeDriver resolution (auto/manual), base download folder, and Edge profile usage. Optionally kills running Edge processes.
   - Sets environment variables and adjusts `Config` accordingly.

2. Input ingestion
   - `ExcelProcessor.get_excel_file_path()` resolves the input.
   - Read and validate POs; optional random sampling via `Config.RANDOM_SAMPLE_POS`.

3. For each PO
   - Create hierarchical folder via `FolderHierarchyManager`.
   - Ensure Selenium driver is ready:
     - Sequential: reuse driver; if unresponsive, reinitialize; lock around all driver usage.
     - Process pool: a fresh driver per worker; set the process's download folder.
   - `Downloader.download_attachments_for_po` performs the retrieval.
   - Wait until download temp files settle (.crdownload/.tmp/.partial) with a short "quiet" period.
   - Compute a unified status code and message from the result payload.
   - Rename folder to include `_COMPLETED`, `_NO_ATTACHMENTS`, `_PARTIAL`, `_FAILED`, or `_PO_NOT_FOUND`.
   - Update the spreadsheet with supplier, counts, folder path, URL, attachment names, and a composed message (with PR-fallback context when applicable).
   - Send UI updates throughout.

4. Error handling and recovery
   - Human-friendly exception messages for common Selenium failures.
   - Sequential mode tries driver/tab cleanup and driver reinit after failures; still records a FAILED status.
   - Process pool isolates crashes; each worker tries to suffix the folder on unexpected exceptions.

5. Summary
   - Prints total success/failed counts; shuts down driver(s).

## Important Helpers & Contracts

- Status derivation: from payload fields and message patterns → `COMPLETED`, `NO_ATTACHMENTS`, `PARTIAL`, `FAILED`, `PO_NOT_FOUND`.
- Folder suffixing: renames base folder with `_STATUS`, handling collisions (`-2`, `-3`, …).
- Worker process contract:
  - Input: `(po_data: dict, hierarchy_cols: list[str], has_hierarchy_data: bool)`
  - Output: dict with keys including `po_number_display`, `status_code`, `message`, `final_folder`, `supplier_name`, `attachments_found`, `attachments_downloaded`, `coupa_url`, `attachment_names`, `status_reason`, `errors`, `success`, `fallback_*`, `source_page`, `initial_url`.
- Progress telemetry (sequential mode): tracks elapsed, average PO time, remaining estimate, and ETA.

## Notable Design Choices

- No tab-per-PO; sequential mode uses a single window for stability.
- Process pool deliberately avoids Edge profile usage to prevent profile lock contention.
- Download completion waits for a "quiet" period, not just file disappearance.
- UI integration is non-blocking; if the interactive UI can't run, it gracefully falls back to the non-UI pipeline.

## Folder Contents

- `main.py`: full orchestrator, interactive setup, worker, and processing pipeline.
- `__init__.py`: empty marker.
