import os
import sys
import random
import re
import time
import threading
import multiprocessing as mp
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchWindowException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.browser import BrowserManager
from src.core.config import Config
from src.core.downloader import Downloader
from src.core.excel_processor import ExcelProcessor
from src.core.folder_hierarchy import FolderHierarchyManager


# ---------- Helpers for process workers ----------
def _has_active_downloads(folder_path: str) -> bool:
    try:
        names = os.listdir(folder_path)
    except Exception:
        return False
    return any(name.endswith(('.crdownload', '.tmp', '.partial')) for name in names)


def _wait_for_downloads_complete(folder_path: str, timeout: int = 180, poll: float = 0.5) -> None:
    start = time.time()
    quiet_required = 1.5
    quiet_start = None
    while time.time() - start < timeout:
        if not _has_active_downloads(folder_path):
            if quiet_start is None:
                quiet_start = time.time()
            elif time.time() - quiet_start >= quiet_required:
                return
        else:
            quiet_start = None
        time.sleep(poll)


def _parse_counts_from_message(message: str) -> tuple[int | None, int | None]:
    """Extract (downloaded, total) from messages like 'Initiated download for X/Y attachments.'"""
    if not message:
        return None, None
    m = re.search(r"(\d+)\s*/\s*(\d+)", message)
    if not m:
        return None, None
    try:
        return int(m.group(1)), int(m.group(2))
    except Exception:
        return None, None


def _humanize_exception(exc: Exception) -> str:
    mapping: dict[type[Exception], str] = {
        InvalidSessionIdException: 'Browser session expired while processing the PO.',
        NoSuchWindowException: 'Browser window closed unexpectedly.',
        TimeoutException: 'Timed out waiting for the page to finish loading.',
    }
    for exc_type, friendly in mapping.items():
        if isinstance(exc, exc_type):
            return friendly

    text = str(exc).strip()
    if not text:
        text = exc.__class__.__name__
    if len(text) > 150:
        text = text[:147] + '...'
    return f"{exc.__class__.__name__}: {text}"


def _derive_status_label(result: dict | None) -> str:
    if not result:
        return 'FAILED'
    if 'status_code' in result and result['status_code']:
        return result['status_code']

    success = result.get('success', False)
    message = result.get('message', '') or ''
    msg_lower = message.lower()
    dl, total = _parse_counts_from_message(message)
    if success:
        if total == 0 or 'no attachments' in msg_lower:
            return 'NO_ATTACHMENTS'
        if dl is not None and total is not None and dl < total:
            return 'PARTIAL'
        return 'COMPLETED'
    if 'oops' in msg_lower or 'not found' in msg_lower:
        return 'PO_NOT_FOUND'
    return 'FAILED'


def _suffix_for_status(status_code: str) -> str:
    if status_code == 'COMPLETED':
        return '_COMPLETED'
    if status_code == 'FAILED':
        return '_FAILED'
    if status_code == 'NO_ATTACHMENTS':
        return '_NO_ATTACHMENTS'
    if status_code == 'PARTIAL':
        return '_PARTIAL'
    if status_code == 'PO_NOT_FOUND':
        return '_PO_NOT_FOUND'
    return f'_{status_code}'


def _rename_folder_with_status(folder_path: str, status_code: str) -> str:
    try:
        base_dir = os.path.dirname(folder_path)
        base_name = os.path.basename(folder_path)
        target = f"{base_name}{_suffix_for_status(status_code)}"
        new_path = os.path.join(base_dir, target)
        if folder_path == new_path:
            return folder_path
        if os.path.exists(new_path):
            i = 2
            while True:
                candidate = os.path.join(base_dir, f"{target}-{i}")
                if not os.path.exists(candidate):
                    new_path = candidate
                    break
                i += 1
        os.rename(folder_path, new_path)
        return new_path
    except Exception:
        return folder_path


