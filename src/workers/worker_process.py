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
from ..core.utils import (
    _has_active_downloads,
    _wait_for_downloads_complete,
    _derive_status_label,
    _parse_counts_from_message
)
from ..core.protocols import StorageManager, Messenger
from ..core.output import maybe_print as print

# Centralized config for URLs
try:
    from ..lib.config import Config as _ExperimentalConfig  # type: ignore
    BASE_URL: str = getattr(_ExperimentalConfig, "BASE_URL", "https://unilever.coupahost.com")
except Exception:
    BASE_URL = "https://unilever.coupahost.com"

logger = structlog.get_logger(__name__)


_DOWNLOAD_SUFFIXES = ('.crdownload', '.tmp', '.partial')


# Helper functions moved to core/utils.py


# Debug logging helper
def _debug_log(msg: str):
    try:
        with open('/tmp/worker_debug.log', 'a') as f:
            import datetime
            ts = datetime.datetime.now().isoformat()
            f.write(f"[{ts}] {msg}\n")
    except:
        pass

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
        storage_manager: Optional[StorageManager] = None,
        messenger: Optional[Messenger] = None,
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
        self.storage_manager = storage_manager
        self.messenger = messenger
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
        """Initialize persistent browser session based on execution mode."""
        try:
            logger.debug("Initializing browser session", worker_id=self.worker_id)
            
            # Configure urllib3 connection pools BEFORE any HTTP operations
            # This prevents "Connection pool is full" errors during multiprocessing
            self._configure_connection_pools()
            
            # Create browser session
            self.browser_session = BrowserSession()
            
            # Determine initialization path based on execution_mode
            execution_mode = getattr(self.config, 'execution_mode', 'standard')
            mode_str = execution_mode.value if hasattr(execution_mode, 'value') else str(execution_mode)
            
            _debug_log(f"Worker {self.worker_id} initializing. Config mode: {execution_mode} -> Str: {mode_str}")
            print(f"DEBUG: Worker {self.worker_id} initializing with mode: {mode_str} (Raw: {execution_mode})", flush=True)
            logger.info(
                "WorkerProcess browser init",
                worker_id=self.worker_id,
                execution_mode=mode_str,
            )
            
            # Use Playwright for filtered and no_js modes (resource blocking)
            if mode_str in ("filtered", "no_js"):
                _debug_log(f"Worker {self.worker_id} selecting Playwright session")
                print(f"DEBUG: Worker {self.worker_id} selecting Playwright session", flush=True)
                self._initialize_playwright_session(mode_str)
                return
            
            _debug_log(f"Worker {self.worker_id} selecting Selenium session")
            print(f"DEBUG: Worker {self.worker_id} selecting Selenium session", flush=True)
            # Otherwise, use Selenium with Edge WebDriver (standard mode)
            self._initialize_selenium_session()
            
        except Exception as e:
            logger.error("Failed to initialize browser session", 
                        worker_id=self.worker_id, error=str(e))
            raise
    
    def _initialize_playwright_session(self, mode: str) -> None:
        """Initialize Playwright session with resource blocking for filtered/no_js modes."""
        from ..lib.playwright_manager import PlaywrightManager
        
        normalized_dl = self._apply_download_root_override()
        
        logger.info(
            "⚡ Initializing Playwright session for worker",
            worker_id=self.worker_id,
            mode=mode,
            download_folder=normalized_dl,
        )
        
        # Create PlaywrightManager instance
        pw_manager = PlaywrightManager()
        
        # Start Playwright with Edge channel and profile
        playwright_page = pw_manager.start(
            headless=self.config.headless_mode,
            execution_mode=mode,
            profile_dir=self.profile.worker_profile_path,
        )
        
        # Store Playwright manager and page in browser session for later use
        self.browser_session._playwright_manager = pw_manager
        self.browser_session._playwright_page = playwright_page
        self.browser_session._using_playwright = True
        
        # For Playwright, we don't have a Selenium driver but need to maintain compatibility
        # The browser_session should handle both cases
        self.browser_session.driver = None  # No Selenium driver in this mode
        self.browser_session.main_window_handle = None
        self.browser_session.keeper_handle = None
        
        logger.info(
            "Playwright session initialized for worker",
            worker_id=self.worker_id,
            mode=mode,
        )
        
        # Playwright sessions are pre-authenticated via Edge profile
        # Verify we can access Coupa
        try:
            test_url = f"{BASE_URL}/purchase_orders"
            playwright_page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
            current_url = playwright_page.url
            
            if "login" in current_url.lower() or "okta" in current_url.lower():
                raise RuntimeError("Playwright session not authenticated - login page detected")
            
            logger.info("Playwright session authenticated", worker_id=self.worker_id)
        except Exception as auth_err:
            logger.error("Playwright authentication check failed", worker_id=self.worker_id, error=str(auth_err))
            raise RuntimeError(f"Playwright authentication failed: {auth_err}")
    
    def _initialize_selenium_session(self) -> None:
        """Initialize Selenium session with Edge WebDriver for standard mode."""
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
        _debug_log(f"Worker {self.worker_id} using driver at: {driver_path}")
        
        # Verify driver before start
        if not dm.verify_driver(driver_path):
            msg = f"Worker {self.worker_id}: EdgeDriver verification failed for {driver_path}"
            _debug_log(f"❌ {msg}")
            raise RuntimeError(msg)
        _debug_log(f"✅ Worker {self.worker_id}: EdgeDriver verified")
        
        # Create service with minimal configuration to avoid conflicts
        service = Service(
            executable_path=driver_path,
            # Remove log suppression to see potential errors
            # service_args=["--verbose", "--log-level=DEBUG"]  # Commented out to reduce noise
        )

        # Add delay to prevent simultaneous driver starts
        import time
        init_delay = 2 + (abs(hash(self.worker_id)) % 3) # Jittered delay
        _debug_log(f"Worker {self.worker_id} delaying start by {init_delay}s...")
        time.sleep(init_delay)
        
        try:
            _debug_log(f"Worker {self.worker_id} spawning Edge process...")
            driver = webdriver.Edge(service=service, options=edge_options)
            _debug_log(f"✅ Worker {self.worker_id} Edge process spawned successfully")
        except Exception as e:
            _debug_log(f"❌ Worker {self.worker_id} failed to spawn Edge: {str(e)}")
            raise
        
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
        self.browser_session._using_playwright = False
        
        logger.info(
            "Edge WebDriver started",
            worker_id=self.worker_id,
            profile_path=self.profile.worker_profile_path,
            headless=self.config.headless_mode,
        )
        self.browser_session.ensure_keeper_tab()

        # Authenticate with Coupa
        _debug_log(f"Worker {self.worker_id} starting authentication...")
        success = self.browser_session.authenticate()
        
        if not success:
            _debug_log(f"❌ Worker {self.worker_id} failed to authenticate with Coupa")
            raise RuntimeError("Failed to authenticate with Coupa")
        
        _debug_log(f"✅ Worker {self.worker_id} authentication successful")
        
        logger.debug("Browser session initialized", worker_id=self.worker_id)

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
            except Exception as e:
                logger.warning(
                    "Failed to get download folder from config (attempt 1)",
                    worker_id=self.worker_id,
                    error=str(e)
                )
                try:
                    from ..lib.config import Config as _Cfg  # type: ignore
                    target = getattr(_Cfg, 'DOWNLOAD_FOLDER', None)
                except Exception as e2:
                    logger.warning(
                        "Failed to get download folder from config (attempt 2)",
                        worker_id=self.worker_id,
                        error=str(e2)
                    )
                    # Will use default fallback
        
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
            logger.debug("Updated lib.Config.DOWNLOAD_FOLDER", worker_id=self.worker_id, path=normalized)
        except Exception as e:
            logger.warning("Failed to update lib.Config", worker_id=self.worker_id, error=str(e))

        # Also try to update any config objects that might be cached
        try:
            from ..lib import config as experimental_config
            experimental_config._settings.DOWNLOAD_FOLDER = normalized  # type: ignore[attr-defined]
        except Exception as e:
            logger.debug(
                "Failed to update config _settings (non-critical)",
                worker_id=self.worker_id,
                error=str(e)
            )

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

            # Emit STARTED metric for immediate UI update
            if self.messenger:
                try:
                    po_number = task.po_number or task.metadata.get('po_number')
                    self.messenger.send_metric({
                        'worker_id': self.worker_id,
                        'task_id': task.task_id,
                        'po_id': po_number,
                        'status': 'STARTED',
                        'timestamp': time.time(),
                        'attachments_found': 0,
                        'attachments_downloaded': 0,
                        'message': f"Started PO {po_number}" if po_number else "Started PO",
                    })
                except Exception:
                    pass
            
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
                
                # Send COMPLETED metric with updated stats
                if self.messenger:
                    try:
                        po_number = task.po_number or task.metadata.get('po_number')
                        self.messenger.send_metric({
                            'worker_id': self.worker_id,
                            'task_id': task.task_id,
                            'po_id': po_number,
                            'status': 'COMPLETED',
                            'timestamp': time.time(),
                            'attachments_found': result.get('attachments_found', 0),
                            'attachments_downloaded': result.get('attachments_downloaded', 0),
                            'tasks_processed': self.tasks_processed,
                            'tasks_failed': self.tasks_failed,
                            'efficiency_score': (self.tasks_processed / max(1, self.tasks_processed + self.tasks_failed)) * 100,
                            'message': f"Completed {po_number}",
                        })
                    except Exception:
                        pass
            else:
                self.tasks_failed += 1
                self.worker.complete_task(success=False)
                logger.warning("Task failed",
                              worker_id=self.worker_id,
                              po_number=task.po_number,
                              error=result.get('error'))
                
                # Send FAILED metric with updated stats
                if self.messenger:
                    try:
                        po_number = task.po_number or task.metadata.get('po_number')
                        self.messenger.send_metric({
                            'worker_id': self.worker_id,
                            'task_id': task.task_id,
                            'po_id': po_number,
                            'status': 'FAILED',
                            'timestamp': time.time(),
                            'tasks_processed': self.tasks_processed,
                            'tasks_failed': self.tasks_failed,
                            'efficiency_score': (self.tasks_processed / max(1, self.tasks_processed + self.tasks_failed)) * 100,
                            'message': f"Failed {po_number}: {result.get('error', 'Unknown error')}",
                        })
                    except Exception:
                        pass
            
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
        if not self.browser_session:
            return {
                'success': False,
                'error': 'Browser session not initialized',
                'task_id': task.task_id,
                'status_code': 'FAILED',
            }
            
        po_number = task.po_number
        po_data = dict(task.metadata or {})
        display_po = po_data.get('po_number', po_number)
        hierarchy_cols = self.config.hierarchy_columns or []
        has_hierarchy = bool(self.config.has_hierarchy_data)

        # Handle Playwright Session
        if getattr(self.browser_session, '_using_playwright', False):
            try:
                manager = self.browser_session._playwright_manager
                if not manager:
                    raise RuntimeError("Playwright manager not available in session")
                
                logger.info("Delegating PO processing to Playwright", worker_id=self.worker_id, po=po_number)
                result = manager.process_po(
                    po_number=po_number,
                    po_data=po_data,
                    hierarchy_cols=hierarchy_cols,
                    has_hierarchy=has_hierarchy
                )
                
                # Add task metadata
                result['task_id'] = task.task_id
                result['processing_time'] = task.get_processing_time()
                return result
                
            except Exception as e:
                logger.error("Playwright processing failed", worker_id=self.worker_id, error=str(e))
                return {
                    'success': False,
                    'error': str(e),
                    'task_id': task.task_id,
                    'po_number': po_number,
                    'status_code': 'FAILED',
                }

        # Fallback to Selenium (Standard Mode)
        if not self.browser_session.driver:
            return {
                'success': False,
                'error': 'Browser session driver not available',
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

            def progress_bridge(progress_data: Dict[str, Any]):
                if self.messenger:
                    metric = {
                        'worker_id': self.worker_id,
                        'task_id': task.task_id,
                        'po_id': po_number,
                        'status': f"Downloading {progress_data.get('attachments_downloaded', 0)}/{progress_data.get('attachments_found', 0)}",
                        'attachments_found': progress_data.get('attachments_found', 0),
                        'attachments_downloaded': progress_data.get('attachments_downloaded', 0),
                        'message': progress_data.get('message', ''),
                        'timestamp': time.time(),
                        'tasks_processed': self.tasks_processed,
                        'tasks_failed': self.tasks_failed,
                    }
                    self.messenger.send_metric(metric)

            # Check if batch finalization is enabled in experimental config
            skip_finalization = False
            try:
                from ..lib.config import Config
                skip_finalization = getattr(Config, 'BATCH_FINALIZATION_ENABLED', False)
            except Exception:
                pass

            result_entry = process_single_po(
                po_number=po_number,
                po_data=po_data,
                driver=driver,
                browser_manager=browser_manager,
                hierarchy_columns=hierarchy_cols,
                has_hierarchy_data=has_hierarchy,
                progress_callback=progress_bridge,
                skip_finalization=skip_finalization
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
            if not self.browser_session:
                return

            # Handle Playwright Cleanup
            if getattr(self.browser_session, '_using_playwright', False):
                try:
                    logger.debug("Cleaning up Playwright session", worker_id=self.worker_id)
                    manager = getattr(self.browser_session, '_playwright_manager', None)
                    if manager:
                        manager.cleanup()
                    self.browser_session = None
                    logger.debug("Playwright session cleaned up", worker_id=self.worker_id)
                except Exception as pw_err:
                    logger.error("Failed to cleanup Playwright session", worker_id=self.worker_id, error=str(pw_err))
                return

            if not self.browser_session.driver:
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
                logger.debug("Attempting driver quit with timeout", worker_id=self.worker_id)
                # Use a separate thread and event to avoid hanging forever on driver.quit()
                def quit_driver():
                    try:
                        driver.quit()
                    except Exception as e:
                        logger.debug("driver.quit() exception", worker_id=self.worker_id, error=str(e))

                quit_thread = threading.Thread(target=quit_driver, daemon=True)
                quit_thread.start()
                quit_thread.join(timeout=10 if not emergency else 3)
                
                if quit_thread.is_alive():
                     logger.warning("driver.quit() timed out", worker_id=self.worker_id)
                else:
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
