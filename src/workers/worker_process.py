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
import threading
import time
from typing import Any, Callable, Dict, Optional

import requests
import structlog

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

from .models import Worker, Profile, POTask, PoolConfig, WorkerStatus
from .browser_session import BrowserSession
from .task_queue import ProcessingTask

from ..lib.browser import BrowserManager
from ..lib.po_processing import process_single_po  # shared utility
from ..lib.driver_manager import DriverManager
from ..core.protocols import StorageManager, Messenger

# Centralized config for URLs
try:
    from ..config.app_config import Config as _ExperimentalConfig  # type: ignore
    BASE_URL: str = getattr(_ExperimentalConfig, "BASE_URL", "https://unilever.coupahost.com")
except Exception:
    BASE_URL = "https://unilever.coupahost.com"

logger = structlog.get_logger(__name__)

_HTTP_POOL_PATCH_MARKER = "_coupa_worker_pool_patch_applied"


_DOWNLOAD_SUFFIXES = ('.crdownload', '.tmp', '.partial')


# Helper functions moved to core/utils.py


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse a boolean environment flag with safe defaults."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str) -> list[str]:
    """Parse a comma-separated environment variable into a list of args."""
    raw_value = os.environ.get(name, "")
    return [item.strip() for item in raw_value.split(",") if item.strip()]

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
        self.task_queue: "queue.Queue[ProcessingTask]" = queue.Queue(maxsize=1)
        
        # State management
        self._stop_event = threading.Event()
        self._running = False
        self._last_heartbeat = time.time()

        # PID of the actual browser process (ms:browserProcessId capability).
        # Tracked at session startup so we can force-kill it even if the
        # WebDriver service handle becomes unavailable.
        self._browser_pid: Optional[int] = None
        
        # Statistics
        self.start_time: Optional[float] = None
        self.tasks_processed = 0
        self.tasks_failed = 0
        self._debug_runtime_enabled = _env_flag("COUPA_DEBUG_RUNTIME", False)
        telemetry_mode = os.environ.get("COUPA_TELEMETRY_MODE", "aggregated").strip().lower()
        self._telemetry_mode = telemetry_mode if telemetry_mode in {"aggregated", "detailed"} else "aggregated"
        self._telemetry_debounce_seconds = max(
            0.0,
            float(os.environ.get("COUPA_TELEMETRY_DEBOUNCE_MS", "500")) / 1000.0,
        )
        self._last_progress_signature: Optional[tuple[Any, ...]] = None
        self._last_progress_emitted_at = 0.0
        self._last_progress_downloaded = -1
        
        logger.debug("WorkerProcess initialized", worker_id=worker_id)

    def _runtime_debug_log(self, message: str) -> None:
        """Write runtime debug traces only when explicitly enabled."""
        if not self._debug_runtime_enabled:
            return
        try:
            with open("/tmp/worker_debug.log", "a", encoding="utf-8") as debug_log:
                timestamp = datetime.datetime.now().isoformat()
                debug_log.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    def _publish_metric(
        self,
        *,
        status: str,
        po_id: str = "SYSTEM",
        message: str = "",
        attachments_found: int = 0,
        attachments_downloaded: int = 0,
        timestamp: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publish a worker snapshot used by the UI and activity feed."""
        if not self.messenger:
            return

        try:
            payload = {
                "worker_id": self.worker_id,
                "po_id": po_id,
                "status": status,
                "timestamp": float(timestamp if timestamp is not None else time.time()),
                "attachments_found": attachments_found,
                "attachments_downloaded": attachments_downloaded,
                "tasks_processed": self.tasks_processed,
                "tasks_failed": self.tasks_failed,
                "efficiency_score": (self.tasks_processed / max(1, self.tasks_processed + self.tasks_failed)) * 100
                if (self.tasks_processed + self.tasks_failed) > 0
                else 0.0,
                "message": message,
            }
            if extra:
                payload.update(extra)
            self.messenger.send_metric(payload)
        except Exception:
            pass

    def _emit_worker_state(self, status: str, message: str, *, po_id: str = "SYSTEM") -> None:
        """Publish worker lifecycle state so the UI can render the worker before first task."""
        self._publish_metric(status=status, po_id=po_id, message=message)

    def _reset_progress_telemetry(self) -> None:
        """Reset per-task progress debounce state."""
        self._last_progress_signature = None
        self._last_progress_emitted_at = 0.0
        self._last_progress_downloaded = -1

    def _emit_task_started(self, task: POTask) -> None:
        """Publish the beginning of task processing once per task."""
        po_number = task.po_number or task.metadata.get("po_number") or "SYSTEM"
        self._reset_progress_telemetry()
        self._publish_metric(
            status="STARTED",
            po_id=po_number,
            message=f"Started PO {po_number}",
            extra={"task_id": task.task_id},
        )

    def _emit_ready_for_next_task(self) -> None:
        """Publish that the worker is ready for another assignment."""
        self._publish_metric(
            status="READY",
            po_id="SYSTEM",
            message=f"{self.worker_id} is ready",
        )

    def _emit_task_progress(self, task: POTask, progress_data: Dict[str, Any]) -> None:
        """Publish debounced task progress snapshots."""
        po_number = task.po_number or task.metadata.get("po_number") or "SYSTEM"
        attachments_found = int(progress_data.get("attachments_found", 0) or 0)
        attachments_downloaded = int(progress_data.get("attachments_downloaded", 0) or 0)
        message = str(progress_data.get("message", "") or "")
        now = time.time()
        signature = (
            task.task_id,
            attachments_found,
            attachments_downloaded,
            message,
        )

        if self._telemetry_mode != "detailed":
            downloads_changed = attachments_downloaded != self._last_progress_downloaded
            enough_time_elapsed = (now - self._last_progress_emitted_at) >= self._telemetry_debounce_seconds
            if signature == self._last_progress_signature:
                return
            if not downloads_changed and not enough_time_elapsed:
                return

        self._last_progress_signature = signature
        self._last_progress_downloaded = attachments_downloaded
        self._last_progress_emitted_at = now
        self._publish_metric(
            status="PROCESSING",
            po_id=po_number,
            message=message,
            attachments_found=attachments_found,
            attachments_downloaded=attachments_downloaded,
            timestamp=now,
            extra={"task_id": task.task_id},
        )

    def _get_startup_delay_seconds(self) -> float:
        """Return a small deterministic jitter to spread browser-launch load.

        Values are intentionally kept small (<0.31 s) after the P13 stagger removal.
        """
        try:
            worker_index = int(self.worker_id.split("-")[-1])
        except (ValueError, IndexError):
            worker_index = 0
        return 0.1 + (worker_index % 5) * 0.04

    def can_accept_task(self) -> bool:
        """Return True when the worker is ready for exactly one new assignment."""
        if not self._running or self.should_stop():
            return False
        if self.current_task is not None or not self.task_queue.empty():
            return False
        return self.worker.status in {WorkerStatus.READY, WorkerStatus.IDLE}

    def submit_task_assignment(self, task: ProcessingTask) -> bool:
        """Queue one assigned task for this worker without allowing prefetch beyond one item."""
        if not self.can_accept_task():
            return False

        try:
            self.task_queue.put_nowait(task)
            return True
        except queue.Full:
            return False

    def get_assigned_task(self, timeout: float = 0.1) -> Optional[ProcessingTask]:
        """Return the next centrally-assigned task for this worker."""
        if self.should_stop():
            return None

        try:
            return self.task_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def has_pending_assignment(self) -> bool:
        """Return True when a task is already reserved for this worker."""
        return not self.task_queue.empty()

    def drain_assigned_tasks(self) -> list[ProcessingTask]:
        """Drain reserved assignments that never started processing."""
        drained: list[ProcessingTask] = []
        while True:
            try:
                drained.append(self.task_queue.get_nowait())
            except queue.Empty:
                return drained
    
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
            self._emit_worker_state("STARTING", f"{self.worker_id} is starting")
            
            # Initialize browser session
            self._initialize_browser_session()
            
            # Mark worker as ready
            self.worker.status = WorkerStatus.READY
            self._emit_worker_state("READY", f"{self.worker_id} is ready")
            
            logger.info("Worker process started successfully", 
                       worker_id=self.worker_id)
            
        except Exception as e:
            self._running = False
            self.worker.status = WorkerStatus.CRASHED
            self.worker.last_error = f"Startup failed: {str(e)}"
            self._emit_worker_state("FAILED", f"{self.worker_id} failed to start: {e}")
            try:
                logger.error("Failed to start worker process",
                            worker_id=self.worker_id, error=str(e))
            except (ValueError, OSError):
                pass
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
            
            self._runtime_debug_log(
                f"Worker {self.worker_id} initializing. Config mode: {execution_mode} -> Str: {mode_str}"
            )
            logger.info(
                "WorkerProcess browser init",
                worker_id=self.worker_id,
                execution_mode=mode_str,
            )
            
            # Use Playwright for filtered and no_js modes (resource blocking)
            if mode_str in ("filtered", "no_js"):
                self._runtime_debug_log(f"Worker {self.worker_id} selecting Playwright session")
                self._initialize_playwright_session(mode_str)
                return
            
            self._runtime_debug_log(f"Worker {self.worker_id} selecting Selenium session")
            # Otherwise, use Selenium with Edge WebDriver (standard mode)
            self._initialize_selenium_session()
            
        except Exception as e:
            try:
                logger.error("Failed to initialize browser session",
                            worker_id=self.worker_id, error=str(e))
            except (ValueError, OSError):
                pass
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
        # Lazy imports: Selenium is only needed in Selenium mode; deferring avoids
        # the ~500 ms import cost on every worker spawn regardless of mode.
        from selenium import webdriver  # noqa: PLC0415
        from selenium.webdriver.edge.options import Options  # noqa: PLC0415
        from selenium.webdriver.edge.service import Service  # noqa: PLC0415

        # Setup Edge options
        edge_options = Options()

        if self.config.headless_mode:
            edge_options.add_argument("--headless=new")
            edge_options.add_argument("--disable-gpu")
            edge_options.add_argument("--hide-scrollbars")
            edge_options.add_argument("--mute-audio")
        
        # Profile configuration
        if self.profile.worker_profile_path:
            edge_options.add_argument(f"--user-data-dir={self.profile.worker_profile_path}")
            edge_options.add_argument(f"--profile-directory={self.profile.profile_name}")

        # Basic options
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--window-size=1920,1080")
        edge_options.add_argument("--no-first-run")

        # Reduce memory footprint: disable unneeded browser background services
        edge_options.add_argument("--disable-extensions")
        edge_options.add_argument("--disable-sync")
        edge_options.add_argument("--disable-translate")
        edge_options.add_argument("--disable-default-apps")
        # Cap V8 JS heap per renderer at 768 MB (Coupa SPA needs headroom above 512 MB)
        edge_options.add_argument("--js-flags=--max-old-space-size=768")

        for extra_arg in _env_csv("COUPA_EDGE_EXTRA_ARGS"):
            edge_options.add_argument(extra_arg)

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
        self._runtime_debug_log(f"Worker {self.worker_id} using driver at: {driver_path}")
        
        # Verify driver before start
        if not dm.verify_driver(driver_path):
            msg = f"Worker {self.worker_id}: EdgeDriver verification failed for {driver_path}"
            self._runtime_debug_log(f"FAIL {msg}")
            raise RuntimeError(msg)
        self._runtime_debug_log(f"OK Worker {self.worker_id}: EdgeDriver verified")
        
        # Create service with minimal configuration to avoid conflicts
        service = Service(
            executable_path=driver_path,
            # Remove log suppression to see potential errors
            # service_args=["--verbose", "--log-level=DEBUG"]  # Commented out to reduce noise
        )

        try:
            self._runtime_debug_log(f"Worker {self.worker_id} spawning Edge process")
            driver = webdriver.Edge(service=service, options=edge_options)
            self._runtime_debug_log(f"OK Worker {self.worker_id} Edge process spawned successfully")
        except Exception as e:
            self._runtime_debug_log(f"FAIL Worker {self.worker_id} failed to spawn Edge: {str(e)}")
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

        # Record the browser process PID for reliable force-kill.
        # ms:browserProcessId is the actual Edge/Chrome browser PID, distinct
        # from the msedgedriver service process — killing only the service
        # leaves the browser as an orphan on macOS.
        caps = getattr(driver, 'capabilities', None) or {}
        self._browser_pid = caps.get('ms:browserProcessId')
        if self._browser_pid:
            logger.debug("Tracked browser PID", worker_id=self.worker_id, pid=self._browser_pid)
        
        logger.info(
            "Edge WebDriver started",
            worker_id=self.worker_id,
            profile_path=self.profile.worker_profile_path,
            headless=self.config.headless_mode,
        )
        self.browser_session.ensure_keeper_tab()

        # Authenticate with Coupa
        self._runtime_debug_log(f"Worker {self.worker_id} starting authentication")
        success = self.browser_session.authenticate()
        
        if not success:
            self._runtime_debug_log(f"FAIL Worker {self.worker_id} failed to authenticate with Coupa")
            raise RuntimeError("Failed to authenticate with Coupa")

        self.browser_session.trim_to_single_tab(
            preferred_handle=self.browser_session.keeper_handle or self.browser_session.main_window_handle
        )
        
        self._runtime_debug_log(f"OK Worker {self.worker_id} authentication successful")
        
        logger.debug("Browser session initialized", worker_id=self.worker_id)

    def _configure_connection_pools(self) -> None:
        """Configure urllib3 connection pools to prevent multiprocessing issues."""
        try:
            import urllib3
            
            # Monkey patch urllib3 to use larger default pool sizes globally
            # This prevents "Connection pool is full" errors during multiprocessing
            http_pool_init = urllib3.connectionpool.HTTPConnectionPool.__init__
            if not getattr(http_pool_init, _HTTP_POOL_PATCH_MARKER, False):
                original_init = http_pool_init

                def patched_init(self, host, port=None, timeout=urllib3.util.timeout.Timeout.DEFAULT_TIMEOUT, maxsize=1, block=False, headers=None, retries=None, _proxy=None, _proxy_headers=None, _proxy_config=None, **conn_kw):
                    # Force larger pool sizes, especially for localhost
                    if host in ('localhost', '127.0.0.1'):
                        maxsize = max(maxsize, 20)  # Larger pools for localhost/multiprocessing
                    else:
                        maxsize = max(maxsize, 10)  # Normal pools for external connections
                    return original_init(self, host, port, timeout, maxsize, block, headers, retries, _proxy, _proxy_headers, _proxy_config, **conn_kw)

                setattr(patched_init, _HTTP_POOL_PATCH_MARKER, True)
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
                from ..config.app_config import Config as _Cfg
                target = _Cfg.DOWNLOAD_FOLDER
            except Exception as e:
                logger.warning(
                    "Failed to get download folder from config (attempt 1)",
                    worker_id=self.worker_id,
                    error=str(e)
                )
                try:
                    from ..config.app_config import Config as _Cfg  # type: ignore
                    target = _Cfg.DOWNLOAD_FOLDER
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

        # Update shared runtime config singleton so other components see the same path.
        try:
            from ..config import app_config as runtime_config
            runtime_config.Config.DOWNLOAD_FOLDER = normalized  # type: ignore[attr-defined]
            logger.debug("Updated runtime Config.DOWNLOAD_FOLDER", worker_id=self.worker_id, path=normalized)
        except Exception as e:
            logger.warning("Failed to update runtime Config", worker_id=self.worker_id, error=str(e))

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
            self._emit_task_started(task)
            
            # Assignment reservation happens in the central dispatcher.
            
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
            self._emit_ready_for_next_task()
            self._reset_progress_telemetry()
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
            self._emit_ready_for_next_task()
            self._reset_progress_telemetry()
            
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
        
        po_number = task.po_number
        po_data = dict(task.metadata or {})
        display_po = po_data.get('po_number', po_number)
        hierarchy_cols = self.config.hierarchy_columns or []
        has_hierarchy = bool(self.config.has_hierarchy_data)

        # Reuse a cached BrowserManager to avoid reconstructing DriverManager per PO
        if not hasattr(self, '_cached_browser_manager'):
            self._cached_browser_manager = BrowserManager()
        browser_manager = self._cached_browser_manager
        browser_manager.driver = driver

        tab_handle = None
        try:
            # create_tab ensures keeper tab exists and switches to the new tab
            tab_handle = self.browser_session.create_tab(task.task_id)
            
            # Assign PO number to tab after creation
            if task.task_id in self.browser_session.active_tabs:
                tab = self.browser_session.active_tabs[task.task_id]
                tab.assign_po(po_number)

            def progress_bridge(progress_data: Dict[str, Any]):
                # Keep heartbeat fresh while downloads are in progress so the
                # health monitor doesn't kill a legitimately busy worker.
                self._update_heartbeat()
                self._emit_task_progress(task, progress_data)

            # Check if batch finalization is enabled in experimental config
            skip_finalization = False
            try:
                from ..config.app_config import Config
                skip_finalization = Config.BATCH_FINALIZATION_ENABLED
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

            # Try to recover download folder and count any files that were
            # already saved before the exception occurred.
            failed_folder = ''
            files_on_disk = 0
            try:
                normalized_dl = self._apply_download_root_override()
                # Look for __WORK folders matching this PO
                if normalized_dl and os.path.isdir(normalized_dl):
                    for entry in os.scandir(normalized_dl):
                        if entry.is_dir() and po_number in entry.name:
                            failed_folder = entry.path
                            files_on_disk = sum(
                                1 for f in os.scandir(entry.path)
                                if f.is_file() and not f.name.startswith('.') and not f.name.endswith(('.crdownload', '.tmp'))
                            )
                            break
            except Exception:
                pass

            # If files were partially downloaded, report PARTIAL instead of FAILED
            if files_on_disk > 0 and status_code == 'FAILED':
                status_code = 'PARTIAL'

            return {
                'success': False,
                'error': friendly,
                'task_id': task.task_id,
                'po_number': po_number,
                'po_number_display': display_po,
                'status_code': status_code,
                'message': friendly,
                'final_folder': failed_folder,
                'attachments_downloaded': files_on_disk,
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
                # Tab close failed; try to at least refocus the main window
                try:
                    self.browser_session.focus_main_window()
                except Exception:
                    pass
    
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
                     # Escalate: terminate/kill the underlying browser process
                     self._force_kill_browser_process(driver)
                else:
                     logger.debug("Driver quit successful", worker_id=self.worker_id)
            except Exception as quit_err:
                logger.warning("Graceful quit failed; forcing shutdown", worker_id=self.worker_id, error=str(quit_err))
                self._force_kill_browser_process(driver)
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
    
    def _force_kill_browser_process(self, driver) -> None:
        """Kill the entire browser process tree (msedgedriver + Edge) using psutil.

        On macOS, killing only the WebDriver service (msedgedriver) leaves the
        browser process as an orphan.  We therefore collect PIDs from two
        sources and kill the full sub-tree of each:
          1. driver.service.process  — the msedgedriver service
          2. self._browser_pid       — the actual Edge browser (ms:browserProcessId)
        """
        import psutil  # noqa: PLC0415 — already a declared dependency

        pids_to_kill: list[int] = []

        # Source 1: WebDriver service process and its children
        service = getattr(driver, 'service', None)
        svc_proc = getattr(service, 'process', None) if service else None
        svc_pid = getattr(svc_proc, 'pid', None) if svc_proc else None
        if svc_pid:
            try:
                ps = psutil.Process(svc_pid)
                pids_to_kill += [c.pid for c in ps.children(recursive=True)]
                pids_to_kill.append(svc_pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pids_to_kill.append(svc_pid)

        # Source 2: Tracked browser PID (ms:browserProcessId capability)
        browser_pid = self._browser_pid
        if browser_pid and browser_pid not in pids_to_kill:
            try:
                ps = psutil.Process(browser_pid)
                pids_to_kill += [c.pid for c in ps.children(recursive=True)]
                pids_to_kill.append(browser_pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pids_to_kill.append(browser_pid)

        if not pids_to_kill:
            logger.debug("No browser PIDs to kill", worker_id=self.worker_id)
            return

        logger.debug("Killing browser process tree", worker_id=self.worker_id, pids=pids_to_kill)

        # SIGTERM first pass
        live_procs: list[psutil.Process] = []
        for pid in pids_to_kill:
            try:
                p = psutil.Process(pid)
                p.terminate()
                live_procs.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Wait up to 3 s for graceful exit
        if live_procs:
            _, survivors = psutil.wait_procs(live_procs, timeout=3)
            for p in survivors:
                try:
                    p.kill()
                    logger.warning("Escalated to SIGKILL", worker_id=self.worker_id, pid=p.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        self._browser_pid = None  # Reset so a fresh session can record its own PID

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
        heartbeat_age = time.time() - self._last_heartbeat
        
        return {
            'worker_id': self.worker_id,
            'status': self.worker.status.value,
            'running': self._running,
            'healthy': self._running and heartbeat_age <= 300 and self.browser_session is not None,
            'heartbeat_age': heartbeat_age,
            'uptime_seconds': uptime,
            'current_task': self.current_task.po_number if self.current_task else None,
            'has_pending_assignment': self.has_pending_assignment(),
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
