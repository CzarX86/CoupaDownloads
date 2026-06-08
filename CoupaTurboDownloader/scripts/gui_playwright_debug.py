#!/usr/bin/env python3
"""Playwright probe for CoupaTurbo GUI frontend.

Modes:
- mock: deterministic backend simulation for fast UI diagnostics.
- real: executes real AppAPI methods (import/history/details/export/retry) through a
  Python-JS bridge, while simulating telemetry-only methods required by the UI.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db.session_db import SessionDB
from src.gui.api import AppAPI


INIT_BRIDGE_SCRIPT = r"""
(() => {
  const call = async (method, ...args) => {
    if (!window.__pw_api_call) {
      throw new Error('Bridge function __pw_api_call not available');
    }
    return window.__pw_api_call(method, args);
  };

  window.pywebview = {
    api: {
      select_directory: async () => call('select_directory'),
      import_file: async (filepath) => call('import_file', filepath),
      start_download: async (sessionId, downloadDir) => call('start_download', sessionId, downloadDir),
      get_active_session_status: async (sessionId) => call('get_active_session_status', sessionId),
    pause_download: async (sessionId) => call('pause_download', sessionId),
    resume_download: async (sessionId) => call('resume_download', sessionId),
    stop_download: async (sessionId) => call('stop_download', sessionId),
      get_session_history: async () => call('get_session_history'),
      get_session_details: async (sessionId) => call('get_session_details', sessionId),
      confirm_and_retry_company: async (sessionId, companyCode) => call('confirm_and_retry_company', sessionId, companyCode),
      export_session_report: async (sessionId, destPath) => call('export_session_report', sessionId, destPath),
    }
  };
})();
"""


@dataclass
class ProbeResult:
    run_dir: Path
    report_path: Path
    report: dict[str, Any]


@dataclass
class MockBridge:
    download_dir: str
    _tick: int = 0
    _stopped: bool = False
    _paused: bool = False

    def call(self, method: str, args: list[Any]) -> Any:
        if method == "select_directory":
            return self.download_dir
        if method == "import_file":
            filepath = str(args[0]) if args else ""
            if not filepath:
                return {"success": False, "error": "Empty filepath"}
            return {"success": True, "session_id": 777, "total_pos": 15}
        if method == "start_download":
            self._stopped = False
            self._paused = False
            return {"success": True}
        if method == "get_active_session_status":
            if self._stopped:
                return {
                    "status": "STOPPED",
                    "total": 15,
                    "processed": min(self._tick * 2, 15),
                    "speed": 0.0,
                    "eta": "--:--",
                    "errors": 0,
                    "latest_logs": [{"type": "System", "message": "Session stopped"}],
                }
            if self._paused:
                return {
                    "status": "PAUSED",
                    "total": 15,
                    "processed": min(self._tick * 2, 15),
                    "speed": 0.0,
                    "eta": "--:--",
                    "errors": 0,
                    "latest_logs": [{"type": "System", "message": "Session paused"}],
                }
            self._tick += 1
            processed = min(self._tick * 2, 15)
            status = "SUCCESS" if processed >= 15 else "RUNNING"
            return {
                "status": status,
                "total": 15,
                "processed": processed,
                "speed": 42.5,
                "eta": "00:00" if status == "SUCCESS" else "00:12",
                "errors": 1 if processed >= 10 else 0,
                "latest_logs": [
                    {
                        "type": "Success" if status == "SUCCESS" else "Info",
                        "message": "Mock session completed" if status == "SUCCESS" else f"Processed {processed}/15",
                    }
                ],
            }
        if method == "get_session_history":
            return [
                {
                    "id": 777,
                    "input_file": "sample_for_gui_probe.csv",
                    "created_at": datetime.now().isoformat(),
                    "status": "SUCCESS",
                }
            ]
        if method == "get_session_details":
            return {
                "session": {
                    "id": 777,
                    "input_file": "sample_for_gui_probe.csv",
                    "status": "SUCCESS",
                },
                "pos": [
                    {
                        "po_number": "PO-001",
                        "company_code": "ACME-BR",
                        "status": "SUCCESS",
                        "error_message": None,
                    },
                    {
                        "po_number": "PO-002",
                        "company_code": "ACME-BR",
                        "status": "SKIPPED_VERIFICATION_REQUIRED",
                        "error_message": "Verification required",
                    },
                    {
                        "po_number": "PO-003",
                        "company_code": "ACME-US",
                        "status": "SUCCESS",
                        "error_message": None,
                    },
                ],
            }
        if method == "confirm_and_retry_company":
            return {"success": True}
        if method == "export_session_report":
            return {"success": True}
        if method == "pause_download":
            self._paused = True
            return {"success": True}
        if method == "resume_download":
            self._paused = False
            return {"success": True}
        if method == "stop_download":
            self._stopped = True
            return {"success": True}
        raise ValueError(f"Unsupported method in mock bridge: {method}")


@dataclass
class RealBridge:
    run_dir: Path
    db: SessionDB = field(init=False)
    api: AppAPI = field(init=False)
    _start_times: dict[int, float] = field(default_factory=dict)
    _latest_processed: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        db_path = self.run_dir / "probe.db"
        self.db = SessionDB(str(db_path))
        downloads = self.run_dir / "downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        self.api = AppAPI(self.db, str(downloads))

    def _session_total(self, session_id: int) -> int:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM po_downloads WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        return int(row["total"] if row else 0)

    def _update_processed_rows(self, session_id: int, processed_target: int) -> int:
        current = self._latest_processed.get(session_id, 0)
        if processed_target <= current:
            return current

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT po_number FROM po_downloads
            WHERE session_id = ? AND status = 'PENDING'
            ORDER BY id ASC
            LIMIT ?
            """,
            (session_id, processed_target - current),
        )
        rows = [r["po_number"] for r in cursor.fetchall()]
        for po_number in rows:
            self.db.update_po_status(session_id, po_number, "SUCCESS")

        updated = current + len(rows)
        self._latest_processed[session_id] = updated
        return updated

    def call(self, method: str, args: list[Any]) -> Any:
        if method == "select_directory":
            return self.api.default_download_dir

        if method == "import_file":
            filepath = str(args[0]) if args else ""
            file_candidate = Path(filepath)
            if not file_candidate.exists() and file_candidate.name:
                fallback = self.run_dir / file_candidate.name
                if fallback.exists():
                    filepath = str(fallback)
            result = self.api.import_file(filepath)
            if result.get("success"):
                session_id = int(result["session_id"])
                self._latest_processed[session_id] = 0
            return result

        if method == "start_download":
            session_id = int(args[0])
            self._start_times[session_id] = time.time()
            return {"success": True}

        if method == "get_active_session_status":
            session_id = int(args[0])
            total = self._session_total(session_id)
            start_t = self._start_times.get(session_id, time.time())
            elapsed = max(time.time() - start_t, 0.1)
            target_processed = min(total, int(elapsed * 4))
            processed = self._update_processed_rows(session_id, target_processed)
            status = "SUCCESS" if processed >= total and total > 0 else "RUNNING"
            speed = (processed / elapsed) * 60.0 if elapsed > 0 else 0.0
            remaining = max(total - processed, 0)
            eta_seconds = int((remaining / 4.0)) if status != "SUCCESS" else 0
            eta = time.strftime("%M:%S", time.gmtime(eta_seconds))
            latest_logs = [
                {
                    "type": "Success" if status == "SUCCESS" else "Info",
                    "message": "Session finished" if status == "SUCCESS" else f"Processed {processed}/{total}",
                }
            ]
            return {
                "status": status,
                "total": total,
                "processed": processed,
                "speed": speed,
                "eta": eta,
                "errors": 0,
                "latest_logs": latest_logs,
            }

        if method == "get_session_history":
            return self.api.get_session_history()

        if method == "pause_download":
            session_id = int(args[0])
            return self.api.pause_download(session_id)

        if method == "resume_download":
            session_id = int(args[0])
            return self.api.resume_download(session_id)

        if method == "stop_download":
            session_id = int(args[0])
            return self.api.stop_download(session_id)

        if method == "get_session_details":
            session_id = int(args[0])
            return self.api.get_session_details(session_id)

        if method == "confirm_and_retry_company":
            session_id = int(args[0])
            company_code = str(args[1])
            return self.api.confirm_and_retry_company(session_id, company_code)

        if method == "export_session_report":
            session_id = int(args[0])
            dest_name = os.path.basename(str(args[1]))
            dest_path = self.run_dir / dest_name
            return self.api.export_session_report(session_id, str(dest_path))

        raise ValueError(f"Unsupported method in real bridge: {method}")

    def close(self) -> None:
        self.db.close()


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(web_root: Path) -> tuple[ThreadingHTTPServer, threading.Thread]:
    port = pick_free_port()
    handler = partial(SimpleHTTPRequestHandler, directory=str(web_root))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def create_sample_csv(path: Path) -> Path:
    path.write_text(
        "PO_NUMBER;Legal Entity\n"
        "PO-001;ACME-BR\n"
        "PO-002;ACME-BR\n"
        "PO-003;ACME-US\n",
        encoding="utf-8",
    )
    return path