def process_po_worker(args):
    """Run a single PO in its own process, with its own Edge driver.

    Args tuple: (po_data, hierarchy_cols, has_hierarchy_data)
    Returns: dict with keys: po_number_display, status_code, message, final_folder
    """
    po_data, hierarchy_cols, has_hierarchy_data = args
    display_po = po_data['po_number']
    folder_manager = FolderHierarchyManager()
    browser_manager = BrowserManager()
    driver = None
    folder_path = ''
    try:
        print(f"[worker] ▶ Starting PO {display_po}", flush=True)
        # Create folder without suffix
        folder_path = folder_manager.create_folder_path(po_data, hierarchy_cols, has_hierarchy_data)
        print(f"[worker] 📁 Folder ready: {folder_path}", flush=True)

        # Start browser for this worker and set download dir
        print("[worker] 🚀 Initializing WebDriver...", flush=True)
        # Avoid using a shared profile in workers to prevent profile locks/hangs
        try:
            from src.core.config import Config as _Cfg
            _Cfg.EDGE_PROFILE_DIR = ''
            _Cfg.EDGE_PROFILE_NAME = ''
        except Exception:
            pass
        browser_manager.initialize_driver()
        driver = browser_manager.driver
        print("[worker] ⚙️ WebDriver initialized", flush=True)
        browser_manager.update_download_directory(folder_path)
        print("[worker] 📥 Download dir set", flush=True)

        # Download
        downloader = Downloader(driver, browser_manager)
        po_number = po_data['po_number']
        print(f"[worker] 🌐 Starting download for {po_number}", flush=True)
        result_payload = downloader.download_attachments_for_po(po_number)
        message = result_payload.get('message', '')
        print(f"[worker] ✅ Download routine finished for {po_number}", flush=True)

        # Wait for downloads to finish
        _wait_for_downloads_complete(folder_path)
        print("[worker] ⏳ Downloads settled", flush=True)

        status_code = _derive_status_label(result_payload)
        final_folder = _rename_folder_with_status(folder_path, status_code)
        result = {
            'po_number_display': display_po,
            'status_code': status_code,
            'message': message,
            'final_folder': final_folder,
            'supplier_name': result_payload.get('supplier_name', ''),
            'attachments_found': result_payload.get('attachments_found', 0),
            'attachments_downloaded': result_payload.get('attachments_downloaded', 0),
            'coupa_url': result_payload.get('coupa_url', ''),
            'attachment_names': result_payload.get('attachment_names', []),
            'status_reason': result_payload.get('status_reason', ''),
            'errors': result_payload.get('errors', []),
            'success': result_payload.get('success', False),
            'fallback_attempted': result_payload.get('fallback_attempted', False),
            'fallback_used': result_payload.get('fallback_used', False),
            'fallback_details': result_payload.get('fallback_details', {}),
            'fallback_trigger_reason': result_payload.get('fallback_trigger_reason', ''),
            'source_page': result_payload.get('source_page', 'PO'),
            'initial_url': result_payload.get('initial_url', result_payload.get('coupa_url', '')),
        }
        print(f"[worker] 🏁 Done {display_po} → {status_code}", flush=True)
        return result
    except Exception as e:
        try:
            # Attempt rename with FAILED suffix even on exceptions
            if folder_path:
                final_folder = _rename_folder_with_status(folder_path, 'FAILED')
            else:
                final_folder = ''
        except Exception:
            final_folder = folder_path or ''
        friendly = _humanize_exception(e)
        return {
            'po_number_display': display_po,
            'status_code': 'FAILED',
            'message': friendly,
            'final_folder': final_folder,
            'status_reason': 'UNEXPECTED_EXCEPTION',
            'errors': [{'filename': '', 'reason': friendly}],
            'success': False,
        }
    finally:
        try:
            browser_manager.cleanup()
        except Exception:
            pass


def _scan_local_drivers() -> list[str]:
    """Return a list of plausible local driver paths under 'drivers/' directory."""
    candidates: list[str] = []
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'drivers')
    if not os.path.isdir(base):
        return candidates
    for root, _dirs, files in os.walk(base):
        for name in files:
            if name.lower().startswith('msedgedriver'):
                candidates.append(os.path.join(root, name))
    return sorted(candidates)


