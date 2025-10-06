import os
import sys
import shutil
import tempfile
import random
import re
import time
import threading
import multiprocessing as mp
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
from enum import Enum
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchWindowException,
    TimeoutException,
)
# Add the project root to Python path for local execution
project_root = Path(__file__).resolve().parents[2]
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

# Add EXPERIMENTAL directory to path for local corelib imports
experimental_root = Path(__file__).resolve().parents[1]
experimental_root_str = str(experimental_root)
if experimental_root_str not in sys.path:
    sys.path.insert(0, experimental_root_str)

from corelib.browser import BrowserManager
from corelib.config import Config as ExperimentalConfig
from corelib.downloader import Downloader
from corelib.excel_processor import ExcelProcessor
from corelib.folder_hierarchy import FolderHierarchyManager
from corelib.ui import DownloadCLIController, PODescriptor
from corelib.models import InteractiveSetupSession, HeadlessConfiguration

# Import worker pool for parallel processing
from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

# Import CSV handler for incremental persistence
from src.csv_handler import CSVHandler, WriteQueue
from EXPERIMENTAL.workers.models import PoolConfig

# Feature toggles for the experimental runner (NEW: interactive mode is now default)
# If environment variables are provided, assume non-interactive automation mode
# Otherwise, default to interactive mode for better user experience
def _should_use_interactive_mode() -> bool:
    """Determine if interactive mode should be used based on environment and arguments."""
    # Check explicit ENABLE_INTERACTIVE_UI override first
    explicit_interactive = os.environ.get('ENABLE_INTERACTIVE_UI', '').strip().lower()
    if explicit_interactive in ('true', 'false'):
        return explicit_interactive == 'true'
    
    # Check if runtime environment variables suggest automation mode (not .env file values)
    # These are typically set by CI/CD or automation scripts
    runtime_automation_vars = [
        'EXCEL_FILE_PATH', 'HEADLESS', 'USE_PROCESS_POOL', 'PROC_WORKERS'
    ]
    has_runtime_automation = any(os.environ.get(var) for var in runtime_automation_vars)
    
    # Default: interactive mode unless runtime automation env vars are present
    return not has_runtime_automation

ENABLE_INTERACTIVE_UI = _should_use_interactive_mode()

# Global variable to store current setup session (replaces environment variables)
_current_setup_session: Optional[InteractiveSetupSession] = None
# ---------- Profile clone helpers (mirrors tools/test_three_profile_clones.py) ----------
_SKIP_DIRS = {
    'Cache', 'Code Cache', 'GPUCache', 'Service Worker', 'Session Storage',
    'Local Storage', 'IndexedDB', 'logs', 'GrShaderCache', 'Crashpad', 'ShaderCache'
}


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _copy_root_essentials(source_root: str, dest_root: str) -> None:
    src = os.path.join(source_root, 'Local State')
    if os.path.exists(src):
        try:
            shutil.copy2(src, os.path.join(dest_root, 'Local State'))
        except Exception:
            pass


def _copy_profile_folder(src_profile: str, dst_profile: str) -> None:
    _ensure_dir(dst_profile)
    try:
        for item in os.listdir(src_profile):
            if item in _SKIP_DIRS:
                continue
            s = os.path.join(src_profile, item)
            d = os.path.join(dst_profile, item)
            try:
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            except Exception:
                # best-effort clone; skip problematic items
                pass
    except FileNotFoundError:
        pass


