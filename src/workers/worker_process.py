"""
WorkerProcess for individual worker lifecycle management.

This module provides the WorkerProcess class for managing individual
worker processes with support for:
- Browser session management
- Task processing coordination
- Health monitoring and recovery
- Resource cleanup
"""

import datetime
import os
import queue
import subprocess
import threading
import time
from typing import Dict, Any, Optional, Callable

import structlog
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
import requests
from requests.adapters import HTTPAdapter

# Configure urllib3 connection pools globally to prevent "connection pool full" errors
# import urllib3
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# # Increase default connection pool sizes to handle multiprocessing communication
# urllib3.util.connection.HAS_IPV6 = False  # Disable IPv6 to reduce connection issues

# # Monkey patch urllib3 to use larger default pool sizes for all connections
# import urllib3.connectionpool
# original_init = urllib3.connectionpool.HTTPConnectionPool.__init__

# def patched_init(self, host, port=None, strict=False, timeout=urllib3.util.timeout.Timeout.DEFAULT_TIMEOUT, maxsize=10, block=False, headers=None, retries=None, _proxy=None, _proxy_headers=None, **conn_kw):
#     # Force larger pool sizes, especially for localhost
#     if host in ('localhost', '127.0.0.1'):
#         maxsize = max(maxsize, 20)  # Larger pools for localhost
#     else:
#         maxsize = max(maxsize, 10)  # Normal pools for external hosts
#     return original_init(self, host, port, strict, timeout, maxsize, block, headers, retries, _proxy, _proxy_headers, **conn_kw)

# urllib3.connectionpool.HTTPConnectionPool.__init__ = patched_init

import datetime
import os
import queue
import threading
import time
from typing import Dict, Any, Optional, Callable

import structlog
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
import requests
from requests.adapters import HTTPAdapter

from .models import Worker, Profile, POTask, PoolConfig, WorkerStatus
from .browser_session import BrowserSession

from ..lib.browser import BrowserManager
from ..lib.downloader import Downloader
from ..lib.folder_hierarchy import FolderHierarchyManager
from ..lib.po_processing import process_single_po  # shared utility
from ..lib.driver_manager import DriverManager

# Centralized config for URLs
try:
    from ..lib.config import Config as _ExperimentalConfig  # type: ignore
    BASE_URL: str = getattr(_ExperimentalConfig, "BASE_URL", "https://unilever.coupahost.com")
except Exception:
    BASE_URL = "https://unilever.coupahost.com"

logger = structlog.get_logger(__name__)


_DOWNLOAD_SUFFIXES = ('.crdownload', '.tmp', '.partial')


def _has_active_downloads(folder_path: str) -> bool:
    try:
        names = os.listdir(folder_path)
    except Exception:
        return False
    return any(name.endswith(_DOWNLOAD_SUFFIXES) for name in names)


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


def _suffix_for_status(status_code: str) -> str:
    mapping = {
        'COMPLETED': '_COMPLETED',
        'FAILED': '_FAILED',
        'NO_ATTACHMENTS': '_NO_ATTACHMENTS',
        'PARTIAL': '_PARTIAL',
        'PO_NOT_FOUND': '_PO_NOT_FOUND',
    }
    return mapping.get(status_code, f'_{status_code}')


def _rename_folder_with_status(folder_path: str, status_code: str) -> str:
    """Rename folder with status, ensuring __WORK is removed first."""
    try:
        import re
        base_dir = os.path.dirname(folder_path)
        base_name = os.path.basename(folder_path)
        status_upper = (status_code or '').upper().strip() or 'FAILED'
        
        # Remove any __WORK sequences first
        base_name = re.sub(r'(?:__WORK)+', '', base_name)
        base_name = re.sub(r'_+', '_', base_name).strip('_')
        
        # Remove existing status suffixes if changing
        known_suffixes = ['_COMPLETED', '_FAILED', '_NO_ATTACHMENTS', '_PARTIAL', '_PO_NOT_FOUND', '_TIMEOUT']
        upper_name = base_name.upper()
        
        for suf in known_suffixes:
            if upper_name.endswith(suf) and suf != f'_{status_upper}':
                base_name = base_name[:-len(suf)].rstrip('_')
                break
        
        # Add status suffix if not already present
        if not base_name.upper().endswith(f'_{status_upper}'):
            target = f"{base_name}_{status_upper}"
        else:
            target = base_name
            
        # Final cleanup
        target = re.sub(r'_+', '_', target).rstrip('_')
        
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