def run_probe(
    mode: str = "mock",
    headed: bool = False,
    timeout_ms: int = 20000,
    output_root: Path | None = None,
) -> ProbeResult:
    if mode not in {"mock", "real"}:
        raise ValueError("mode must be 'mock' or 'real'")

    repo_root = Path(__file__).resolve().parents[1]
    web_root = repo_root / "src" / "gui" / "web"
    if not web_root.exists():
        raise FileNotFoundError(f"web root not found: {web_root}")

    evidence_root = output_root or (repo_root / "artifacts" / "gui-playwright")
    run_dir = evidence_root / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    sample_csv = create_sample_csv(run_dir / "sample_for_gui_probe.csv")

    server, _thread = start_server(web_root)
    base_url = f"http://127.0.0.1:{server.server_port}/index.html"

    console_logs: list[dict[str, Any]] = []
    page_errors: list[str] = []
    steps: list[str] = []

    bridge: MockBridge | RealBridge
    if mode == "mock":
        bridge = MockBridge(download_dir=str(run_dir / "downloads"))
    else:
        bridge = RealBridge(run_dir=run_dir)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not headed)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(timeout_ms)

            page.on(
                "console",
                lambda msg: console_logs.append({"type": msg.type, "text": msg.text, "location": msg.location}),
            )
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.on("dialog", lambda dialog: dialog.accept())

            page.expose_function("__pw_api_call", lambda method, args: bridge.call(method, args))
            page.add_init_script(INIT_BRIDGE_SCRIPT)

            page.goto(base_url, wait_until="domcontentloaded")
            steps.append("loaded-index")
            page.screenshot(path=str(run_dir / "01_loaded.png"), full_page=True)

            page.locator("#file-input").set_input_files(str(sample_csv))
            steps.append("selected-input-file")
            page.screenshot(path=str(run_dir / "02_file_selected.png"), full_page=True)

            page.click("#btn-start-run")
            steps.append("clicked-start")

            page.wait_for_selector("#screen-progress.active")
            page.wait_for_timeout(2500)
            steps.append("progress-visible")
            pause_button = page.locator("#btn-pause-resume")
            if pause_button.is_enabled():
                pause_button.click()
                steps.append("pause-clicked")
                page.wait_for_timeout(300)
                if pause_button.is_enabled():
                    pause_button.click()
                    steps.append("resume-clicked")
            page.screenshot(path=str(run_dir / "03_progress.png"), full_page=True)

            page.click("#btn-history")
            page.wait_for_selector("#history-list .btn-view-details")
            steps.append("history-loaded")
            page.screenshot(path=str(run_dir / "04_history.png"), full_page=True)

            page.click("#history-list .btn-view-details")
            page.wait_for_selector("#details-modal", state="visible")
            steps.append("modal-opened")
            page.screenshot(path=str(run_dir / "05_modal.png"), full_page=True)

            retry_button = page.locator(".btn-retry-company").first
            if retry_button.count() > 0:
                retry_button.click()
                steps.append("retry-company-clicked")

            page.click("#btn-export-modal-report")
            steps.append("export-clicked")

            page.click("#btn-close-modal")
            steps.append("modal-closed")
            page.screenshot(path=str(run_dir / "06_done.png"), full_page=True)

            dom_state = {
                "progress_text": page.locator("#progress-text").inner_text(),
                "history_rows": page.locator("#history-list tr").count(),
                "console_ui_lines": page.locator("#console-log .log-line").count(),
            }

            browser.close()

    except PlaywrightError as exc:
        page_errors.append(f"PlaywrightError: {exc}")
        dom_state = {
            "progress_text": "",
            "history_rows": 0,
            "console_ui_lines": 0,
        }
    finally:
        server.shutdown()
        server.server_close()
        if isinstance(bridge, RealBridge):
            bridge.close()

    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "base_url": base_url,
        "sample_csv": str(sample_csv),
        "steps": steps,
        "console_log_count": len(console_logs),
        "page_error_count": len(page_errors),
        "console_logs": console_logs,
        "page_errors": page_errors,
        "dom_state": dom_state,
    }

    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return ProbeResult(run_dir=run_dir, report_path=report_path, report=report)


def main() -> int:
    parser = argparse.ArgumentParser(description="Playwright GUI probe with mock/real backend bridge")
    parser.add_argument("--mode", choices=["mock", "real"], default="mock", help="Backend mode")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    parser.add_argument("--timeout-ms", type=int, default=20000, help="Per-action timeout in ms")
    args = parser.parse_args()

    result = run_probe(mode=args.mode, headed=args.headed, timeout_ms=args.timeout_ms)
    report = result.report

    print(f"Run directory: {result.run_dir}")
    print(f"Report: {result.report_path}")
    print(f"Mode: {report['mode']}")
    print(f"Steps executed: {len(report['steps'])}")
    print(f"Page errors captured: {report['page_error_count']}")

    return 0 if report["page_error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