def _prompt_bool(prompt: str, default: bool) -> bool:
    d = 'Y/n' if default else 'y/N'
    while True:
        ans = input(f"{prompt} [{d}]: ").strip().lower()
        if ans == '' and default is not None:
            return default
        if ans in ('y', 'yes'):
            return True
        if ans in ('n', 'no'):
            return False
        print("Please answer y or n.")


def _interactive_setup() -> None:
    """Interactive wizard to gather runtime configuration from the user."""
    print("\n=== Interactive Setup ===")
    print("(Press Enter to accept defaults shown in [brackets])")

    # 1) Input file path
    from src.core.excel_processor import ExcelProcessor
    default_input = ExcelProcessor.get_excel_file_path()
    inp = input(f"Path to input CSV/XLSX [{default_input}]: ").strip() or default_input
    os.environ['EXCEL_FILE_PATH'] = inp

    # 2) Choose execution model
    use_pool = _prompt_bool("Use process workers (one WebDriver per process)?", default=False)
    os.environ['USE_PROCESS_POOL'] = 'true' if use_pool else 'false'

    # 3) Process workers with safe cap (only if using process pool)
    try:
        default_workers = 1
        procs_int = default_workers
        if use_pool:
            procs = input(f"Number of process workers (1-3) [{default_workers}]: ").strip()
            if procs:
                procs_int = max(1, min(3, int(procs)))
    except Exception:
        procs_int = default_workers
    os.environ['PROC_WORKERS'] = str(procs_int)
    os.environ.setdefault('PROC_WORKERS_CAP', '3')

    # 4) Headless mode (default: Yes)
    headless = _prompt_bool("Run browser in headless mode?", default=True)
    os.environ['HEADLESS'] = 'true' if headless else 'false'

    # 5) Driver selection — auto-pick, fallback to download, final guidance
    # Respect existing env var; default to allowing auto-download
    allow_auto = os.environ.get('DRIVER_AUTO_DOWNLOAD', 'true').lower() == 'true'
    os.environ['DRIVER_AUTO_DOWNLOAD'] = 'true' if allow_auto else 'false'

    from src.core.driver_manager import DriverManager
    dm = DriverManager()
    try:
        auto_path = dm.get_driver_path()  # auto local match; may download if allowed
        os.environ['EDGE_DRIVER_PATH'] = auto_path
        print(f"   ✅ Auto-selected EdgeDriver: {auto_path}")
    except Exception as e:
        edge_version = dm.get_edge_version() or "unknown"
        major = edge_version.split('.')[0] if isinstance(edge_version, str) and '.' in edge_version else "unknown"
        print("   ❌ Could not auto-select/download EdgeDriver.")
        print(f"   Installed Edge version: {edge_version} (major {major})")
        print("   Please download a matching EdgeDriver:")
        print("   https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/")
        print("   Place it under 'drivers/' or set EDGE_DRIVER_PATH, then rerun.")
        manual = input("   Provide full path to EdgeDriver (or press Enter to continue without): ").strip()
        if manual:
            os.environ['EDGE_DRIVER_PATH'] = manual

    # 6) Download folder base
    default_dl = os.path.expanduser(Config.DOWNLOAD_FOLDER)
    dl = input(f"Base download folder [{default_dl}]: ").strip() or default_dl
    Config.DOWNLOAD_FOLDER = os.path.expanduser(dl)
    os.makedirs(Config.DOWNLOAD_FOLDER, exist_ok=True)

    # 7) Edge profile usage
    use_prof = _prompt_bool("Use Edge profile (cookies/login)?", default=True)
    os.environ['USE_EDGE_PROFILE'] = 'true' if use_prof else 'false'
    print("Tip: Leave blank to keep the default shown in brackets.")
    prof_dir = input(f"Edge profile directory [{Config.EDGE_PROFILE_DIR}]: ").strip()
    if prof_dir:
        Config.EDGE_PROFILE_DIR = os.path.expanduser(prof_dir)
    prof_name = input(f"Edge profile name [{Config.EDGE_PROFILE_NAME}]: ").strip()
    if prof_name:
        Config.EDGE_PROFILE_NAME = prof_name
    # 8) Pre-start cleanup (kill running Edge processes)
    kill_procs = _prompt_bool("Close any running Edge processes before starting?", default=True)
    os.environ['CLOSE_EDGE_PROCESSES'] = 'true' if kill_procs else 'false'
    print("=== End of setup ===\n")