def _parse_counts_from_message(message: str) -> tuple[Optional[int], Optional[int]]:
    if not message:
        return None, None
    import re

    match = re.search(r"(\d+)\s*/\s*(\d+)", message)
    if not match:
        return None, None
    try:
        return int(match.group(1)), int(match.group(2))
    except Exception:
        return None, None


def _derive_status_label(result: Dict[str, Any]) -> str:
    if not result:
        return 'FAILED'

    if 'status_code' in result and result['status_code']:
        return result['status_code']

    success = result.get('success', False)
    message = result.get('message', '') or ''
    msg_lower = message.lower()
    downloaded, total = _parse_counts_from_message(message)

    if success:
        if total == 0 or 'no attachments' in msg_lower:
            return 'NO_ATTACHMENTS'
        if downloaded is not None and total is not None and downloaded < total:
            return 'PARTIAL'
        return 'COMPLETED'

    if 'oops' in msg_lower or 'not found' in msg_lower:
        return 'PO_NOT_FOUND'

    return 'FAILED'


class WorkerProcess:
    """
    Individual worker process for PO processing.
    
    Manages a persistent browser session and processes assigned tasks
    with health monitoring and error recovery.
    """
    
    def __init__(
        self,
        worker_id: str,
        profile: Profile,
        config: PoolConfig,
        csv_handler: Optional[Any] = None,
        result_callback: Optional[Callable[[POTask, Dict[str, Any]], None]] = None,
    ):
        """
        Initialize worker process.
        
        Args:
            worker_id: Unique identifier for this worker
            profile: Browser profile for isolation
            config: Pool configuration
        """
        self.worker_id = worker_id
        self.profile = profile
        self.config = config
        self.csv_handler = csv_handler
        self._result_callback = result_callback
        
        # Create worker model
        self.worker = Worker(
            worker_id=worker_id,
            profile_path=profile.worker_profile_path
        )
        
        # Browser session management
        self.browser_session: Optional[BrowserSession] = None
        
        # HTTP session for controlled connection pooling
        self._http_session: Optional[requests.Session] = None
        
        # urllib3 pool manager for multiprocessing communication
        self._pool_manager: Optional[Any] = None
        
        # Task processing
        self.current_task: Optional[POTask] = None
        self.task_queue = queue.Queue()
        
        # State management
        self._stop_event = threading.Event()
        self._running = False
        self._last_heartbeat = time.time()
        
        # Statistics
        self.start_time: Optional[float] = None
        self.tasks_processed = 0
        self.tasks_failed = 0
        
        logger.debug("WorkerProcess initialized", worker_id=worker_id)
    
    def start(self) -> None:
        """
        Start the worker process.
        
        Initializes browser session and begins task processing.
        
        Raises:
            RuntimeError: If worker is already running or startup fails
        """
        if self._running:
            raise RuntimeError(f"Worker {self.worker_id} is already running")
        
        try:
            logger.info("Starting worker process", worker_id=self.worker_id)
            self.start_time = time.time()
            self._running = True
            
            # Update worker status
            self.worker.status = WorkerStatus.STARTING
            
            # Initialize browser session
            self._initialize_browser_session()
            
            # Mark worker as ready
            self.worker.status = WorkerStatus.READY
            
            logger.info("Worker process started successfully", 
                       worker_id=self.worker_id)
            
        except Exception as e:
            self._running = False
            self.worker.status = WorkerStatus.CRASHED
            self.worker.last_error = f"Startup failed: {str(e)}"
            logger.error("Failed to start worker process", 
                        worker_id=self.worker_id, error=str(e))
            raise RuntimeError(f"Worker startup failed: {e}") from e
    
    def _initialize_browser_session(self) -> None:
        """Initialize persistent browser session."""
        try:
            logger.debug("Initializing browser session", worker_id=self.worker_id)
            
            # Configure urllib3 connection pools BEFORE any HTTP operations
            # This prevents "Connection pool is full" errors during multiprocessing
            self._configure_connection_pools()
            
            # Create browser session
            self.browser_session = BrowserSession()

            # Setup Edge options
            edge_options = Options()

            if self.config.headless_mode:
                edge_options.add_argument("--headless")
            
            # Profile configuration
            if self.profile.worker_profile_path:
                edge_options.add_argument(f"--user-data-dir={self.profile.worker_profile_path}")
                edge_options.add_argument(f"--profile-directory={self.profile.profile_name}")

            # Basic options only
            edge_options.add_argument("--no-sandbox")
            edge_options.add_argument("--disable-dev-shm-usage")
            edge_options.add_argument("--window-size=1920,1080")

            # Configure download preferences to use timestamped folder
            normalized_dl = self._apply_download_root_override()
            download_prefs = {
                "download.default_directory": normalized_dl,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            edge_options.add_experimental_option("prefs", download_prefs)
            logger.info("Worker download folder configured", worker_id=self.worker_id, download_folder=normalized_dl)

            # Create WebDriver - SIMPLIFIED CONFIGURATION
            dm = DriverManager()
            driver_path = dm.get_driver_path()
            
            # Create service with minimal configuration to avoid conflicts
            service = Service(
                executable_path=driver_path,
                # Remove log suppression to see potential errors
                # service_args=["--verbose", "--log-level=DEBUG"]  # Commented out to reduce noise
            )

            # Add delay to prevent simultaneous driver starts
            import time
            time.sleep(2)  # 2 second delay between driver initializations
            
            driver = webdriver.Edge(service=service, options=edge_options)
            
            # Force-set download directory via DevTools to override any profile defaults
            try:
                driver.execute_cdp_cmd(
                    "Page.setDownloadBehavior",
                    {"behavior": "allow", "downloadPath": normalized_dl}
                )
                logger.debug("CDP download directory set", worker_id=self.worker_id, download_folder=normalized_dl)
            except Exception as cdp_err:
                logger.warning("Failed to set CDP download directory", worker_id=self.worker_id, error=str(cdp_err))

            # Initialize browser session
            self.browser_session.driver = driver
            self.browser_session.main_window_handle = driver.current_window_handle
            self.browser_session.keeper_handle = driver.current_window_handle
            logger.info(
                "Edge WebDriver started",
                worker_id=self.worker_id,
                profile_path=self.profile.worker_profile_path,
                headless=self.config.headless_mode,
            )
            self.browser_session.ensure_keeper_tab()

            # Authenticate with Coupa
            success = self.browser_session.authenticate()
            
            if not success:
                raise RuntimeError("Failed to authenticate with Coupa")
            
            logger.debug("Browser session initialized", worker_id=self.worker_id)
            
        except Exception as e:
            logger.error("Failed to initialize browser session", 
                        worker_id=self.worker_id, error=str(e))
            raise

    def _configure_connection_pools(self) -> None:
        """Configure urllib3 connection pools to prevent multiprocessing issues."""
        try:
            import urllib3
            from urllib3.util import connection
            
            # Monkey patch urllib3 to use larger default pool sizes globally
            # This prevents "Connection pool is full" errors during multiprocessing
            original_init = urllib3.connectionpool.HTTPConnectionPool.__init__
            
            def patched_init(self, host, port=None, timeout=urllib3.util.timeout.Timeout.DEFAULT_TIMEOUT, maxsize=1, block=False, headers=None, retries=None, _proxy=None, _proxy_headers=None, _proxy_config=None, **conn_kw):
                # Force larger pool sizes, especially for localhost
                if host in ('localhost', '127.0.0.1'):
                    maxsize = max(maxsize, 20)  # Larger pools for localhost/multiprocessing
                else:
                    maxsize = max(maxsize, 10)  # Normal pools for external connections
                return original_init(self, host, port, timeout, maxsize, block, headers, retries, _proxy, _proxy_headers, _proxy_config, **conn_kw)
            
            urllib3.connectionpool.HTTPConnectionPool.__init__ = patched_init
            
            # Create a custom connection pool manager with larger pools
            http = urllib3.PoolManager(
                num_pools=20,  # Increased from 10
                maxsize=20,    # Increased from 10
                retries=urllib3.Retry(total=3, backoff_factor=0.3)
            )
            
            # Store the pool manager for potential use
            self._pool_manager = http
            
            logger.debug("Connection pools configured for multiprocessing", worker_id=self.worker_id)
            
        except Exception as e:
            logger.warning("Failed to configure connection pools", worker_id=self.worker_id, error=str(e))

    def _apply_download_root_override(self) -> str:
        """Ensure Config and environment use the configured download root."""
        # Always use the timestamped download root from PoolConfig first
        target = self.config.download_root
        if not target:
            # Fallback to environment variable
            target = os.environ.get('DOWNLOAD_FOLDER')
        
        # If still no target, get from ..config with timestamp preservation
        if not target:
            try:
                from ..lib.config import Config as _Cfg
                target = getattr(_Cfg, 'DOWNLOAD_FOLDER', None)
            except Exception:
                try:
                    from ..lib.config import Config as _Cfg  # type: ignore
                    target = getattr(_Cfg, 'DOWNLOAD_FOLDER', None)
                except Exception:
                    pass
        
        # Final fallback to default (but this should not happen with proper config)
        if not target:
            target = os.path.join(os.path.expanduser('~'), 'Downloads', 'CoupaDownloads')

        normalized = os.path.abspath(os.path.expanduser(target))
        
        # Set environment variable for downstream processes
        os.environ['DOWNLOAD_FOLDER'] = normalized

        # Update all config facades so that FolderHierarchyManager sees the right path
        try:
            from ..lib import config as experimental_config
            experimental_config.Config.DOWNLOAD_FOLDER = normalized  # type: ignore[attr-defined]
            logger.debug("Updated EXPERIMENTAL.corelib.Config.DOWNLOAD_FOLDER", worker_id=self.worker_id, path=normalized)
        except Exception as e:
            logger.warning("Failed to update EXPERIMENTAL.corelib.Config", worker_id=self.worker_id, error=str(e))

        try:
            import corelib.config as core_config  # type: ignore
            core_config.Config.DOWNLOAD_FOLDER = normalized  # type: ignore[attr-defined]
            logger.debug("Updated corelib.Config.DOWNLOAD_FOLDER", worker_id=self.worker_id, path=normalized)
        except Exception as e:
            logger.warning("Failed to update corelib.Config", worker_id=self.worker_id, error=str(e))

        # Also try to update any config objects that might be cached
        try:
            from ..lib import config as experimental_config
            experimental_config._settings.DOWNLOAD_FOLDER = normalized  # type: ignore[attr-defined]
        except Exception:
            pass

        try:
            os.makedirs(normalized, exist_ok=True)
            logger.debug("Created download directory", worker_id=self.worker_id, download_folder=normalized)
        except Exception as create_err:
            logger.warning("Failed to create download directory", worker_id=self.worker_id, download_folder=normalized, error=str(create_err))

        return normalized
    
    def process_task(self, task: POTask) -> Dict[str, Any]:
        """
        Process a single PO task.
        
        Args:
            task: POTask to process
            
        Returns:
            Dictionary containing task result
        """
        if not self._running or not self.browser_session:
            return {
                'success': False,
                'error': 'Worker not ready for task processing'
            }
        
        try:
            logger.debug("Processing task", worker_id=self.worker_id, 
                        po_number=task.po_number, task_id=task.task_id)
            
            # Update worker state
            self.current_task = task
            self.worker.assign_task(task)
            self._update_heartbeat()
            
            # Note: task assignment and processing start is already done by TaskQueue.get_next_task()
            # No need to duplicate the assignment here
            
            # Process the task using browser session
            result = self._process_po_task(task)

            if self._result_callback:
                try:
                    self._result_callback(task, result)
                except Exception as callback_error:  # pragma: no cover - defensive logging
                    logger.warning(
                        "Result callback execution failed",
                        worker_id=self.worker_id,
                        po_number=task.po_number,
                        error=str(callback_error),
                    )
            
            # Update statistics
            if result['success']:
                self.tasks_processed += 1
                self.worker.complete_task(success=True)
                logger.debug("Task completed successfully", 
                           worker_id=self.worker_id, po_number=task.po_number)
            else:
                self.tasks_failed += 1
                self.worker.complete_task(success=False)
                logger.warning("Task failed", 
                              worker_id=self.worker_id, 
                              po_number=task.po_number,
                              error=result.get('error'))
            
            self.current_task = None
            return result
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error processing task: {str(e)}"
            logger.error("Task processing error", 
                        worker_id=self.worker_id,
                        po_number=task.po_number,
                        error=error_msg)
            
            self.tasks_failed += 1
            self.worker.complete_task(success=False)
            self.current_task = None
            
            return {
                'success': False,
                'error': error_msg,
                'task_id': task.task_id
            }
    
    def _process_po_task(self, task: POTask) -> Dict[str, Any]:
        """Process a single PO using the worker's persistent browser session."""
        if not self.browser_session or not self.browser_session.driver:
            return {
                'success': False,
                'error': 'Browser session not available',
                'task_id': task.task_id,
                'status_code': 'FAILED',
            }

        driver = self.browser_session.driver
        
        # Validate WebDriver health before processing
        if not self._validate_webdriver_health(driver):
            return {
                'success': False,
                'error': 'WebDriver session is not healthy',
                'task_id': task.task_id,
                'status_code': 'FAILED',
            }
        
        po_number = task.po_number
        po_data = dict(task.metadata or {})
        display_po = po_data.get('po_number', po_number)
        hierarchy_cols = self.config.hierarchy_columns or []
        has_hierarchy = bool(self.config.has_hierarchy_data)

        browser_manager = BrowserManager()
        browser_manager.driver = driver

        tab_handle = None
        try:
            self.browser_session.ensure_keeper_tab()
            self.browser_session.focus_main_window()

            tab_handle = self.browser_session.create_tab(task.task_id)
            
            # Assign PO number to tab after creation
            if task.task_id in self.browser_session.active_tabs:
                tab = self.browser_session.active_tabs[task.task_id]
                tab.assign_po(po_number)
            
            driver.switch_to.window(tab_handle)

            result_entry = process_single_po(
                po_number=po_number,
                po_data=po_data,
                driver=driver,
                browser_manager=browser_manager,
                hierarchy_columns=hierarchy_cols,
                has_hierarchy_data=has_hierarchy,
            )

            # attach processing timing and task id
            result_entry['task_id'] = task.task_id
            result_entry['processing_time'] = task.get_processing_time()

            return result_entry

        except Exception as e:
            friendly = str(e)
            lower_msg = friendly.lower()
            status_code = 'FAILED'
            if 'read timed out' in lower_msg or 'read timeout' in lower_msg or 'timeout' in lower_msg:
                status_code = 'TIMEOUT'
            # Folder path is managed inside process_single_po; on exception we may not have it
            failed_folder = ''

            return {
                'success': False,
                'error': friendly,
                'task_id': task.task_id,
                'po_number': po_number,
                'po_number_display': display_po,
                'status_code': status_code,
                'message': friendly,
                'final_folder': failed_folder,
                'errors': [{'filename': '', 'reason': friendly}],
                'processing_time': task.get_processing_time(),
                'transient': True if status_code == 'TIMEOUT' else False,
            }

        finally:
            try:
                if tab_handle:
                    self.browser_session.close_tab(tab_handle)
            except Exception as close_err:
                logger.warning("Failed to close worker tab", worker_id=self.worker_id, error=str(close_err))
            self.browser_session.focus_main_window()
    
    def stop(self) -> None:
        """Stop the worker process gracefully."""
        if not self._running:
            return
        
        logger.info("Stopping worker process", worker_id=self.worker_id)
        
        # Signal stop
        self._stop_event.set()
        self._running = False
        
        # Update worker status
        self.worker.status = WorkerStatus.TERMINATING
        
        # Cleanup browser session
        self._cleanup_browser_session()
        
        logger.info("Worker process stopped", worker_id=self.worker_id)
    
    def force_stop(self) -> None:
        """Force stop the worker process immediately."""
        logger.warning("Force stopping worker process", worker_id=self.worker_id)
        
        self._stop_event.set()
        self._running = False
        
        # Force cleanup using the robust cleanup method with emergency flag
        try:
            self._cleanup_browser_session(emergency=True)
        except Exception as e:
             logger.debug("Force cleanup failed error during force_stop", error=str(e))
        
        self.worker.status = WorkerStatus.CRASHED
        self.worker.last_error = "Force stopped"
    
    def _cleanup_browser_session(self, emergency: bool = False) -> None:
        """Cleanup browser session and resources."""
        try:
            if not (self.browser_session and self.browser_session.driver):
                return

            driver = self.browser_session.driver
            logger.debug("Cleaning up browser session", worker_id=self.worker_id, emergency=emergency)

            # If emergency, skip state capture and window enumeration to save time and avoid hangs
            if emergency:
                handles = []
            else:
                # First, try to save current state for debugging
                try:
                    current_url = driver.current_url
                    title = driver.title
                    logger.debug("Browser state before cleanup", worker_id=self.worker_id, 
                               url=current_url, title=title)
                except Exception as state_err:
                    logger.debug("Could not capture browser state", worker_id=self.worker_id, error=str(state_err))

                # Defensive: collect handles snapshot early
                try:
                    handles = list(driver.window_handles)
                    logger.debug("Window handles before cleanup", worker_id=self.worker_id, handles=handles)
                except Exception as e:
                    logger.warning("Failed to enumerate window handles", worker_id=self.worker_id, error=str(e))
                    handles = []

            # Try graceful close of non-main windows with short timeout semantics
            for handle in handles:
                if handle == self.browser_session.main_window_handle:
                    continue
                try:
                    driver.switch_to.window(handle)
                    driver.close()
                    logger.debug("Closed tab", worker_id=self.worker_id, handle=handle)
                except Exception as tab_err:
                    logger.debug("Non-fatal tab close error", worker_id=self.worker_id, error=str(tab_err))
                    continue

            # Final attempt: switch to main and quit
            try:
                if self.browser_session.main_window_handle in getattr(driver, 'window_handles', []):
                    driver.switch_to.window(self.browser_session.main_window_handle)
                    logger.debug("Switched to main window", worker_id=self.worker_id)
            except Exception as switch_err:
                logger.debug("Failed to switch to main window before quit", worker_id=self.worker_id, error=str(switch_err))

            # Attempt quit; if it hangs Selenium may throw a timeout -> catch and force kill
            try:
                logger.debug("Attempting graceful driver quit", worker_id=self.worker_id)
                driver.quit()
                logger.debug("Driver quit successful", worker_id=self.worker_id)
            except Exception as quit_err:
                logger.warning("Graceful quit failed; forcing shutdown", worker_id=self.worker_id, error=str(quit_err))
                try:
                    # Force kill underlying process if accessible
                    service = getattr(driver, 'service', None)
                    proc = getattr(service, 'process', None) if service else None
                    if proc and hasattr(proc, 'terminate'):
                        proc.terminate()
                        logger.debug("Force terminated driver process", worker_id=self.worker_id)
                except Exception as force_err:
                    logger.debug("Force termination failed", worker_id=self.worker_id, error=str(force_err))
            finally:
                self.browser_session.driver = None
                self.browser_session = None
                logger.debug("Browser session cleanup completed", worker_id=self.worker_id)

        except Exception as e:
            logger.warning("Error during browser cleanup", worker_id=self.worker_id, error=str(e))
            # Ensure we don't leave dangling references
            try:
                if self.browser_session:
                    self.browser_session.driver = None
                    self.browser_session = None
            except:
                pass
    
    def should_stop(self) -> bool:
        """Check if worker should stop processing."""
        return self._stop_event.is_set() or not self._running
    
    def is_healthy(self) -> bool:
        """Check if worker is healthy and operational."""
        if not self._running:
            return False
        
        # Check heartbeat
        time_since_heartbeat = time.time() - self._last_heartbeat
        if time_since_heartbeat > 300:  # 5 minutes
            return False
        
        # Check browser session
        if not self.browser_session or not self.browser_session.driver:
            return False
        
        # Use comprehensive WebDriver health validation
        return self._validate_webdriver_health(self.browser_session.driver)
    
    def _update_heartbeat(self) -> None:
        """Update worker heartbeat timestamp."""
        self._last_heartbeat = time.time()
        self.worker.last_activity = datetime.datetime.now()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive worker status.
        
        Returns:
            Dictionary containing worker status and statistics
        """
        uptime = time.time() - (self.start_time or time.time()) if self.start_time else 0
        
        return {
            'worker_id': self.worker_id,
            'status': self.worker.status.value,
            'running': self._running,
            'healthy': self.is_healthy(),
            'uptime_seconds': uptime,
            'current_task': self.current_task.po_number if self.current_task else None,
            'tasks_processed': self.tasks_processed,
            'tasks_failed': self.tasks_failed,
            'last_heartbeat': self._last_heartbeat,
            'profile_path': self.profile.worker_profile_path,
            'browser_session_active': self.browser_session is not None,
            'worker_model': self.worker.to_dict()
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get worker performance statistics.
        
        Returns:
            Performance metrics dictionary
        """
        total_tasks = self.tasks_processed + self.tasks_failed
        success_rate = (self.tasks_processed / total_tasks * 100) if total_tasks > 0 else 0
        
        avg_processing_time = 0
        if self.tasks_processed > 0 and self.start_time:
            avg_processing_time = (time.time() - self.start_time) / self.tasks_processed
        
        return {
            'total_tasks': total_tasks,
            'successful_tasks': self.tasks_processed,
            'failed_tasks': self.tasks_failed,
            'success_rate_percent': round(success_rate, 2),
            'average_processing_time_seconds': round(avg_processing_time, 2),
            'uptime_hours': (time.time() - (self.start_time or time.time())) / 3600 if self.start_time else 0
        }
    
    def __str__(self) -> str:
        """String representation of worker process."""
        return f"WorkerProcess({self.worker_id}, {self.worker.status.value})"
    
    def __repr__(self) -> str:
        """Detailed representation of worker process."""
        return (f"WorkerProcess(worker_id='{self.worker_id}', "
                f"status={self.worker.status}, running={self._running}, "
                f"tasks_processed={self.tasks_processed})")
    
    def _validate_webdriver_health(self, driver) -> bool:
        """Validate that the WebDriver session is healthy and responsive."""
        try:
            # Test basic WebDriver connectivity
            current_url = driver.current_url
            window_handles = driver.window_handles
            
            # Ensure we have at least one window handle
            if not window_handles:
                logger.error("WebDriver has no window handles", worker_id=self.worker_id)
                return False
            
            # Test switching to current window (should not fail if healthy)
            driver.switch_to.window(driver.current_window_handle)
            
            # Additional health check: try to execute a simple script
            driver.execute_script("return 'health_check_ok';")
            
            logger.debug("WebDriver health check passed", worker_id=self.worker_id, 
                        url=current_url, windows=len(window_handles))
            return True
            
        except Exception as e:
            logger.error("WebDriver health check failed", worker_id=self.worker_id, error=str(e))
            return False
