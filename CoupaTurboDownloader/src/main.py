import os
import sys
import asyncio
import subprocess
import threading
from pathlib import Path
from urllib.parse import quote, urlparse

import webview

from src.db.session_db import SessionDB
from src.gui.api import AppAPI
from src.gui.cli_supervisor import CliProcessSupervisor
from src.engine.authenticator import get_coupa_cookies, load_cached_cookies
from src.engine.benchmarker import benchmark
from src.engine.updater import (
    apply_update_and_restart,
    check_for_update,
    download_update as fetch_update,
    prepare_update,
)


def resolve_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        bundle_root = Path(sys._MEIPASS)
        candidates = [
            bundle_root.parent / "Resources" / relative_path,
            bundle_root / relative_path,
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        # Preserve a useful path in the error shown by pywebview if an asset is
        # missing from a malformed package.
        return str(candidates[-1])
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_database_path() -> str:
    user_home = os.path.expanduser("~")
    app_data_dir = os.path.join(user_home, ".coupa_turbo")
    os.makedirs(app_data_dir, exist_ok=True)
    return os.path.join(app_data_dir, "sessions.db")


class TurboAPI(AppAPI):
    """GUI bridge backed by the canonical process_all_pos.py pipeline."""

    def __init__(self, db: SessionDB, default_download_dir: str):
        super().__init__(db, default_download_dir)
        self.cli_backend = CliProcessSupervisor()
        self._pending_input_path: str | None = None

    def authenticate(self) -> dict:
        """Open Edge for Coupa login, return extracted cookies dict."""
        try:
            cookies = asyncio.run(get_coupa_cookies(load_from_file=True))
            self.set_auth_cookies(cookies)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_benchmark(self, urls: list[str], base_url: str = "https://unilever.coupahost.com") -> dict:
        """Run network benchmark against sample URLs, return optimal params."""
        try:
            cookies = asyncio.run(get_coupa_cookies(load_from_file=True))
            result = asyncio.run(benchmark(urls, cookies=cookies, base_url=base_url))
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_updates(self) -> dict:
        """Check GitHub Releases for newer version."""
        try:
            update_info = asyncio.run(check_for_update())
            if update_info:
                return {"success": True, "update_available": True, **update_info}
            return {"success": True, "update_available": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def download_update(self, download_url: str, asset_name: str = "update.zip", checksum_url: str | None = None) -> dict:
        """Download a verified release asset to the local update cache."""
        try:
            from pathlib import Path
            update_dir = Path.home() / ".coupa_turbo" / "updates"
            path = asyncio.run(fetch_update(download_url, str(update_dir), asset_name, checksum_url))
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def install_update(self, package_path: str) -> dict:
        """Install a downloaded update and restart the application."""
        try:
            payload = prepare_update(package_path)
            apply_update_and_restart(payload)
            # The detached updater waits for this process to exit before
            # replacing the executable or .app bundle.
            threading.Timer(0.7, lambda: os._exit(0)).start()
            return {"success": True, "restarting": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def import_file(self, filepath: str) -> dict:
        """Validate and stage the input; the CLI creates the real session."""
        validation = self.validate_input_file(filepath)
        if not validation.get("valid"):
            return {
                "success": False,
                "error": "Input validation failed.",
                "validation": validation,
            }
        self._pending_input_path = str(Path(filepath).expanduser().resolve())
        return {
            "success": True,
            "session_id": 0,
            "total_pos": validation.get("valid_po_count", 0),
            "backend": "cli",
        }

    def start_download(
        self,
        session_id: int,
        download_dir: str,
        concurrency: int = 4,
        hierarchy_order: list[str] | None = None,
        retry_attempts: int | None = None,
    ) -> dict:
        if not self._pending_input_path:
            return {"success": False, "error": "No validated input file is staged."}
        settings = self.get_app_settings()
        selected_dir = str(download_dir or self.get_default_download_directory()).strip()
        effective_concurrency = int(settings.get("concurrency", concurrency))
        effective_retry_attempts = int(retry_attempts or settings.get("retry_attempts", 1))
        msg_processing = str(settings.get("msg_processing", "convert_extract"))
        deduplicate_files = bool(settings.get("deduplicate_files", True))
        selected_path = Path(self._absolute_user_path(selected_dir))
        persistent_root = selected_path.parent if selected_path.name.startswith("run_") else selected_path
        self._persist_download_root(str(persistent_root))
        return self.cli_backend.start(
            self._pending_input_path,
            str(selected_path),
            effective_concurrency,
            run_dir=str(selected_path),
            hierarchy_order=hierarchy_order,
            retry_attempts=effective_retry_attempts,
            msg_processing=msg_processing,
            deduplicate_files=deduplicate_files,
        )

    def get_active_session_status(self, session_id: int) -> dict:
        return self.cli_backend.get_status(session_id)

    def pause_download(self, session_id: int) -> dict:
        return self.cli_backend.pause()

    def resume_download(self, session_id: int) -> dict:
        return self.cli_backend.resume()

    def stop_download(self, session_id: int) -> dict:
        return self.cli_backend.stop()

    def retry_errors(self, session_id: int) -> dict:
        return self.cli_backend.retry_errors(int(session_id))

    def retry_po(self, session_id: int, po_number: str) -> dict:
        return self.cli_backend.retry_po(int(session_id), po_number)

    def open_input_file(self, session_id: int) -> dict:
        return self.cli_backend.open_input_file(int(session_id))

    def open_coupa_po(self, po_number: str) -> dict:
        value = str(po_number or "").strip()
        order_number = value[2:] if value.upper().startswith(("PO", "PM")) else value
        if not order_number:
            return {"success": False, "error": "PO number is missing."}
        target = f"https://unilever.coupahost.com/order_headers/{quote(order_number, safe='')}"
        return self.open_external_url(target)

    def open_external_url(self, url: str) -> dict:
        target = str(url).strip()
        parsed = urlparse(target)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or not (
            hostname == "unilever.coupahost.com" or hostname.endswith(".coupahost.com")
        ):
            return {"success": False, "error": "Only Coupa URLs can be opened."}
        try:
            # Use the OS launcher synchronously so failures are observable. A
            # detached Popen can report success even when macOS rejects it.
            if sys.platform == "darwin":
                # Keep browser selection outside the app. On macOS the default
                # URL handler (including Finicky) chooses the browser.
                subprocess.run(["/usr/bin/open", target], check=True, timeout=10)
            elif os.name == "nt":
                os.startfile(target)  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", target], check=True, timeout=10)
            return {"success": True, "url": target, "external_browser": True}
        except (OSError, subprocess.SubprocessError) as exc:
            try:
                import webbrowser
                if webbrowser.open_new_tab(target):
                    return {"success": True, "url": target, "external_browser": True, "fallback": True}
            except Exception:
                pass
            return {"success": False, "error": f"Could not open the external browser: {exc}"}

    def get_concurrency_estimates(self) -> dict:
        return self.cli_backend.concurrency_estimates()

    def get_session_history(self) -> list[dict]:
        return self.cli_backend.history()

    def get_session_details(self, session_id: int) -> dict:
        return self.cli_backend.details(int(session_id))

    def delete_session(self, session_id: int) -> dict:
        return self.cli_backend.delete_session(int(session_id))

    def clear_all_sessions(self) -> dict:
        return self.cli_backend.clear_all_sessions()

    def export_session_report(self, session_id: int, dest_filepath: str) -> dict:
        return self.cli_backend.export_report(int(session_id), dest_filepath)

    def confirm_and_retry_company(self, session_id: int, company_code: str) -> dict:
        return {"success": False, "error": "Supplier-specific retry is not implemented; use Retry failed POs."}


def _activate_macos_window() -> None:
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyRegular
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        app.activateIgnoringOtherApps_(True)
    except Exception:
        # Window activation is best-effort and must not prevent startup.
        pass


def calculate_window_geometry(screen_width: int, screen_height: int, screen_x: int = 0, screen_y: int = 0) -> dict[str, int]:
    """Size the window to 85% of the screen width and center it."""
    width = max(980, round(screen_width * 0.85))
    height = min(820, max(700, round(screen_height * 0.85)))
    return {
        "width": width,
        "height": height,
        "x": round(screen_x + (screen_width - width) / 2),
        "y": round(screen_y + (screen_height - height) / 2),
    }


def main():
    # The packaged GUI can also host the canonical CLI pipeline in a child
    # process, avoiding a second crawler implementation.
    if "--cli-pipeline" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg != "--cli-pipeline"]
        import process_all_pos
        asyncio.run(process_all_pos.main())
        return

    db_path = get_database_path()
    db = SessionDB(db_path)

    api = TurboAPI(db, default_download_dir=os.path.expanduser("~/Downloads/CoupaAttachments"))

    html_file = resolve_path(os.path.join("gui", "web", "index.html"))

    primary_screen = webview.screens[0] if getattr(webview, "screens", None) else None
    geometry = calculate_window_geometry(
        int(primary_screen.width) if primary_screen else 1600,
        int(primary_screen.height) if primary_screen else 900,
        int(primary_screen.x) if primary_screen else 0,
        int(primary_screen.y) if primary_screen else 0,
    )

    window = webview.create_window(
        title="Coupa Turbo Downloader",
        url=html_file,
        js_api=api,
        width=geometry["width"],
        height=geometry["height"],
        x=geometry["x"],
        y=geometry["y"],
        screen=primary_screen,
        min_size=(980, 700),
        resizable=True,
    )
    if sys.platform == "darwin":
        def position_and_activate_window() -> None:
            # Cocoa may ignore x/y while constructing the WebKit window. Apply
            # the measured geometry again after the native window is visible.
            window.resize(geometry["width"], geometry["height"])
            window.move(geometry["x"], geometry["y"])
            _activate_macos_window()

        window.events.shown += position_and_activate_window

    try:
        # Serve bundled HTML/CSS/JS through pywebview's loopback server;
        # this avoids file:// and resource-path 404s in packaged .app bundles.
        webview.start(debug=False, http_server=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
