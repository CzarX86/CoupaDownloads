# Implementation Plan - Advanced Performance Optimizations

This plan outlines the implementation of advanced execution modes in CoupaDownloads to improve efficiency and speed, as requested by the user.

## 1. New Models & Configuration

- **Objective**: Define a unified way to track execution modes.
- **Changes**:
  - Add `ExecutionMode` Enum to `src/lib/models.py`.
  - Modes: `STANDARD`, `FILTERED` (No assets), `NO_JS` (No Javascript), `DIRECT_HTTP` (No browser).
  - Update `InteractiveSetupSession` and `HeadlessConfiguration` to carry these settings.

## 2. Interactive Setup Enhancements

- **Objective**: Allow the user to select the execution path during startup.
- **Changes**:
  - Modify `src/setup_manager.py` to add a new menu after worker count selection.
  - Provide clear descriptions for each mode:
    1. **Standard**: Existing browser flow (Selenium/Edge).
    2. **Optimized (Filtered)**: Browser without images, fonts, analytics, and CSS. (Will use Playwright for better interception).
    3. **Fast (No JS)**: Browser with Javascript and CSS disabled.
    4. **Turbo (Direct HTTP)**: Machine-level requests using `httpx`. No browser overhead after initial login.

## 3. SQLite WAL Optimization

- **Objective**: Confirm and ensure SQLite is running at peak performance.
- **Changes**:
  - The current `SQLiteHandler` already uses `PRAGMA journal_mode=WAL`.
  - I will add `PRAGMA synchronous=NORMAL` and verify the timeout is optimal for high concurrency.
  - Add a log confirmation on startup that WAL is active.

## 4. Playwright Integration for Filtered Mode

- **Objective**: Implement resource blocking which is more robust in Playwright than Selenium.
- **Changes**:
  - Create `src/lib/playwright_manager.py` to handle Playwright lifecycle.
  - Implement resource interception to block `image`, `font`, `stylesheet`, and known analytics domains.
  - Create `src/lib/playwright_downloader.py` or adapt existing logic.

## 5. Direct HTTP Extraction (Turbo Mode)

- **Objective**: Implement the most efficient extraction path.
- **Changes**:
  - Create `src/lib/direct_http_downloader.py`.
  - **Login Integration**: Use a one-time browser session (or existing profile) to extract `session` and `remember_token` cookies.
  - **Worker Logic**: Instead of launching a browser per worker, workers will receive the cookies and use `httpx.AsyncClient` for high-concurrency downloads.
  - **Parsing**: Use `BeautifulSoup` with `lxml` (already in dependencies) for extremely fast HTML parsing.

## 6. Workforce Orchestration

- **Objective**: Update the `WorkerManager` to spawn the correct type of worker based on the mode.
- **Changes**:
  - Update `process_po_worker` in `worker_manager.py` to branch into different downloader implementations.
  - Ensure progress reporting remains consistent across all modes.

## 7. Performance Monitoring

- **Objective**: Show the impact of different modes in the UI.
- **Changes**:
  - Update `UIController` to display the active "Execution Mode".
  - Track and show more granular performance stats if applicable.

---

## Workflow Steps

### Step 1: Initialize New Models

- Edit `src/lib/models.py`.

### Step 2: Update Setup Manager

- Edit `src/setup_manager.py` to add the new menu.

### Step 3: Implement Direct HTTP Downloader

- Create `src/lib/direct_http_downloader.py`.

### Step 4: Implement Playwright Resource Blocking

- Create `src/lib/playwright_manager.py` and integration in `BrowserManager`.

### Step 5: Orchestration Update

- Update `src/worker_manager.py` and `src/main.py`.

### Step 6: Verification

- Test each mode with a single PO to ensure functionality.