class MainApp:
    def __init__(self):
        self.excel_processor = ExcelProcessor()
        self.browser_manager = BrowserManager()
        self.folder_hierarchy = FolderHierarchyManager()
        self.driver = None
        self.lock = threading.Lock()  # Thread safety for browser operations
        self._run_start_time: float | None = None
        self._current_po_start_time: float | None = None
        self._completed_po_count = 0
        self._total_po_count = 0
        self._accumulated_po_seconds = 0.0

    def _has_active_downloads(self, folder_path: str) -> bool:
        try:
            names = os.listdir(folder_path)
        except Exception:
            return False
        suffixes = ('.crdownload', '.tmp', '.partial')
        return any(name.endswith(suffixes) for name in names)

    def _wait_for_downloads_complete(self, folder_path: str, timeout: int = 120, poll: float = 0.5) -> None:
        """Wait until there are no active download temp files in the folder."""
        start = time.time()
        # Require a short quiet period with no temp files
        quiet_required = 1.5
        quiet_start = None
        while time.time() - start < timeout:
            if not self._has_active_downloads(folder_path):
                if quiet_start is None:
                    quiet_start = time.time()
                elif time.time() - quiet_start >= quiet_required:
                    return
            else:
                quiet_start = None
            time.sleep(poll)
        # Timed out; proceed anyway
        return

    def _rename_folder_with_status(self, folder_path: str, status: str) -> str:
        """Rename the PO folder to include the status suffix. Returns final path."""
        try:
            base_dir = os.path.dirname(folder_path)
            base_name = os.path.basename(folder_path)
            target = f"{base_name}_{status}"
            new_path = os.path.join(base_dir, target)
            if folder_path == new_path:
                return folder_path
            # If target exists, append a simple numeric suffix
            if os.path.exists(new_path):
                i = 2
                while True:
                    candidate = os.path.join(base_dir, f"{target}-{i}")
                    if not os.path.exists(candidate):
                        new_path = candidate
                        break
                    i += 1
            os.rename(folder_path, new_path)
            print(f"   🏷️ Renamed folder to: {new_path}")
            return new_path
        except Exception as e:
            print(f"   ⚠️ Could not rename folder: {e}")
            return folder_path

    def initialize_browser_once(self):
        """Initialize browser once and keep it open for all POs."""
        if not self.driver:
            print("🚀 Initializing browser for parallel processing...")
            self.browser_manager.initialize_driver()
            self.driver = self.browser_manager.driver
            print("✅ Browser initialized successfully")

    def _prepare_progress_tracking(self, total_pos: int) -> None:
        """Reset telemetry accumulators before sequential PO processing."""
        self._total_po_count = max(0, total_pos)
        self._completed_po_count = 0
        self._accumulated_po_seconds = 0.0
        self._current_po_start_time = None
        self._run_start_time = time.perf_counter()

    def _format_duration(self, seconds: float | None) -> str:
        if seconds is None or seconds < 0:
            return "--:--"
        total_minutes = int(seconds // 60)
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours:02d}:{minutes:02d}"

    def _progress_snapshot(self) -> tuple[str, str, str]:
        if self._run_start_time is None:
            return "--:--", "--:--", "--"

        elapsed_seconds = max(0.0, time.perf_counter() - self._run_start_time)
        elapsed = self._format_duration(elapsed_seconds)

        if self._completed_po_count <= 0 or self._accumulated_po_seconds <= 0.0:
            return elapsed, "--:--", "--"

        remaining_pos = max(self._total_po_count - self._completed_po_count, 0)
        if remaining_pos <= 0:
            eta_time = datetime.now()
            return elapsed, "00:00", eta_time.strftime("%Y-%m-%d %H:%M")

        average = self._accumulated_po_seconds / self._completed_po_count
        remaining_seconds = max(0.0, average * remaining_pos)
        remaining = self._format_duration(remaining_seconds)
        eta = (datetime.now() + timedelta(seconds=remaining_seconds)).strftime("%Y-%m-%d %H:%M")
        return elapsed, remaining, eta

    def _build_progress_line(self, index: int, total: int) -> str:
        elapsed, remaining, eta = self._progress_snapshot()
        return (
            f"📋 Processing PO {index + 1}/{total} – "
            f"Elapsed Time: {elapsed}, Remaining Time: {remaining}, "
            f"Estimated Completion: {eta}"
        )

    def _register_po_completion(self) -> None:
        if self._current_po_start_time is None:
            return

        duration = max(0.0, time.perf_counter() - self._current_po_start_time)
        self._accumulated_po_seconds += duration
        if self._total_po_count > 0:
            self._completed_po_count = min(self._completed_po_count + 1, self._total_po_count)
        else:
            self._completed_po_count += 1
        self._current_po_start_time = None

    def _compose_csv_message(self, result_payload: dict) -> str:
        status_code = (result_payload.get('status_code') or '').upper()
        status_reason = result_payload.get('status_reason', '') or ''
        fallback_used = bool(result_payload.get('fallback_used'))
        fallback_details = result_payload.get('fallback_details') or {}
        trigger_reason = (
            result_payload.get('fallback_trigger_reason')
            or fallback_details.get('trigger_reason')
            or ''
        )
        message = result_payload.get('message', '') or ''

        if fallback_used:
            parts: list[str] = []
            if message:
                parts.append(message)

            if trigger_reason == 'po_without_pdf':
                parts.append('PO page did not expose PDF attachments.')
            elif trigger_reason == 'po_without_attachments':
                parts.append('PO page did not expose attachments.')

            source = (fallback_details.get('source') or '').strip()
            if source:
                friendly_source = source.replace('::', ' via ')
                parts.append(f"PR link source: {friendly_source}")

            pr_url = (fallback_details.get('url') or '').strip()
            if pr_url:
                parts.append(f"PR URL: {pr_url}")

            if not parts:
                parts.append('PR fallback used to retrieve documents.')
            return ' — '.join(parts)

        if status_code == 'COMPLETED':
            return ''
        if message:
            return message
        if status_code == 'NO_ATTACHMENTS':
            return status_reason.replace('_', ' ').title() if status_reason else 'No attachments found.'
        if status_reason:
            return status_reason.replace('_', ' ').title()
        return ''

    def process_single_po(self, po_data, hierarchy_cols, has_hierarchy_data, index, total):
        """Process a single PO using the existing browser window (no extra tabs)."""
        display_po = po_data['po_number']
        po_number = po_data['po_number']
        if self._run_start_time is None:
            self._prepare_progress_tracking(total)

        self._current_po_start_time = time.perf_counter()
        print(self._build_progress_line(index, total))
        print(f"   Current PO: {display_po}")

        try:
            # Create hierarchical folder structure
            folder_path = self.folder_hierarchy.create_folder_path(
                po_data, hierarchy_cols, has_hierarchy_data
            )
            print(f"   📁 Folder: {folder_path}")
            
            # Process entirely under lock to avoid Selenium races (single window)
            with self.lock:
                # Ensure driver exists and is responsive
                if not self.browser_manager.is_browser_responsive():
                    print("   ⚠️ Browser not responsive. Reinitializing driver...")
                    self.browser_manager.cleanup()
                    self.browser_manager.initialize_driver()
                    self.driver = self.browser_manager.driver

                # Ensure downloads for this PO go to the right folder
                self.browser_manager.update_download_directory(folder_path)

                # Create downloader and attempt processing
                downloader = Downloader(self.driver, self.browser_manager)
                try:
                    result_payload = downloader.download_attachments_for_po(po_number)
                except (InvalidSessionIdException, NoSuchWindowException) as e:
                    # Session/tab was lost. Try to recover once.
                    print(f"   ⚠️ Session issue detected ({type(e).__name__}). Recovering driver and retrying once...")
                    self.browser_manager.cleanup()
                    self.browser_manager.initialize_driver()
                    self.driver = self.browser_manager.driver
                    downloader = Downloader(self.driver, self.browser_manager)
                    result_payload = downloader.download_attachments_for_po(po_number)

                message = result_payload.get('message', '')

                # Wait for downloads to complete before finalizing folder name
                self._wait_for_downloads_complete(folder_path)

                # Derive unified status and rename folder with standardized suffix
                status_code = _derive_status_label(result_payload)
                final_folder = _rename_folder_with_status(folder_path, status_code)
                status_reason = result_payload.get('status_reason', '')
                errors = result_payload.get('errors', [])

                # Update status with the final folder path and enriched fields
                formatted_names = self.folder_hierarchy.format_attachment_names(
                    result_payload.get('attachment_names', [])
                )
                csv_message = self._compose_csv_message(result_payload)
                self.excel_processor.update_po_status(
                    display_po,
                    status_code,
                    supplier=result_payload.get('supplier_name', ''),
                    attachments_found=result_payload.get('attachments_found', 0),
                    attachments_downloaded=result_payload.get('attachments_downloaded', 0),
                    error_message=csv_message,
                    download_folder=final_folder,
                    coupa_url=result_payload.get('coupa_url', ''),
                    attachment_names=formatted_names,
                )

            emoji = {
                'COMPLETED': '✅',
                'NO_ATTACHMENTS': '📭',
                'PARTIAL': '⚠️',
                'FAILED': '❌',
                'PO_NOT_FOUND': '🚫',
            }.get(status_code, 'ℹ️')
            log_message = message or status_reason or status_code
            print(f"   {emoji} {display_po}: {log_message}")
            return status_code in {'COMPLETED', 'NO_ATTACHMENTS'}

        except Exception as e:
            friendly = _humanize_exception(e)
            print(f"   ❌ Error processing {display_po}: {friendly}")
            # Use unified FAILED status on exceptions in sequential mode
            self.excel_processor.update_po_status(display_po, "FAILED", error_message=friendly)

            # Clean up browser state: close any extra tabs and return to main tab
            try:
                with self.lock:
                    # Skip cleanup if driver doesn't exist
                    if self.driver is None:
                        print("   ⚠️ Driver is None - skipping cleanup")
                        return False
                    
                    # Attempt to close extra tabs if they exist
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                    except (NoSuchWindowException, InvalidSessionIdException) as e:
                        print(f"   ⚠️ Tab cleanup error: {str(e)}")
            except Exception as unexpected_error:
                print(f"   ⚠️ Unexpected cleanup error: {str(unexpected_error)}")
            
            # Always attempt browser recovery after errors
            try:
                with self.lock:
                    if self.driver is None or not self.browser_manager.is_browser_responsive():
                        print("   ⚠️ Attempting browser recovery")
                        self.browser_manager.cleanup()
                        self.browser_manager.initialize_driver()
                        self.driver = self.browser_manager.driver
            except Exception as recovery_error:
                print(f"   🔴 Browser recovery failed: {str(recovery_error)}")
                
            return False
        finally:
            self._register_po_completion()

    def run(self) -> None:
        """
        Main execution loop for processing POs with parallel tabs.
        """
        # Interactive wizard for runtime config
        _interactive_setup()

        os.makedirs(Config.INPUT_DIR, exist_ok=True)
        os.makedirs(Config.DOWNLOAD_FOLDER, exist_ok=True)

        try:
            excel_path = self.excel_processor.get_excel_file_path()
            # Inform which input file will be processed (CSV or Excel)
            _, ext = os.path.splitext(excel_path.lower())
            file_kind = "CSV" if ext == ".csv" else "Excel"
            print(f"📄 Processing input file: {excel_path} ({file_kind})")
            po_entries, original_cols, hierarchy_cols, has_hierarchy_data = self.excel_processor.read_po_numbers_from_excel(excel_path)
            valid_entries = self.excel_processor.process_po_numbers(po_entries)
        except Exception as e:
            print(f"❌ Failed to read or process input file: {e}")
            return

        if not valid_entries:
            print("No valid PO entries found to process.")
            return

        print(f"Found {len(valid_entries)} POs to process.")

        if Config.RANDOM_SAMPLE_POS and Config.RANDOM_SAMPLE_POS > 0:
            k = min(Config.RANDOM_SAMPLE_POS, len(valid_entries))
            print(f"Sampling {k} random POs for processing...")
            valid_entries = random.sample(valid_entries, k)

        # Convert to list of PO data
        po_data_list = []
        for display_po, po_number in valid_entries:
            for entry in po_entries:
                if entry['po_number'] == display_po:
                    po_data_list.append(entry)
                    break

        print(f"🚀 Starting parallel processing with {len(po_data_list)} POs...")
        use_process_pool = os.environ.get('USE_PROCESS_POOL', 'false').lower() == 'true'

        successful = 0
        failed = 0

        if use_process_pool:
            # Real parallelism: one Edge driver per process
            # Limit concurrency to reduce Edge rate-limits and memory pressure
            default_workers = min(2, len(po_data_list))
            env_procs = int(os.environ.get("PROC_WORKERS", str(default_workers)))
            hard_cap = int(os.environ.get("PROC_WORKERS_CAP", "3"))
            proc_workers = max(1, min(env_procs, hard_cap, len(po_data_list)))
            print(f"📊 Using {proc_workers} process worker(s), one WebDriver per process")

            # Submit process tasks and update Excel serially in parent
            with ProcessPoolExecutor(max_workers=proc_workers, mp_context=mp.get_context("spawn")) as executor:
                futures = [
                    executor.submit(process_po_worker, (po_data, hierarchy_cols, has_hierarchy_data))
                    for po_data in po_data_list
                ]
                for future in as_completed(futures):
                    result = future.result()
                    display_po = result['po_number_display']
                    status_code = result['status_code']
                    message = result['message']
                    final_folder = result['final_folder']
                    status_reason = result.get('status_reason', '')

                    # Update Excel in parent (avoids CSV write contention)
                    formatted_names = self.folder_hierarchy.format_attachment_names(
                        result.get('attachment_names', [])
                    )
                    csv_message = self._compose_csv_message(result)
                    self.excel_processor.update_po_status(
                        display_po,
                        status_code,
                        supplier=result.get('supplier_name', ''),
                        attachments_found=result.get('attachments_found', 0),
                        attachments_downloaded=result.get('attachments_downloaded', 0),
                        error_message=csv_message,
                        download_folder=final_folder,
                        coupa_url=result.get('coupa_url', ''),
                        attachment_names=formatted_names,
                    )
                    print("-" * 60)
                    emoji = {
                        'COMPLETED': '✅',
                        'NO_ATTACHMENTS': '📭',
                        'PARTIAL': '⚠️',
                        'FAILED': '❌',
                        'PO_NOT_FOUND': '🚫',
                    }.get(status_code, 'ℹ️')
                    log_text = message or status_reason or status_code
                    print(f"   {emoji} {display_po}: {log_text}")
                    if status_code in {'COMPLETED', 'NO_ATTACHMENTS'}:
                        successful += 1
                    else:
                        failed += 1
        else:
            # Legacy in-process mode (single WebDriver, sequential)
            print("📊 Using in-process mode (single WebDriver, sequential)")
            self.initialize_browser_once()
            self._prepare_progress_tracking(len(po_data_list))
            for i, po_data in enumerate(po_data_list):
                ok = self.process_single_po(po_data, hierarchy_cols, has_hierarchy_data, i, len(po_data_list))
                if ok:
                    successful += 1
                else:
                    failed += 1

        print("-" * 60)
        print(f"🎉 Processing complete!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
    
        print(f"📊 Total: {successful + failed}")

    def close(self):
        """Close the browser properly."""
        if self.driver:
            print("🔄 Closing browser...")
            self.browser_manager.cleanup()
            self.driver = None
            print("✅ Browser closed successfully")


if __name__ == "__main__":
    app = MainApp()
    try:
        app.run()
    finally:
        app.close()