def _create_profile_clone(base_user_data_dir: str, profile_name: str, clone_root: str) -> str:
    _ensure_dir(clone_root)
    _copy_root_essentials(base_user_data_dir, clone_root)
    src_profile = os.path.join(base_user_data_dir, profile_name)
    dst_profile = os.path.join(clone_root, profile_name)
    _copy_profile_folder(src_profile, dst_profile)
    return clone_root



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

    Args tuple: (po_data, hierarchy_cols, has_hierarchy_data, headless_config[, download_root, csv_path])
    Returns: dict with keys: po_number_display, status_code, message, final_folder
    """
    if len(args) == 4:
        po_data, hierarchy_cols, has_hierarchy_data, headless_config = args
        download_root = os.environ.get('DOWNLOAD_FOLDER', ExperimentalConfig.DOWNLOAD_FOLDER)
        csv_path = None
    elif len(args) == 5:
        po_data, hierarchy_cols, has_hierarchy_data, headless_config, download_root = args
        csv_path = None
    elif len(args) >= 6:
        po_data, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path = args[:6]
    else:
        raise ValueError("process_po_worker expects at least 4 arguments")

    download_root = os.path.abspath(os.path.expanduser(download_root)) if download_root else os.path.abspath(os.path.expanduser(ExperimentalConfig.DOWNLOAD_FOLDER))
    os.environ['DOWNLOAD_FOLDER'] = download_root
    try:
        ExperimentalConfig.DOWNLOAD_FOLDER = download_root
        from corelib.config import Config
        Config.DOWNLOAD_FOLDER = download_root
    except Exception:
        pass
    display_po = po_data['po_number']
    folder_manager = FolderHierarchyManager()
    browser_manager = BrowserManager()
    driver = None
    folder_path = ''
    clone_dir = ''
    
    # Initialize CSV handler if path provided
    csv_handler = None
    if csv_path:
        try:
            import sys
            from pathlib import Path
            # Add src directory to path for imports
            src_path = Path(__file__).parent.parent.parent / 'src'
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))
            from csv_handler.handler import CSVHandler
            csv_handler = CSVHandler(csv_path)
            print(f"[worker] 📊 CSV handler initialized for {csv_path}", flush=True)
        except Exception as e:
            print(f"[worker] ⚠️ Failed to initialize CSV handler: {e}", flush=True)
    
    # Log headless configuration for this worker
    print(f"[worker] 🎯 Headless configuration: {headless_config}", flush=True)
    
    try:
        print(f"[worker] ▶ Starting PO {display_po}", flush=True)
        # Create folder without suffix
        folder_path = folder_manager.create_folder_path(po_data, hierarchy_cols, has_hierarchy_data)
        print(f"[worker] 📁 Folder ready: {folder_path}", flush=True)

        # Start browser for this worker and set download dir
        print("[worker] 🚀 Initializing WebDriver...", flush=True)
        # Clone and load the selected profile for this worker (isolated user-data-dir)
        try:
            base_ud = os.path.expanduser(ExperimentalConfig.EDGE_PROFILE_DIR)
            profile_name = ExperimentalConfig.EDGE_PROFILE_NAME or 'Default'
            session_root = os.path.join(tempfile.gettempdir(), 'edge_profile_clones')
            _ensure_dir(session_root)
            clone_dir = os.path.join(session_root, f"proc_{os.getpid()}_{int(time.time()*1000)}")
            _create_profile_clone(base_ud, profile_name, clone_dir)
            # Point config to the clone so BrowserManager uses it
            ExperimentalConfig.USE_PROFILE = True
            ExperimentalConfig.EDGE_PROFILE_DIR = clone_dir
            ExperimentalConfig.EDGE_PROFILE_NAME = profile_name
        except Exception as e:
            print(f"[worker] ⚠️ Profile clone failed, continuing without profile: {e}")
            try:
                # Ensure we don't point to a broken dir
                ExperimentalConfig.EDGE_PROFILE_DIR = ''
            except Exception:
                pass

        browser_manager.initialize_driver(headless=headless_config.get_effective_headless_mode())
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
        
        # Persist to CSV if handler available
        if csv_handler:
            try:
                csv_updates = {
                    'po_number': display_po,
                    'status': result_payload.get('status_code', status_code),
                    'supplier': result_payload.get('supplier_name', ''),
                    'attachments_found': result_payload.get('attachments_found', 0),
                    'attachments_downloaded': result_payload.get('attachments_downloaded', 0),
                    'final_folder': final_folder,
                    'error_message': message,
                    'coupa_url': result_payload.get('coupa_url', ''),
                    'attachment_names': ', '.join(result_payload.get('attachment_names', []))
                }
                csv_handler.update_po_status(**csv_updates)
                print(f"[worker] 💾 CSV updated for {display_po}", flush=True)
            except Exception as e:
                print(f"[worker] ⚠️ Failed to update CSV: {e}", flush=True)
        
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
        
        # Persist failed result to CSV if handler available
        if csv_handler:
            try:
                csv_updates = {
                    'po_number': display_po,
                    'status': 'ERROR',
                    'supplier': po_data.get('supplier', ''),
                    'attachments_found': 0,
                    'attachments_downloaded': 0,
                    'final_folder': final_folder,
                    'error_message': friendly,
                    'coupa_url': po_data.get('coupa_url', ''),
                    'attachment_names': ''
                }
                csv_handler.update_po_status(**csv_updates)
                print(f"[worker] 💾 CSV updated for failed {display_po}", flush=True)
            except Exception as csv_e:
                print(f"[worker] ⚠️ Failed to update CSV for failed PO: {csv_e}", flush=True)
        
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
        # Best-effort cleanup of clone directory
        if clone_dir:
            try:
                shutil.rmtree(clone_dir, ignore_errors=True)
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


def _interactive_setup() -> 'InteractiveSetupSession':
    """Interactive wizard to gather runtime configuration from the user."""
    print("\n=== Interactive Setup ===")
    print("(Press Enter to accept defaults shown in [brackets])")

    # 1) Input file path
    from src.core.excel_processor import ExcelProcessor
    default_input = ExcelProcessor.get_excel_file_path()
    inp = input(f"Path to input CSV/XLSX [{default_input}]: ").strip() or default_input
    # Persist selection to experimental config (avoids env usage)
    ExperimentalConfig.EXCEL_FILE_PATH = inp

    # 2) Download folder path
    # Use value from .env as default, but expand ~ properly
    default_download = os.path.expanduser(ExperimentalConfig.DOWNLOAD_FOLDER)
    
    # If using the old default format, suggest the new timestamped format
    if "CoupaDownloads" in default_download and not any(char.isdigit() for char in os.path.basename(default_download)):
        # Generate a new timestamped folder as suggestion
        from corelib.config import generate_timestamped_download_folder
        suggested_download = generate_timestamped_download_folder("/Users/juliocezar/Downloads")
        print(f"💡 Suggested timestamped folder: {suggested_download}")
        default_download = suggested_download
    
    download_path = input(f"Download folder path [{default_download}]: ").strip() or default_download
    # Expand user path and ensure it's absolute
    download_path = os.path.expanduser(download_path)
    if not os.path.isabs(download_path):
        download_path = os.path.abspath(download_path)
    
    # Update config and ensure folder exists
    normalized_download = os.path.abspath(os.path.expanduser(download_path))
    ExperimentalConfig.DOWNLOAD_FOLDER = normalized_download
    # Keep core Config in sync so browser options pick the right path on first init
    try:
        from corelib.config import Config
        Config.DOWNLOAD_FOLDER = normalized_download
    except Exception:
        pass
    # Propagate selection so child processes inherit the correct folder
    os.environ['DOWNLOAD_FOLDER'] = normalized_download
    os.makedirs(normalized_download, exist_ok=True)
    print(f"📁 Downloads will be saved to: {download_path}")

    # 3) Choose execution model
    use_pool = _prompt_bool("Use process workers (one WebDriver per process)?", default=False)
    ExperimentalConfig.USE_PROCESS_POOL = bool(use_pool)

    # 4) Process workers with safe cap (only if using process pool)
    default_workers = 1
    try:
        procs_int = default_workers
        if use_pool:
            procs = input(f"Number of process workers (1-8) [{default_workers}]: ").strip()
            if procs:
                procs_int = max(1, min(8, int(procs)))
    except Exception:
        procs_int = default_workers
    ExperimentalConfig.PROC_WORKERS = int(procs_int)
    ExperimentalConfig.PROC_WORKERS_CAP = int(ExperimentalConfig.PROC_WORKERS_CAP or 8)

    # 5) Headless mode (default: Yes) - NEW: Use HeadlessConfiguration instead of env var
    headless_preference = _prompt_bool("Run browser in headless mode?", default=True)
    
    # Create interactive setup session to track user preferences
    from corelib.models import InteractiveSetupSession
    setup_session = InteractiveSetupSession(headless_preference=headless_preference)
    
    # Log the headless mode configuration
    mode_str = "headless" if headless_preference else "visible"
    print(f"🎯 Browser mode configured: {mode_str}")
    
    # Store setup session for later use (replace env var dependency)
    global _current_setup_session
    _current_setup_session = setup_session
    
    return setup_session

    # 5) Driver selection — auto-pick, fallback to download, final guidance
    # Respect existing env var; default to allowing auto-download
    allow_auto = bool(getattr(ExperimentalConfig, 'DRIVER_AUTO_DOWNLOAD', True))
    ExperimentalConfig.DRIVER_AUTO_DOWNLOAD = allow_auto

    from src.core.driver_manager import DriverManager
    dm = DriverManager()
    try:
        auto_path = dm.get_driver_path()  # auto local match; may download if allowed
        ExperimentalConfig.EDGE_DRIVER_PATH = auto_path
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
            ExperimentalConfig.EDGE_DRIVER_PATH = manual

    # 6) Download folder base
    default_dl = os.path.expanduser(ExperimentalConfig.DOWNLOAD_FOLDER)
    dl = input(f"Base download folder [{default_dl}]: ").strip() or default_dl
    ExperimentalConfig.DOWNLOAD_FOLDER = os.path.expanduser(dl)
    os.makedirs(ExperimentalConfig.DOWNLOAD_FOLDER, exist_ok=True)

    # 7) Edge profile usage
    use_prof = _prompt_bool("Use Edge profile (cookies/login)?", default=True)
    ExperimentalConfig.USE_PROFILE = bool(use_prof)
    print("Tip: Leave blank to keep the default shown in brackets.")
    prof_dir = input(f"Edge profile directory [{ExperimentalConfig.EDGE_PROFILE_DIR}]: ").strip()
    if prof_dir:
        ExperimentalConfig.EDGE_PROFILE_DIR = os.path.expanduser(prof_dir)
    prof_name = input(f"Edge profile name [{ExperimentalConfig.EDGE_PROFILE_NAME}]: ").strip()
    if prof_name:
        ExperimentalConfig.EDGE_PROFILE_NAME = prof_name
    # 8) Pre-start cleanup (kill running Edge processes)
    kill_procs = _prompt_bool("Close any running Edge processes before starting?", default=True)
    ExperimentalConfig.CLOSE_EDGE_PROCESSES = bool(kill_procs)
    print("=== End of setup ===\n")


def _apply_env_overrides_non_interactive() -> 'InteractiveSetupSession':
    """Configure runtime from environment variables for non-interactive runs.

    Respects the following vars (all optional):
      - EXCEL_FILE_PATH: path to CSV/XLSX
      - USE_PROCESS_POOL: 'true'|'false' (defaults to false)
      - PROC_WORKERS: int 1-8 (defaults to 2)
      - HEADLESS: 'true'|'false' (defaults to true)
      - EDGE_PROFILE_DIR / EDGE_PROFILE_NAME: profile hints
      - DOWNLOAD_FOLDER: base output folder
    """
    # Import here to avoid circulars during module import
    from src.core.excel_processor import ExcelProcessor as SrcExcelProcessor
    from corelib.models import InteractiveSetupSession

    # Input path
    input_path = os.environ.get('EXCEL_FILE_PATH')
    if not input_path:
        input_path = SrcExcelProcessor.get_excel_file_path()
    ExperimentalConfig.EXCEL_FILE_PATH = os.path.expanduser(input_path)

    # Execution model
    ExperimentalConfig.USE_PROCESS_POOL = os.environ.get('USE_PROCESS_POOL', 'false').strip().lower() == 'true'
    try:
        workers = int(os.environ.get('PROC_WORKERS', '2'))
    except ValueError:
        workers = 2
    ExperimentalConfig.PROC_WORKERS = max(1, min(8, workers))
    ExperimentalConfig.PROC_WORKERS_CAP = int(getattr(ExperimentalConfig, 'PROC_WORKERS_CAP', 8) or 8)

    # Headless
    headless_pref = os.environ.get('HEADLESS', 'true').strip().lower() == 'true'
    setup_session = InteractiveSetupSession(headless_preference=headless_pref)

    # Download folder (apply timestamp prefix automatically)
    from datetime import datetime
    
    base_dl = os.path.abspath(os.path.expanduser(os.environ.get('DOWNLOAD_FOLDER', ExperimentalConfig.DOWNLOAD_FOLDER)))
    
    # Add timestamp prefix to download folder
    timestamp = datetime.now().strftime('%Y%m%d-%Hh%M')
    parent_dir = os.path.dirname(base_dl)
    base_name = os.path.basename(base_dl.rstrip('/'))
    timestamped_dl = os.path.join(parent_dir, f"{timestamp}_{base_name}")
    
    ExperimentalConfig.DOWNLOAD_FOLDER = os.path.abspath(os.path.expanduser(timestamped_dl))
    
    # IMPORTANT: Also update Config.DOWNLOAD_FOLDER so browser uses the correct path
    from corelib.config import Config
    Config.DOWNLOAD_FOLDER = os.path.abspath(os.path.expanduser(timestamped_dl))
    normalized_dl = Config.DOWNLOAD_FOLDER
    os.environ['DOWNLOAD_FOLDER'] = normalized_dl
    os.makedirs(normalized_dl, exist_ok=True)

    # Profile hints (optional)
    prof_dir = os.environ.get('EDGE_PROFILE_DIR')
    if prof_dir:
        ExperimentalConfig.EDGE_PROFILE_DIR = os.path.expanduser(prof_dir)
    prof_name = os.environ.get('EDGE_PROFILE_NAME')
    if prof_name:
        ExperimentalConfig.EDGE_PROFILE_NAME = prof_name

    return setup_session


class MainApp:
    def __init__(self, enable_parallel: bool = True, max_workers: int = 4):
        """
        Initialize MainApp with optional parallel processing support.
        
        Args:
            enable_parallel: Whether to enable parallel processing for multiple POs
            max_workers: Maximum number of parallel workers (1-8) when parallel processing is enabled
        """
        # Validate parallel processing parameters
        if not isinstance(enable_parallel, bool):
            raise TypeError("enable_parallel must be a boolean")
        
        if not (1 <= max_workers <= 8):
            raise ValueError(f"max_workers must be between 1 and 8, got {max_workers}")
        
        # Parallel processing configuration
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self._processing_session: Optional[ProcessingSession] = None
        self._last_parallel_report: Optional[Dict[str, Any]] = None
        
        # Original initialization
        self.excel_processor = ExcelProcessor()
        self.browser_manager = BrowserManager()
        self.folder_hierarchy = FolderHierarchyManager()
        self.driver = None
        self.lock = threading.Lock()  # Thread safety for browser operations
        self._run_start_time: float | None = None
        self._current_po_start_time: float | None = None
        
        # CSV handler for incremental persistence
        self.csv_handler: CSVHandler | None = None
        self._csv_write_queue: WriteQueue | None = None
        self._csv_session_id: str | None = None
        self._completed_po_count = 0
        self._total_po_count = 0
        self._accumulated_po_seconds = 0.0
        self.cli_controller: DownloadCLIController | None = None
        self._headless_config: HeadlessConfiguration | None = None

    def set_headless_configuration(self, headless_config: HeadlessConfiguration) -> None:
        """Set the headless configuration for this MainApp instance."""
        self._headless_config = headless_config
        print(f"[MainApp] 🎯 Headless configuration set: {headless_config}")

    def _get_headless_setting(self) -> bool:
        """Get the current headless setting from configuration."""
        if self._headless_config is None:
            print("[MainApp] ⚠️  No headless configuration set, falling back to default")
            return False  # Safe default
        return self._headless_config.get_effective_headless_mode()
    
    def _parallel_progress_callback(self, progress: Dict[str, Any]) -> None:
        """Progress callback for ProcessingSession parallel processing."""
        try:
            total = progress.get('total_tasks', 0)
            completed = progress.get('completed_tasks', 0)
            failed = progress.get('failed_tasks', 0)
            active = progress.get('active_tasks', 0)
            
            if total > 0:
                completion_pct = (completed + failed) / total * 100
                print(f"📊 Progress: {completed}/{total} completed ({completion_pct:.1f}%), {active} active, {failed} failed")
                
                # Update UI if available
                if self.cli_controller:
                    # Update overall progress - this is a simplified integration
                    pass
                    
        except Exception as e:
            print(f"Error in progress callback: {e}")

    # ---- UI helpers ---------------------------------------------------------------------

    @staticmethod
    def _build_po_descriptor(entry: dict) -> PODescriptor:
        return PODescriptor(
            po_number=entry.get('po_number', ''),
            vendor=(entry.get('supplier') or entry.get('vendor') or ''),
            link=entry.get('coupa_url', ''),
        )

    def _ui_po_started(self, po_entry: dict) -> None:
        controller = self.cli_controller
        if controller is None:
            return
        descriptor = self._build_po_descriptor(po_entry)
        if descriptor.po_number:
            controller.po_started(descriptor)

    def _ui_log(self, po_number: str, message: str, level: str = 'info') -> None:
        controller = self.cli_controller
        if controller is None or not po_number or not message:
            return
        controller.log(po_number, message, level=level)

    def _ui_update_metadata(self, po_number: str, vendor: str | None, link: str | None) -> None:
        controller = self.cli_controller
        if controller is None or not po_number:
            return
        controller.update_metadata(po_number, vendor, link)

    def _ui_po_completed(self, po_number: str, status: str, message: str | None = None) -> None:
        controller = self.cli_controller
        if controller is None or not po_number:
            return
        if message:
            controller.log(po_number, message)
        controller.po_completed(po_number, status)

    def _stop_requested(self) -> bool:
        controller = self.cli_controller
        return bool(controller and controller.should_stop())

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
            self.browser_manager.initialize_driver(headless=self._get_headless_setting())
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

    def _initialize_csv_handler(self, csv_path: Path) -> None:
        """Instantiate CSV handler, backup current CSV, and boot write queue."""
        import uuid
        try:
            backup_dir = csv_path.parent.parent / 'backup'
            backup_dir.mkdir(parents=True, exist_ok=True)
            self.csv_handler = CSVHandler(csv_path=csv_path, backup_dir=backup_dir)
            self._csv_session_id = uuid.uuid4().hex[:8]
            backup_path = self.csv_handler.create_session_backup(self._csv_session_id)
            print(f"🛡️ CSV backup created at: {backup_path}")
            self._csv_write_queue = WriteQueue(self.csv_handler)
            self._csv_write_queue.start_writer_thread()
        except Exception as handler_error:
            self.csv_handler = None
            self._csv_write_queue = None
            self._csv_session_id = None
            print(f"⚠️ Failed to initialize CSV handler: {handler_error}")

    def _shutdown_csv_handler(self) -> None:
        """Gracefully stop write queue threads."""
        if self._csv_write_queue:
            self._csv_write_queue.stop_writer_thread(timeout=15.0)
        self._csv_write_queue = None

    def _persist_csv_result(self, result: Dict[str, Any]) -> None:
        """Persist a processing result to the CSV if handler is active."""
        if not self.csv_handler:
            return

        updates = self._build_csv_updates(result)
        po_number = result.get('po_number') or result.get('po_number_display')
        if not po_number:
            return

        if self._csv_write_queue:
            self._csv_write_queue.submit_write(po_number, updates)
        else:
            self.csv_handler.update_record(po_number, updates)

    @staticmethod
    def _build_csv_updates(result: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a processing result into CSV column updates."""
        status_code = (result.get('status_code') or '').upper() or 'FAILED'
        attachment_names = result.get('attachment_names') or []
        if isinstance(attachment_names, str):
            attachment_names = [name for name in attachment_names.split(';') if name]

        error_message = ''
        success = result.get('success')
        if success is None:
            success = status_code in {'COMPLETED', 'NO_ATTACHMENTS', 'PARTIAL'}
        if not success:
            error_message = result.get('message', '') or result.get('error', '')

        updates: Dict[str, Any] = {
            'STATUS': status_code,
            'ATTACHMENTS_FOUND': result.get('attachments_found', 0),
            'ATTACHMENTS_DOWNLOADED': result.get('attachments_downloaded', 0),
            'AttachmentName': attachment_names,
            'DOWNLOAD_FOLDER': result.get('final_folder', ''),
            'COUPA_URL': result.get('coupa_url', ''),
            'ERROR_MESSAGE': error_message,
        }

        supplier_name = result.get('supplier_name')
        if supplier_name:
            updates['SUPPLIER'] = supplier_name

        last_processed = result.get('last_processed')
        if isinstance(last_processed, datetime):
            updates['LAST_PROCESSED'] = last_processed.isoformat()
        elif isinstance(last_processed, str) and last_processed:
            updates['LAST_PROCESSED'] = last_processed

        return updates

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
        vendor_hint = po_data.get('supplier') or po_data.get('vendor') or ''
        self._ui_update_metadata(display_po, vendor_hint, po_data.get('coupa_url'))
        self._ui_po_started(po_data)
        self._ui_log(display_po, 'Starting processing')
        print(self._build_progress_line(index, total))
        print(f"   Current PO: {display_po}")

        try:
            # Create hierarchical folder structure
            folder_path = self.folder_hierarchy.create_folder_path(
                po_data, hierarchy_cols, has_hierarchy_data
            )
            print(f"   📁 Folder: {folder_path}")
            self._ui_log(display_po, f"Folder ready: {folder_path}")

            # Process entirely under lock to avoid Selenium races (single window)
            with self.lock:
                # Ensure driver exists and is responsive
                if not self.browser_manager.is_browser_responsive():
                    print("   ⚠️ Browser not responsive. Reinitializing driver...")
                    self._ui_log(display_po, 'Browser not responsive. Reinitializing driver…', level='warning')
                    self.browser_manager.cleanup()
                    self.browser_manager.initialize_driver(headless=self._get_headless_setting())
                    self.driver = self.browser_manager.driver

                # Ensure downloads for this PO go to the right folder
                self.browser_manager.update_download_directory(folder_path)

                # Create downloader and attempt processing
                downloader = Downloader(self.driver, self.browser_manager)
                try:
                    self._ui_log(display_po, 'Navigating to Coupa page and collecting attachments…')
                    result_payload = downloader.download_attachments_for_po(po_number)
                except (InvalidSessionIdException, NoSuchWindowException) as e:
                    # Session/tab was lost. Try to recover once.
                    print(f"   ⚠️ Session issue detected ({type(e).__name__}). Recovering driver and retrying once...")
                    self._ui_log(
                        display_po,
                        f'Session issue detected ({type(e).__name__}). Recovering driver and retrying…',
                        level='warning',
                    )
                    self.browser_manager.cleanup()
                    self.browser_manager.initialize_driver(headless=self._get_headless_setting())
                    self.driver = self.browser_manager.driver
                    downloader = Downloader(self.driver, self.browser_manager)
                    self._ui_log(display_po, 'Retrying download after driver recovery')
                    result_payload = downloader.download_attachments_for_po(po_number)

                message = result_payload.get('message', '')

                # Wait for downloads to complete before finalizing folder name
                self._wait_for_downloads_complete(folder_path)
                self._ui_log(display_po, 'Downloads settled')

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
                self._ui_update_metadata(
                    display_po,
                    result_payload.get('supplier_name', ''),
                    result_payload.get('coupa_url', ''),
                )

                # Persist to CSV if handler initialized
                if csv_handler:
                    self._persist_csv_result(result_payload)

            emoji = {
                'COMPLETED': '✅',
                'NO_ATTACHMENTS': '📭',
                'PARTIAL': '⚠️',
                'FAILED': '❌',
                'PO_NOT_FOUND': '🚫',
            }.get(status_code, 'ℹ️')
            log_message = message or status_reason or status_code
            print(f"   {emoji} {display_po}: {log_message}")
            self._ui_po_completed(display_po, status_code, log_message)
            return status_code in {'COMPLETED', 'NO_ATTACHMENTS'}

        except Exception as e:
            friendly = _humanize_exception(e)
            print(f"   ❌ Error processing {display_po}: {friendly}")
            self._ui_log(display_po, friendly, level='error')
            self._ui_po_completed(display_po, 'FAILED', friendly)
            # Use unified FAILED status on exceptions in sequential mode
            self.excel_processor.update_po_status(display_po, "FAILED", error_message=friendly)

            # Persist to CSV if handler is initialized
            if self.csv_handler:
                failed_result = {
                    'po_number': po_number,
                    'po_number_display': display_po,
                    'status_code': 'FAILED',
                    'message': friendly,
                    'supplier_name': vendor_hint,
                }
                self._persist_csv_result(failed_result)

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
                        self.browser_manager.initialize_driver(headless=self._get_headless_setting())
                        self.driver = self.browser_manager.driver
            except Exception as recovery_error:
                print(f"   🔴 Browser recovery failed: {str(recovery_error)}")
                self._ui_log(display_po, f'Browser recovery failed: {recovery_error}', level='error')

            return False
        finally:
            self._register_po_completion()

    def _process_po_entries(
        self,
        po_data_list: list[dict],
        hierarchy_cols: list[str],
        has_hierarchy_data: bool,
        use_process_pool: bool,
        headless_config: HeadlessConfiguration,
    ) -> tuple[int, int]:
        """
        Process PO entries with automatic parallel mode selection.
        
        Enhanced to support ProcessingSession for intelligent parallel processing.
        Falls back to original implementation for backward compatibility.
        """
        successful = 0
        failed = 0

        # Check if parallel processing is enabled and beneficial
        if self.enable_parallel and len(po_data_list) > 1 and use_process_pool:
            try:
                print(f"🚀 Using ProcessingSession with parallel processing ({self.max_workers} workers)")
                
                # Create ProcessingSession for intelligent mode selection
                self._processing_session = ProcessingSession(
                    headless_config=headless_config,
                    enable_parallel=self.enable_parallel,
                    max_workers=self.max_workers,
                    progress_callback=self._parallel_progress_callback,
                    hierarchy_columns=hierarchy_cols,
                    has_hierarchy_data=has_hierarchy_data,
                )
                
                # Configure CSV path for workers if CSV handler is available
                if self.csv_handler and hasattr(self.csv_handler, 'csv_path'):
                    self._processing_session.set_csv_path(str(self.csv_handler.csv_path))
                
                # Convert po_data_list to the format expected by ProcessingSession
                # Preserve all hierarchy data for proper folder structure creation
                processed_po_list = []
                for po_data in po_data_list:
                    # Create a copy to preserve all fields including hierarchy columns
                    processed_po = dict(po_data)
                    
                    # Ensure core fields are properly mapped
                    if 'po_number' not in processed_po:
                        processed_po['po_number'] = po_data.get('po_number', '')
                    if 'supplier' not in processed_po:
                        processed_po['supplier'] = po_data.get('supplier', '')
                    if 'url' not in processed_po and 'coupa_url' in po_data:
                        processed_po['url'] = po_data.get('coupa_url', '')
                    if 'amount' not in processed_po:
                        processed_po['amount'] = po_data.get('amount', 0.0)
                    
                    processed_po_list.append(processed_po)
                
                # Process using ProcessingSession
                successful, failed, session_report = self._processing_session.process_pos(processed_po_list)
                
                print(f"📊 ProcessingSession completed:")
                print(f"  - Mode: {session_report.get('processing_mode', 'unknown')}")
                print(f"  - Workers: {session_report.get('worker_count', 1)}")
                print(f"  - Duration: {session_report.get('session_duration', 0):.2f}s")
                
                results_payload = session_report.get('results', []) or []
                if results_payload:
                    for result in results_payload:
                        display_po = result.get('po_number_display') or result.get('po_number', '')
                        status_code = result.get('status_code', 'FAILED')
                        message = result.get('message', '')
                        status_reason = result.get('status_reason', '')
                        final_folder = result.get('final_folder', '')
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
                        self._ui_update_metadata(
                            display_po,
                            result.get('supplier_name', ''),
                            result.get('coupa_url', ''),
                        )

                        # Persist to CSV if handler is initialized
                        if self.csv_handler:
                            self._persist_csv_result(result)

                        emoji = {
                            'COMPLETED': '✅',
                            'NO_ATTACHMENTS': '📭',
                            'PARTIAL': '⚠️',
                            'FAILED': '❌',
                            'PO_NOT_FOUND': '🚫',
                        }.get(status_code, 'ℹ️')
                        log_text = message or status_reason or status_code
                        print("-" * 60)
                        print(f"   {emoji} {display_po}: {log_text}")
                        self._ui_po_completed(display_po, status_code, log_text)
                else:
                    for i, po_data in enumerate(po_data_list):
                        display_po = po_data.get('po_number', f'PO_{i}')
                        status = "COMPLETED" if i < successful else "FAILED"
                        self.excel_processor.update_po_status(display_po, status)
                        self._ui_po_completed(display_po, status, status)
                
                self._last_parallel_report = session_report
                return successful, failed
                
            except Exception as e:
                print(f"⚠️  ProcessingSession failed, falling back to original processing: {e}")
                # Fall through to original implementation
                self._processing_session = None

        # Original implementation (backward compatibility)
        if use_process_pool:
            default_workers = min(2, len(po_data_list))
            from corelib.config import Config as ExperimentalConfig
            env_procs = int(getattr(ExperimentalConfig, 'PROC_WORKERS', default_workers))
            hard_cap = int(getattr(ExperimentalConfig, 'PROC_WORKERS_CAP', 3))
            proc_workers = max(1, min(env_procs, hard_cap, len(po_data_list)))
            print(f"📊 Using {proc_workers} process worker(s), one WebDriver per process")

            # Use the ExperimentalConfig.DOWNLOAD_FOLDER that was updated during setup
            download_root = os.path.abspath(os.path.expanduser(ExperimentalConfig.DOWNLOAD_FOLDER))

            with ProcessPoolExecutor(max_workers=proc_workers, mp_context=mp.get_context("spawn")) as executor:
                future_map: dict = {}
                for po_data in po_data_list:
                    if self._stop_requested():
                        print("🛑 Stop requested — skipping dispatch of remaining POs.")
                        break
                    descriptor = self._build_po_descriptor(po_data)
                    if descriptor.po_number:
                        self._ui_update_metadata(descriptor.po_number, descriptor.vendor, descriptor.link)
                        self._ui_po_started(po_data)
                        self._ui_log(descriptor.po_number, 'Dispatched to background worker')
                    
                    # Determine CSV path for worker
                    csv_path = None
                    if self.csv_handler and hasattr(self.csv_handler, 'csv_path'):
                        csv_path = str(self.csv_handler.csv_path)
                    
                    future = executor.submit(
                        process_po_worker,
                        (po_data, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path),
                    )
                    future_map[future] = po_data

                for future in as_completed(future_map):
                    po_data = future_map[future]
                    if self._stop_requested():
                        print("🛑 Stop requested — waiting current workers before exiting.")
                        # Drain remaining results without bookkeeping.
                        try:
                            future.result()
                        except Exception:
                            pass
                        continue
                    display_po = po_data.get('po_number', '')
                    try:
                        result = future.result()
                    except Exception as exc:
                        friendly = _humanize_exception(exc)
                        print("-" * 60)
                        print(f"   ❌ Worker error for {display_po}: {friendly}")
                        self.excel_processor.update_po_status(display_po, "FAILED", error_message=friendly)
                        self._ui_po_completed(display_po, 'FAILED', friendly)
                        failed += 1
                        continue

                    display_po = result['po_number_display']
                    status_code = result['status_code']
                    message = result.get('message', '')
                    final_folder = result.get('final_folder', '')
                    status_reason = result.get('status_reason', '')

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
                    self._ui_update_metadata(
                        display_po,
                        result.get('supplier_name', ''),
                        result.get('coupa_url', ''),
                    )

                    # Persist to CSV if handler is initialized
                    if self.csv_handler:
                        self._persist_csv_result(result)

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
                    self._ui_po_completed(display_po, status_code, log_text)
                    if status_code in {'COMPLETED', 'NO_ATTACHMENTS'}:
                        successful += 1
                    else:
                        failed += 1
        else:
            print("📊 Using in-process mode (single WebDriver, sequential)")
            self.initialize_browser_once()
            self._prepare_progress_tracking(len(po_data_list))
            for i, po_data in enumerate(po_data_list):
                if self._stop_requested():
                    print("🛑 Stop requested — aborting remaining sequential processing.")
                    break
                ok = self.process_single_po(po_data, hierarchy_cols, has_hierarchy_data, i, len(po_data_list))
                if ok:
                    successful += 1
                else:
                    failed += 1

        return successful, failed

    def run(self) -> None:
        """
        Main execution loop for processing POs with parallel tabs.
        """
        # Interactive or non-interactive configuration
        if ENABLE_INTERACTIVE_UI:
            setup_session = _interactive_setup()
        else:
            print("⚙️ Non-interactive mode: applying environment overrides")
            setup_session = _apply_env_overrides_non_interactive()
        
        # Set headless configuration from setup session
        self.set_headless_configuration(setup_session.create_headless_configuration())

        os.makedirs(ExperimentalConfig.INPUT_DIR, exist_ok=True)
        os.makedirs(ExperimentalConfig.DOWNLOAD_FOLDER, exist_ok=True)

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

        print(f"📊 CSV Reading Results:")
        print(f"  - Total entries read: {len(po_entries)}")
        print(f"  - Valid POs after processing: {len(valid_entries)}")
        print(f"  - PO numbers: {[entry[0] for entry in valid_entries[:10]]}{'...' if len(valid_entries) > 10 else ''}")

        # Initialize CSV handler if input file is CSV
        csv_input_path = Path(excel_path)
        if csv_input_path.suffix.lower() == '.csv' and not self.csv_handler:
            self._initialize_csv_handler(csv_input_path)

        # Disable sampling for parallel testing to ensure multiple POs
        # if ExperimentalConfig.RANDOM_SAMPLE_POS and ExperimentalConfig.RANDOM_SAMPLE_POS > 0:
        #     k = min(ExperimentalConfig.RANDOM_SAMPLE_POS, len(valid_entries))
        #     print(f"Sampling {k} random POs for processing...")
        #     valid_entries = random.sample(valid_entries, k)

        # Convert to list of PO data
        po_data_list = []
        for display_po, po_number in valid_entries:
            for entry in po_entries:
                if entry['po_number'] == display_po:
                    po_data_list.append(entry)
                    break

        print(f"📋 PO Data Conversion:")
        print(f"  - Valid entries: {len(valid_entries)}")
        print(f"  - Po_data_list created: {len(po_data_list)}")
        print(f"  - Sample PO data: {po_data_list[0] if po_data_list else 'None'}")
        print(f"🚀 Starting parallel processing with {len(po_data_list)} POs...")
        use_process_pool = bool(getattr(ExperimentalConfig, 'USE_PROCESS_POOL', False))

        requested_workers = getattr(ExperimentalConfig, 'PROC_WORKERS', self.max_workers)
        try:
            configured_workers = max(1, min(8, int(requested_workers)))
        except (TypeError, ValueError):
            configured_workers = self.max_workers
        self.max_workers = configured_workers

        if use_process_pool and not self.enable_parallel:
            self.enable_parallel = True

        descriptors = [
            self._build_po_descriptor(entry)
            for entry in po_data_list
            if entry.get('po_number')
        ]
        
        enable_ui = ENABLE_INTERACTIVE_UI
        results: dict[str, int] = {}

        def _run_pipeline(controller: DownloadCLIController) -> None:
            self.cli_controller = controller
            try:
                if self._headless_config is None:
                    raise RuntimeError("Headless configuration not set. Call set_headless_configuration first.")
                
                success, fail = self._process_po_entries(
                    po_data_list,
                    hierarchy_cols,
                    has_hierarchy_data,
                    use_process_pool,
                    self._headless_config,
                )
                results['success'] = success
                results['failed'] = fail
            finally:
                self.cli_controller = None

        if enable_ui and descriptors:
            controller = DownloadCLIController()
            try:
                controller.run_with_worker(descriptors, _run_pipeline)
            except Exception as exc:
                print(f"⚠️ Interactive UI disabled: {exc}")
                self.cli_controller = None
                if self._headless_config is None:
                    raise RuntimeError("Headless configuration not set. Call set_headless_configuration first.")
                
                successful, failed = self._process_po_entries(
                    po_data_list,
                    hierarchy_cols,
                    has_hierarchy_data,
                    use_process_pool,
                    self._headless_config,
                )
            else:
                successful = results.get('success', 0)
                failed = results.get('failed', 0)
        else:
            if self._headless_config is None:
                raise RuntimeError("Headless configuration not set. Call set_headless_configuration first.")
                
            successful, failed = self._process_po_entries(
                po_data_list,
                hierarchy_cols,
                has_hierarchy_data,
                use_process_pool,
                self._headless_config,
            )

        # Shutdown CSV handler to ensure all data is persisted
        if self.csv_handler:
            self._shutdown_csv_handler()

        print("-" * 60)
        print("🎉 Processing complete!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {successful + failed}")

    def close(self):
        """Close the browser properly."""
        # Shutdown CSV handler first
        if self.csv_handler:
            self._shutdown_csv_handler()
            
        if self.driver:
            print("🔄 Closing browser...")
            self.browser_manager.cleanup()
            self.driver = None
            print("✅ Browser closed successfully")


class SessionStatus(Enum):
    """Status enumeration for processing sessions."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingSession:
    """
    High-level processing session that manages PO batch processing with automatic mode selection.
    
    This class implements the ProcessingSession API contract for T026 and T027.
    """
    
    def __init__(
        self,
        headless_config: HeadlessConfiguration,
        enable_parallel: bool = True,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        hierarchy_columns: Optional[List[str]] = None,
        has_hierarchy_data: bool = False,
    ):
        """Initialize processing session for PO batch processing."""
        # Validate parameters
        if not isinstance(headless_config, HeadlessConfiguration):
            raise TypeError("headless_config must be HeadlessConfiguration instance")
        
        if not (1 <= max_workers <= 8):
            raise ValueError(f"max_workers must be between 1 and 8, got {max_workers}")
        
        # Configuration
        self.headless_config = headless_config
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self.hierarchy_columns = hierarchy_columns
        self.has_hierarchy_data = has_hierarchy_data
        
        # Session state
        self.status = SessionStatus.IDLE
        self.worker_pool: Optional[PersistentWorkerPool] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Processing metrics
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.active_tasks = 0
        self.processing_mode = "sequential"

        # Progress tracking
        self._progress_lock = threading.Lock()
        self._last_progress_update = datetime.now()
        self.last_results: List[Dict[str, Any]] = []
        
        # CSV handler support
        self.csv_path: Optional[str] = None
    
    def set_csv_path(self, csv_path: str) -> None:
        """Set CSV path for worker processes."""
        self.csv_path = csv_path
    
    def process_pos(self, po_list: List[dict]) -> Tuple[int, int, Dict[str, Any]]:
        """Process list of POs with automatic mode selection."""
        try:
            self.status = SessionStatus.RUNNING
            self.start_time = datetime.now()
            self.total_tasks = len(po_list)
            self.last_results = []
            
            # Determine processing mode
            self.processing_mode = self.get_processing_mode(len(po_list))
            
            print(f"🚀 Starting {self.processing_mode} processing of {len(po_list)} POs")
            
            if self.processing_mode == "parallel":
                return self._process_parallel(po_list)
            else:
                return self._process_sequential(po_list)
                
        except Exception as e:
            self.status = SessionStatus.FAILED
            print(f"❌ Processing failed: {e}")
            return 0, len(po_list), {"error": str(e)}
        
        finally:
            self.end_time = datetime.now()
            if self.status == SessionStatus.RUNNING:
                self.status = SessionStatus.COMPLETED
    
    def get_processing_mode(self, po_count: int) -> str:
        """Determine processing mode based on configuration and PO count."""
        # Decision criteria for parallel processing
        if not self.enable_parallel:
            return "sequential"
        
        if po_count <= 1:
            return "sequential"
        
        # Check system resources (simplified check)
        if self._check_system_resources():
            return "parallel"
        
        return "sequential"
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current processing progress and status."""
        with self._progress_lock:
            elapsed_time = 0.0
            if self.start_time:
                end_time = self.end_time or datetime.now()
                elapsed_time = (end_time - self.start_time).total_seconds()
            
            # Calculate estimated remaining time
            estimated_remaining = None
            if self.completed_tasks > 0 and self.total_tasks > self.completed_tasks:
                avg_time_per_task = elapsed_time / self.completed_tasks
                remaining_tasks = self.total_tasks - self.completed_tasks
                estimated_remaining = avg_time_per_task * remaining_tasks
            
            progress = {
                'session_status': self.status.value,
                'total_tasks': self.total_tasks,
                'completed_tasks': self.completed_tasks,
                'failed_tasks': self.failed_tasks,
                'active_tasks': self.active_tasks,
                'elapsed_time': elapsed_time,
                'estimated_remaining': estimated_remaining,
                'processing_mode': self.processing_mode,
                'worker_details': []
            }
            
            # Add worker details if parallel processing
            if self.worker_pool and self.processing_mode == "parallel":
                status = self.worker_pool.get_status()
                progress['worker_details'] = status.get('workers', {})
            
            return progress
    
    def stop_processing(self) -> bool:
        """Stop current processing session."""
        if self.status != SessionStatus.RUNNING:
            return True
        
        try:
            if self.worker_pool:
                # Run async shutdown in sync context
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Create task for shutdown
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self.worker_pool.shutdown())
                            future.result(timeout=60)  # 1 minute timeout
                    else:
                        loop.run_until_complete(self.worker_pool.shutdown())
                except RuntimeError:
                    asyncio.run(self.worker_pool.shutdown())
                
                self.worker_pool = None
                return True
            
            self.status = SessionStatus.COMPLETED
            return True
            
        except Exception as e:
            print(f"Error stopping processing: {e}")
            self.status = SessionStatus.FAILED
            return False
    
    # Private helper methods
    
    def _process_parallel(self, po_list: List[dict]) -> Tuple[int, int, Dict[str, Any]]:
        """Process POs using parallel worker pool."""
        # Check if profiles are disabled - if so, fall back to ProcessPoolExecutor
        from corelib.config import Config as _Cfg
        if not _Cfg.USE_PROFILE:
            print("🔄 Profiles disabled, using ProcessPoolExecutor instead of PersistentWorkerPool")
            return self._process_parallel_with_processpool(po_list)
        
        import asyncio
        
        async def _async_process():
            try:
                # Create PoolConfig with profile support
                base_profile_path = _Cfg.EDGE_PROFILE_DIR or ""
                if not base_profile_path:
                    raise ValueError("Profile path required for PersistentWorkerPool, but none configured")
                
                download_root = os.path.abspath(os.path.expanduser(_Cfg.DOWNLOAD_FOLDER))
                print(f"🏗️ Creating worker pool with download_root: {download_root}")

                config = PoolConfig(
                    worker_count=min(self.max_workers, len(po_list)),
                    headless_mode=self.headless_config.get_effective_headless_mode(),
                    base_profile_path=base_profile_path,
                    base_profile_name=ExperimentalConfig.EDGE_PROFILE_NAME or "Default",
                    hierarchy_columns=self.hierarchy_columns,
                    has_hierarchy_data=self.has_hierarchy_data,
                    download_root=download_root,
                )
                
                print(f"🔧 PoolConfig created with download_root: {config.download_root}")
                
                # Create and start worker pool
                csv_handler = None
                if hasattr(self, 'csv_path') and self.csv_path:
                    try:
                        from src.csv_handler import CSVHandler
                        from pathlib import Path
                        csv_handler = CSVHandler(Path(self.csv_path))
                        print(f"[PersistentWorkerPool] CSV handler created for: {self.csv_path}")
                    except Exception as e:
                        print(f"[PersistentWorkerPool] Failed to create CSV handler: {e}")
                self.worker_pool = PersistentWorkerPool(config, csv_handler=csv_handler)
                await self.worker_pool.start()
                
                # Submit tasks
                po_numbers = [po['po_number'] for po in po_list]
                handles = self.worker_pool.submit_tasks(po_list)

                # Wait for completion
                await self.worker_pool.wait_for_completion(timeout=600)  # 10 minute timeout

                # Collect results
                successful = 0
                failed = 0
                collected_results: List[Dict[str, Any]] = []

                for handle in handles:
                    try:
                        result = handle.wait_for_completion(timeout=10)
                        if not isinstance(result, dict):
                            result = {'success': False, 'status_code': 'FAILED', 'message': str(result)}
                        if 'po_number' not in result:
                            result['po_number'] = handle.po_number
                        if 'po_number_display' not in result:
                            result['po_number_display'] = result.get('po_number', handle.po_number)

                        collected_results.append(result)

                        status_code = result.get('status_code', 'FAILED')
                        if status_code in {'COMPLETED', 'NO_ATTACHMENTS'}:
                            successful += 1
                        else:
                            failed += 1
                    except Exception as e:
                        print(f"Error getting result for {handle.po_number}: {e}")
                        collected_results.append({
                            'po_number': handle.po_number,
                            'po_number_display': handle.po_number,
                            'status_code': 'FAILED',
                            'message': str(e),
                            'errors': [{'filename': '', 'reason': str(e)}],
                            'success': False,
                            'attachment_names': [],
                            'attachments_found': 0,
                            'attachments_downloaded': 0,
                            'final_folder': '',
                        })
                        failed += 1

                # Get performance data from status
                status = self.worker_pool.get_status()
                performance_data = {
                    'memory_usage': status.get('memory', {}),
                    'worker_stats': status.get('workers', {}),
                    'task_queue_stats': status.get('task_queue', {})
                }

                # Shutdown
                await self.worker_pool.shutdown()
                self.worker_pool = None

                # Process results for CSV persistence (workers should handle this individually)
                # Note: CSV persistence is handled by individual workers in process_po_worker function

                session_report = {
                    'processing_mode': 'parallel',
                    'worker_count': config.worker_count,
                    'performance_data': performance_data,
                    'session_duration': (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0,
                    'results': collected_results,
                }

                self.last_results = collected_results
                
                return successful, failed, session_report
                
            except Exception as e:
                if self.worker_pool:
                    try:
                        await self.worker_pool.shutdown()
                    except:
                        pass
                    self.worker_pool = None
                raise e
        
        # Run async processing in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If there's already a running loop, we need to handle this differently
                # For now, create a new thread with its own event loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _async_process())

                    return future.result(timeout=900)  # 15 minute timeout
            else:
                return loop.run_until_complete(_async_process())
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(_async_process())
    
    def _process_sequential(self, po_list: List[dict]) -> Tuple[int, int, Dict[str, Any]]:
        """Process POs using sequential processing with real downloads (single WebDriver)."""
        from corelib.browser import BrowserManager
        from EXPERIMENTAL.corelib.po_processing import process_single_po

        successful = 0
        failed = 0
        results: List[Dict[str, Any]] = []

        browser_manager = BrowserManager()
        driver = None
    # Folder manager usage is encapsulated inside process_single_po

        try:
            # Initialize a single browser instance for all POs
            browser_manager.initialize_driver(headless=self.headless_config.get_effective_headless_mode())
            driver = browser_manager.driver

            for i, po in enumerate(po_list):
                po_number = po.get('po_number', '')
                display_po = po_number
                folder_path = ''
                try:
                    # Progress bookkeeping
                    self.completed_tasks = i  # completed so far
                    self.active_tasks = 1
                    self._update_progress()

                    # Process single PO using shared utility
                    result_entry = process_single_po(
                        po_number=po_number,
                        po_data=po,
                        driver=driver,
                        browser_manager=browser_manager,
                        hierarchy_columns=self.hierarchy_columns or [],
                        has_hierarchy_data=bool(self.has_hierarchy_data),
                    )
                    results.append(result_entry)

                    if result_entry['success']:
                        successful += 1
                    else:
                        failed += 1

                except Exception as e:
                    # On error, mark failed and continue
                    results.append({
                        'po_number': po_number,
                        'po_number_display': display_po or po_number,
                        'status_code': 'FAILED',
                        'message': str(e),
                        'final_folder': '',
                        'errors': [{'filename': '', 'reason': str(e)}],
                        'success': False,
                        'attachment_names': [],
                        'attachments_found': 0,
                        'attachments_downloaded': 0,
                    })
                    failed += 1

                finally:
                    # Update per-item progress
                    self.completed_tasks = i + 1
                    self.active_tasks = 0
                    self._update_progress()

        finally:
            try:
                if driver is not None:
                    browser_manager.cleanup()
            except Exception:
                pass

        session_report = {
            'processing_mode': 'sequential',
            'worker_count': 1,
            'session_duration': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            'results': results,
        }

        self.last_results = results
        return successful, failed, session_report
    
    def _process_parallel_with_processpool(self, po_list: List[dict]) -> Tuple[int, int, Dict[str, Any]]:
        """Process POs using ProcessPoolExecutor when profiles are disabled."""
        successful = 0
        failed = 0
        results: List[Dict[str, Any]] = []
        
        # Use ProcessPoolExecutor similar to MainApp._process_po_entries
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
        # Calculate workers
        default_workers = min(2, len(po_list))
        proc_workers = max(1, min(self.max_workers, len(po_list)))
        print(f"📊 Using {proc_workers} ProcessPoolExecutor worker(s) (profiles disabled)")
        
        # Get download root for workers
        from corelib.config import Config
        download_root = os.path.abspath(os.path.expanduser(getattr(Config, 'DOWNLOAD_FOLDER', ExperimentalConfig.DOWNLOAD_FOLDER)))
        
        with ProcessPoolExecutor(max_workers=proc_workers, mp_context=mp.get_context("spawn")) as executor:
            future_map: dict = {}
            
            # Convert po_list to expected format and submit tasks
            for po_data in po_list:
                # Determine CSV path for worker (ProcessingSession doesn't have direct CSV handler access)
                csv_path = None
                # Try to get CSV path from environment or current working directory
                try:
                    if hasattr(self, 'csv_path') and self.csv_path:
                        csv_path = str(self.csv_path)
                except:
                    pass
                
                # Ensure po_data has the right format for process_po_worker
                task_args = (
                    po_data, 
                    self.hierarchy_columns or [], 
                    bool(self.has_hierarchy_data), 
                    self.headless_config,
                    download_root,
                    csv_path
                )
                
                future = executor.submit(process_po_worker, task_args)
                future_map[future] = po_data
                
                # Update progress
                self.total_tasks = len(po_list)
                self._update_progress()
            
            # Collect results
            for future in as_completed(future_map):
                po_data = future_map[future]
                po_number = po_data.get('po_number', '')
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result.get('success', False) or result.get('status_code') in {'COMPLETED', 'NO_ATTACHMENTS'}:
                        successful += 1
                    else:
                        failed += 1
                        
                except Exception as exc:
                    # Handle worker exceptions
                    error_result = {
                        'po_number': po_number,
                        'po_number_display': po_number,
                        'status_code': 'FAILED',
                        'message': str(exc),
                        'final_folder': '',
                        'errors': [{'filename': '', 'reason': str(exc)}],
                        'success': False,
                        'attachment_names': [],
                        'attachments_found': 0,
                        'attachments_downloaded': 0,
                    }
                    results.append(error_result)
                    failed += 1
                
                # Update progress after each completion
                self.completed_tasks = successful + failed
                self._update_progress()
        
        # Create session report
        session_report = {
            'processing_mode': 'parallel_processpool',
            'worker_count': proc_workers,
            'session_duration': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            'results': results,
        }
        
        self.last_results = results
        return successful, failed, session_report
    
    def _monitor_parallel_progress(self):
        """Monitor progress of parallel processing."""
        while self.status == SessionStatus.RUNNING and self.worker_pool:
            try:
                status = self.worker_pool.get_status()
                
                self.completed_tasks = status.get('completed_tasks', 0)
                self.failed_tasks = status.get('failed_tasks', 0)
                # For active tasks, we can use task_queue processing_tasks
                queue_stats = status.get('task_queue', {})
                self.active_tasks = queue_stats.get('processing_tasks', 0)
                
                self._update_progress()
                
                # Check if processing is complete
                total_processed = self.completed_tasks + self.failed_tasks
                if total_processed >= self.total_tasks:
                    break
                
                time.sleep(1)  # Update every second
                
            except Exception as e:
                print(f"Error monitoring progress: {e}")
                break
    
    def _update_progress(self):
        """Update progress via callback if configured."""
        if self.progress_callback:
            try:
                progress = self.get_progress()
                self.progress_callback(progress)
            except Exception as e:
                print(f"Error in progress callback: {e}")
    
    def _check_system_resources(self) -> bool:
        """Check if system has adequate resources for parallel processing."""
        # Simplified resource check
        try:
            cpu_count = mp.cpu_count()
            # Use parallel processing if we have enough CPU cores
            return cpu_count >= 2
        except:
            return False


def main() -> None:
    """Run the experimental UI workflow."""
    try:
        configured_workers = int(ExperimentalConfig.MAX_PARALLEL_WORKERS)
    except (TypeError, ValueError):
        configured_workers = 4
    max_workers = max(1, min(8, configured_workers))

    app = MainApp(enable_parallel=True, max_workers=max_workers)
    try:
        app.run()
    finally:
        app.close()


if __name__ == "__main__":
    main()
