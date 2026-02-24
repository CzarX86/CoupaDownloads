"""
Módulo WorkerManager.

Gerencia o processamento paralelo de POs usando workers, incluindo inicialização de drivers,
monitoramento de progresso e coordenação de downloads.
"""

import os
import sys
import shutil
import tempfile
import random
import re
import time
import threading
import queue
import multiprocessing as mp
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
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

from .lib.browser import BrowserManager
from .lib.config import Config as ExperimentalConfig
from .lib.downloader import Downloader
from .lib.folder_hierarchy import FolderHierarchyManager
from .lib.models import HeadlessConfiguration, InteractiveSetupSession

# Import worker pool for parallel processing
from .workers.persistent_pool import PersistentWorkerPool

# Import CSV handler for incremental persistence
from .core.csv_handler import CSVHandler, WriteQueue
from .workers.models import PoolConfig


class SessionStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
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
        stagger_delay: float = 0.5,
        execution_mode: Any = None,
        communication_manager: Optional[Any] = None,
    ):
        """Initialize processing session for PO batch processing."""
        # Validate parameters
        if not isinstance(headless_config, HeadlessConfiguration):
            raise TypeError("headless_config must be HeadlessConfiguration instance")
        
        if not (isinstance(max_workers, int) and max_workers >= 1):
            raise ValueError(f"max_workers must be a positive integer, got {max_workers}")
        
        # Configuration
        self.headless_config = headless_config
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self.hierarchy_columns = hierarchy_columns
        self.has_hierarchy_data = has_hierarchy_data
        self.stagger_delay = stagger_delay
        from .lib.models import ExecutionMode
        self.execution_mode = execution_mode or ExecutionMode.STANDARD
        self.communication_manager = communication_manager
        
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
        
        # CSV/SQLite handler support
        self.csv_path: Optional[str] = None
        self.sqlite_db_path: Optional[str] = None
    
    def set_csv_path(self, csv_path: str) -> None:
        """Set CSV path for worker processes."""
        self.csv_path = csv_path

    def set_sqlite_db_path(self, sqlite_db_path: str) -> None:
        """Set SQLite DB path for worker processes."""
        self.sqlite_db_path = sqlite_db_path
    
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
    
    def stop_processing(self, emergency: bool = False) -> bool:
        """
        Stop current processing session.
        
        Args:
            emergency: If True, accelerated shutdown with minimal timeouts.
        """
        if self.status != SessionStatus.RUNNING and not emergency:
            return True
        
        try:
            if self.worker_pool:
                # Run async shutdown in sync context
                import asyncio
                try:
                    # Check if an event loop is already running in this thread
                    try:
                        loop = asyncio.get_running_loop()
                        is_running = True
                    except RuntimeError:
                        loop = asyncio.get_event_loop()
                        is_running = loop.is_running()

                    if is_running:
                        # Create task for shutdown and wait for it
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self.worker_pool.shutdown(emergency=emergency))
                            future.result(timeout=15 if emergency else 60)
                    else:
                        loop.run_until_complete(self.worker_pool.shutdown(emergency=emergency))
                except Exception as e:
                    # Fallback to a fresh loop if needed
                    try:
                        asyncio.run(self.worker_pool.shutdown(emergency=emergency))
                    except Exception as fallback_err:
                        print(f"Failed final shutdown attempt: {fallback_err}")
                
                self.worker_pool = None
                return True
            
            self.status = SessionStatus.COMPLETED if self.status == SessionStatus.RUNNING else self.status
            return True
            
        except Exception as e:
            print(f"Error stopping processing: {e}")
            self.status = SessionStatus.FAILED
            return False
    
    # Private helper methods
    
    def _process_parallel(self, po_list: List[dict]) -> Tuple[int, int, Dict[str, Any]]:
        """Process POs using parallel worker pool."""
        # Check if profiles are disabled - if so, fall back to ProcessPoolExecutor
        from .lib.config import Config as _Cfg
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

                config = PoolConfig.create_default(
                    base_profile_path=base_profile_path,
                    worker_count=self.max_workers,
                    headless_mode=self.headless_config.get_effective_headless_mode(),
                    base_profile_name=ExperimentalConfig.EDGE_PROFILE_NAME or "Default",
                    hierarchy_columns=self.hierarchy_columns,
                    has_hierarchy_data=self.has_hierarchy_data,
                    download_root=download_root,
                    sqlite_db_path=self.sqlite_db_path,
                    stagger_delay=self.stagger_delay,
                    execution_mode=self.execution_mode.value if hasattr(self.execution_mode, 'value') else str(self.execution_mode)
                )
                
                print(f"🔧 PoolConfig created with download_root: {config.download_root}")
                
                # Create and start worker pool
                csv_handler = None
                if hasattr(self, 'csv_path') and self.csv_path:
                    try:
                        from csv_handler import CSVHandler
                        from pathlib import Path
                        csv_handler = CSVHandler(Path(self.csv_path))
                        print(f"[PersistentWorkerPool] CSV handler created for: {self.csv_path}")
                    except Exception as e:
                        print(f"[PersistentWorkerPool] Failed to create CSV handler: {e}")
                self.worker_pool = PersistentWorkerPool(config, csv_handler=csv_handler, communication_manager=self.communication_manager)
                await self.worker_pool.start()
                
                # Start progress monitoring thread
                import threading
                monitor_thread = threading.Thread(target=self._monitor_parallel_progress, daemon=True)
                monitor_thread.start()
                
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
                        result = handle.wait_for_completion(timeout=120)
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
        from .lib.browser import BrowserManager
        from .lib.po_processing import process_single_po

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
        from concurrent.futures import ProcessPoolExecutor, as_completed
        import multiprocessing as mp
        
        # Calculate workers
        default_workers = min(2, len(po_list))
        proc_workers = max(1, min(self.max_workers, len(po_list)))
        print(f"📊 Using {proc_workers} ProcessPoolExecutor worker(s) (profiles disabled)")
        
        # Get download root for workers
        from .lib.config import Config
        download_root = os.path.abspath(os.path.expanduser(getattr(Config, 'DOWNLOAD_FOLDER', ExperimentalConfig.DOWNLOAD_FOLDER)))
        
        with ProcessPoolExecutor(max_workers=proc_workers, mp_context=mp.get_context("spawn")) as executor:
            future_map: dict = {}
            
            # Convert po_list to expected format and submit tasks
            for po_data in po_list:
                # Prepare args for process_po_worker
                args = (
                    po_data,
                    self.hierarchy_columns or [],
                    self.has_hierarchy_data,
                    self.headless_config,
                    download_root,
                    self.csv_path,
                    self.sqlite_db_path,
                    self.execution_mode,
                )
                future = executor.submit(process_po_worker, args)
                future_map[future] = po_data
            
            # Wait for all tasks to complete
            for future in as_completed(future_map):
                try:
                    result = future.result()
                    results.append(result)
                    if result.get('success', False):
                        successful += 1
                    else:
                        failed += 1
                except Exception as exc:
                    failed += 1
                    po_data = future_map[future]
                    error_msg = f"PO {po_data.get('po_number', 'unknown')} generated an exception: {_humanize_exception(exc)}"
                    results.append({
                        'po_number_display': po_data.get('po_number', 'unknown'),
                        'status_code': 'FAILED',
                        'message': error_msg,
                        'final_folder': '',
                        'success': False
                    })
        
        return successful, failed, {'results': results}
    
    def _monitor_parallel_progress(self):
        """Monitor progress of parallel processing."""
        while self.status == SessionStatus.RUNNING and self.worker_pool:
            try:
                # Get status from task queue
                queue_stats = self.worker_pool.task_queue.get_queue_status()
                
                self.completed_tasks = queue_stats.get('completed_tasks', 0)
                self.failed_tasks = queue_stats.get('failed_tasks', 0)
                self.active_tasks = queue_stats.get('processing_tasks', 0)
                
                # Send progress metrics to communication manager
                if self.communication_manager:
                    progress_data = {
                        'total_tasks': self.total_tasks,
                        'completed_tasks': self.completed_tasks,
                        'failed_tasks': self.failed_tasks,
                        'active_tasks': self.active_tasks,
                        'timestamp': time.time(),
                    }
                    # Send as a special progress metric
                    self.communication_manager.send_metric({
                        'worker_id': -1,  # Special ID for progress updates
                        'po_id': 'PROGRESS_UPDATE',
                        'status': 'PROGRESS',
                        'timestamp': time.time(),
                        'message': f"Progress: {self.completed_tasks}/{self.total_tasks} completed, {self.failed_tasks} failed, {self.active_tasks} active",
                        'total_tasks': self.total_tasks,
                        'completed_tasks': self.completed_tasks,
                        'failed_tasks': self.failed_tasks,
                        'active_tasks': self.active_tasks,
                    })
                
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
    
    # NEW: Actually copy the profile folder content
    src_profile = os.path.join(base_user_data_dir, profile_name)
    dst_profile = os.path.join(clone_root, profile_name)
    if os.path.exists(src_profile):
        _copy_profile_folder(src_profile, dst_profile)
    return clone_root


def _has_active_downloads(folder_path: str) -> bool:
    try:
        names = os.listdir(folder_path)
    except Exception:
        return False
    return any(name.endswith(('.crdownload', '.tmp', '.partial')) for name in names)


def _wait_for_downloads_complete(folder_path: str, timeout: int = 180, poll: float = 0.2, expected_count: Optional[int] = None) -> None:
    start = time.time()
    quiet_required = 0.4  # Matches standardized aggressive wait
    quiet_start = None
    while time.time() - start < timeout:
        active = _has_active_downloads(folder_path)
        
        if expected_count is not None:
            try:
                # Count only finalized files (not matching download suffixes)
                current_files = len([f for f in os.listdir(folder_path) if not any(f.endswith(s) for s in ('.crdownload', '.tmp', '.partial'))])
                if current_files >= expected_count and not active:
                    return
            except Exception:
                pass

        if not active:
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


def _legacy_rename_folder_with_status(folder_path: str, status_code: str) -> str:
    """Legacy fallback for folder renaming - now with robust merging support."""
    try:
        if not folder_path or not os.path.exists(folder_path):
            return folder_path

        folder_name = os.path.basename(folder_path)
        parent_dir = os.path.dirname(folder_path)

        # Normalize __WORK suffix aggressively
        if folder_name.endswith('__WORK'):
            folder_name = folder_name[:-6]  # Remove __WORK

        suffix = _suffix_for_status(status_code)
        new_name = f"{folder_name}{suffix}"
        new_path = os.path.join(parent_dir, new_name)

        # Cooldown period
        time.sleep(1.0)
        
        if os.path.exists(new_path) and os.path.abspath(folder_path) != os.path.abspath(new_path):
            # Target exists, we should merge. 
            # Since this is "legacy", we'll do a simple merge with retries.
            import shutil
            for item in os.listdir(folder_path):
                s = os.path.join(folder_path, item)
                d = os.path.join(new_path, item)
                
                success = False
                for attempt in range(3):
                    try:
                        if os.path.isdir(s):
                            if os.path.exists(d):
                                # Merge subdirectory content
                                for subitem in os.listdir(s):
                                    shutil.move(os.path.join(s, subitem), os.path.join(d, subitem))
                                os.rmdir(s)
                            else:
                                shutil.move(s, d)
                        else:
                            if os.path.exists(d):
                                os.remove(d)
                            shutil.move(s, d)
                        success = True
                        break
                    except Exception:
                        time.sleep(1.0)
                        
            try:
                # Cleanup junk
                for item in os.listdir(folder_path):
                    if item in ('.DS_Store', 'Thumbs.db'):
                        try:
                            os.remove(os.path.join(folder_path, item))
                        except Exception:
                            pass
                
                if not os.listdir(folder_path):
                    os.rmdir(folder_path)
            except Exception:
                pass
            return new_path

        os.rename(folder_path, new_path)
        return new_path
    except Exception:
        return folder_path


def process_po_worker(args):
    """Run a single PO in its own process, with its own Edge driver.

    Args tuple: (po_data, hierarchy_cols, has_hierarchy_data, headless_config[, download_root, csv_path, sqlite_db_path, execution_mode])
    Returns: dict with keys: po_number_display, status_code, message, final_folder
    """
    from pathlib import Path

    # Add the project root to Python path for spawned processes
    project_root = Path(__file__).resolve().parents[2]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    # Add EXPERIMENTAL directory to path
    experimental_root = Path(__file__).resolve().parents[1]
    experimental_root_str = str(experimental_root)
    if experimental_root_str not in sys.path:
        sys.path.insert(0, experimental_root_str)

    sqlite_db_path = None # Default to None
    if len(args) == 4:
        po_data, hierarchy_cols, has_hierarchy_data, headless_config = args
        download_root = os.environ.get('DOWNLOAD_FOLDER', ExperimentalConfig.DOWNLOAD_FOLDER)
        csv_path = None
    elif len(args) == 5:
        po_data, hierarchy_cols, has_hierarchy_data, headless_config, download_root = args
        csv_path = None
    elif len(args) == 7:
        po_data, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path, sqlite_db_path = args
        execution_mode = "standard"
    elif len(args) >= 8:
        po_data, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path, sqlite_db_path, execution_mode = args[:8]
    else:
        raise ValueError("process_po_worker expects at least 4 arguments")

    output_handle = None
    suppress_output = os.environ.get('SUPPRESS_WORKER_OUTPUT', '').strip().lower() in {'1', 'true', 'yes'}
    if suppress_output:
        try:
            output_handle = open(os.devnull, 'w')
            # Redirect stdout/stderr to avoid TTY pollution under Textual UI
            os.dup2(output_handle.fileno(), sys.stdout.fileno())
            os.dup2(output_handle.fileno(), sys.stderr.fileno())
            sys.stdout = output_handle
            sys.stderr = output_handle
            import logging
            logging.getLogger().handlers = []
            logging.basicConfig(stream=output_handle, force=True, level=logging.INFO)
        except Exception:
            output_handle = None

    download_root = os.path.abspath(os.path.expanduser(download_root)) if download_root else os.path.abspath(os.path.expanduser(ExperimentalConfig.DOWNLOAD_FOLDER))
    os.environ['DOWNLOAD_FOLDER'] = download_root
    try:
        ExperimentalConfig.DOWNLOAD_FOLDER = download_root
        from .lib.config import Config
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
            from .core.csv_handler import CSVHandler
            csv_handler = CSVHandler(Path(csv_path), sqlite_db_path=sqlite_db_path)
            print(f"[worker] 📊 CSV handler initialized for {csv_path} (SQLite: {sqlite_db_path})", flush=True)
        except Exception as e:
            print(f"[worker] ⚠️ Failed to initialize CSV handler: {e}", flush=True)

    # Log headless configuration for this worker
    print(f"[worker] 🎯 Headless configuration: {headless_config}", flush=True)

    try:
        print(f"[worker] ▶ Starting PO {display_po}", flush=True)
        # Create folder path without creating directory (JIT)
        folder_path = folder_manager.create_folder_path(po_data, hierarchy_cols, has_hierarchy_data, create_dir=False)
        
        # Callback to create folder when attachments are found
        def _ensure_folder_exists(_findings=None):
            try:
                os.makedirs(folder_path, exist_ok=True)
                return folder_path
            except Exception as e:
                print(f"[worker] ⚠️ Failed to create JIT folder: {e}", flush=True)
                return folder_path
        
        print(f"[worker] 📁 Folder path determined: {folder_path} (Waiting for findings to create)", flush=True)

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

        # Progress emitter
        def _emit_progress(payload: Dict[str, Any]) -> None:
            if not communication_manager:
                return
            try:
                metric_data = {
                    'worker_id': f"Proc_{os.getpid()}",
                    'po_id': display_po,
                    'status': payload.get('status', 'PROCESSING'),
                    'timestamp': time.time(),
                    'attachments_found': payload.get('attachments_found', 0),
                    'attachments_downloaded': payload.get('attachments_downloaded', 0),
                    'message': payload.get('message', ''),
                }
                communication_manager.send_metric(metric_data)
            except Exception:
                pass

        mode_str = getattr(execution_mode, 'value', str(execution_mode))
        if mode_str in ("filtered", "no_js"):
            print(f"[worker] 🛡️ Using Playwright for mode: {execution_mode}", flush=True)
            from .lib.playwright_manager import PlaywrightManager
            from .lib.playwright_downloader import PlaywrightDownloader
            
            pw_manager = PlaywrightManager()
            try:
                # Use clone_dir as profile directory for persistent authentication
                page = pw_manager.start(
                    headless=headless_config.get_effective_headless_mode(), 
                    execution_mode=execution_mode,
                    profile_dir=clone_dir
                )
                
                def _on_findings(findings):
                    # For Playwright mode, we might need a custom folder logic
                    # For now just use the existing folder_path logic
                    return folder_path

                pw_downloader = PlaywrightDownloader(page, progress_callback=_emit_progress)
                print(f"[worker] 🌐 Starting Playwright download for {display_po}", flush=True)
                result_payload = pw_downloader.download_attachments_for_po(display_po, on_attachments_found=_ensure_folder_exists)
            finally:
                pw_manager.cleanup()
        
        elif mode_str == "direct_http":
            print(f"[worker] 🚀 Using Direct HTTP (Turbo) for mode: {execution_mode}", flush=True)
            from .lib.direct_http_downloader import DirectHTTPDownloader
            
            # We still need browser once to get cookies if not provided
            browser_manager.initialize_driver_with_profile(
                headless=headless_config.get_effective_headless_mode(),
                profile_dir=clone_dir,
                download_dir=folder_path
            )
            driver = browser_manager.driver
            
            # Navigate once to get into the domain
            from .lib.config import Config as LibConfig
            driver.get(LibConfig.BASE_URL)
            
            # Get cookies
            selenium_cookies = driver.get_cookies()
            httpx_cookies = {c['name']: c['value'] for c in selenium_cookies}
            
            browser_manager.cleanup()
            
            def _on_findings(findings):
                return folder_path
                
            http_downloader = DirectHTTPDownloader(httpx_cookies, progress_callback=_emit_progress)
            print(f"[worker] 🌐 Starting Direct HTTP download for {display_po}", flush=True)
            result_payload = http_downloader.download_attachments_for_po(display_po, on_attachments_found=_ensure_folder_exists)
            http_downloader.close()
            
        else:
            # Standard Selenium flow
            browser_manager.initialize_driver_with_profile(
                headless=headless_config.get_effective_headless_mode(),
                profile_dir=clone_dir,
                download_dir=folder_path
            )
            driver = browser_manager.driver
            print("[worker] ⚙️ WebDriver initialized", flush=True)
            browser_manager.update_download_directory(folder_path)
            
            downloader = Downloader(driver, browser_manager, progress_callback=_emit_progress)
            print(f"[worker] 🌐 Starting Selenium download for {display_po}", flush=True)
            # Pass _ensure_folder_exists for JIT
            result_payload = downloader.download_attachments_for_po(display_po, on_attachments_found=_ensure_folder_exists)
            
        message = result_payload.get('message', '')
        print(f"[worker] ✅ Download routine finished for {display_po}", flush=True)

        # Wait for downloads to finish
        _wait_for_downloads_complete(folder_path, expected_count=result_payload.get('attachments_downloaded'))
        print("[worker] ⏳ Downloads settled", flush=True)

        status_code = _derive_status_label(result_payload)
        
        # Check for batch finalization setting
        batch_enabled = getattr(ExperimentalConfig, 'BATCH_FINALIZATION_ENABLED', False)
        if not batch_enabled:
            try:
                from .lib.config import Config as LibConfig
                batch_enabled = getattr(LibConfig, 'BATCH_FINALIZATION_ENABLED', False)
            except ImportError:
                pass

        final_folder = folder_path
        if batch_enabled and folder_path.endswith('__WORK'):
             print(f"[worker] ⏳ Skipping finalization (Batch Enabled) for {display_po}", flush=True)
             final_folder = folder_path
        else:
            try:
                final_folder = folder_manager.finalize_folder(folder_path, status_code)
            except Exception:
                final_folder = _legacy_rename_folder_with_status(folder_path, status_code)
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

        # Persist to CSV incrementally (new handler API) if available
        if csv_handler:
            try:
                attachment_names_list = result_payload.get('attachment_names', []) or []
                attachment_names_str = ', '.join(attachment_names_list)
                updates = {
                    'STATUS': result_payload.get('status_code', status_code),
                    'SUPPLIER': result_payload.get('supplier_name', ''),
                    'ATTACHMENTS_FOUND': result_payload.get('attachments_found', 0),
                    'ATTACHMENTS_DOWNLOADED': result_payload.get('attachments_downloaded', 0),
                    'AttachmentName': attachment_names_str,
                    'ERROR_MESSAGE': message,
                    'DOWNLOAD_FOLDER': final_folder,
                    'COUPA_URL': result_payload.get('coupa_url', ''),
                }
                csv_handler.update_record(display_po, updates)
                print(f"[worker] 💾 Incremental CSV update (parallel) for {display_po}", flush=True)
            except Exception as e:
                print(f"[worker] ⚠️ Failed incremental CSV update: {e}", flush=True)

        print(f"[worker] 🏁 Done {display_po} → {status_code}", flush=True)
        return result
    except Exception as e:
        try:
            # Attempt rename with FAILED suffix even on exceptions
            if folder_path:
                try:
                    # Only finalize if batching is disabled or not a WORK folder
                    batch_enabled = getattr(ExperimentalConfig, 'BATCH_FINALIZATION_ENABLED', False)
                    if not batch_enabled:
                        try:
                            from .lib.config import Config as LibConfig
                            batch_enabled = getattr(LibConfig, 'BATCH_FINALIZATION_ENABLED', False)
                        except ImportError:
                            pass
                    
                    if batch_enabled and folder_path.endswith('__WORK'):
                         final_folder = folder_path
                    else:
                        try:
                            final_folder = folder_manager.finalize_folder(folder_path, 'FAILED')
                        except Exception:
                            final_folder = _legacy_rename_folder_with_status(folder_path, 'FAILED')
                except Exception:
                     final_folder = folder_path or ''
            else:
                final_folder = ''
        except Exception:
            final_folder = folder_path or ''
        friendly = _humanize_exception(e)

        # Persist failed result to CSV if handler available (incremental model)
        if csv_handler:
            try:
                updates = {
                    'STATUS': 'FAILED',
                    'SUPPLIER': po_data.get('supplier', ''),
                    'ATTACHMENTS_FOUND': 0,
                    'ATTACHMENTS_DOWNLOADED': 0,
                    'AttachmentName': '',
                    'ERROR_MESSAGE': friendly,
                    'DOWNLOAD_FOLDER': final_folder,
                    'COUPA_URL': po_data.get('coupa_url', ''),
                }
                csv_handler.update_record(display_po, updates)
                print(f"[worker] 💾 Incremental CSV update (failed) for {display_po}", flush=True)
            except Exception as csv_e:
                print(f"[worker] ⚠️ Failed incremental CSV update (failed path): {csv_e}", flush=True)

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
        if output_handle:
            try:
                output_handle.close()
            except Exception:
                pass


def process_reusable_worker(args):
    """Run a reusable worker that processes multiple POs from a shared queue, with persistent Edge driver.

    Args tuple: (po_queue, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path, worker_id, communication_manager, sqlite_db_path, execution_mode)
    Returns: list of results for all processed POs
    """
    from pathlib import Path

    # Add the project root to Python path for spawned processes
    project_root = Path(__file__).resolve().parents[2]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    # Add EXPERIMENTAL directory to path
    experimental_root = Path(__file__).resolve().parents[1]
    experimental_root_str = str(experimental_root)
    if experimental_root_str not in sys.path:
        sys.path.insert(0, experimental_root_str)

    if len(args) >= 10:
        po_queue, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path, worker_id, communication_manager, sqlite_db_path, execution_mode = args[:10]
    else:
        po_queue, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path, worker_id, communication_manager, sqlite_db_path = args[:9]
        execution_mode = "standard"

    output_handle = None
    suppress_output = os.environ.get('SUPPRESS_WORKER_OUTPUT', '').strip().lower() in {'1', 'true', 'yes'}
    if suppress_output:
        try:
            output_handle = open(os.devnull, 'w')
            # Forceful redirection at OS level to catch sub-processes and loggers
            os.dup2(output_handle.fileno(), sys.stdout.fileno())
            os.dup2(output_handle.fileno(), sys.stderr.fileno())
            
            # Update Python's sys objects as well
            sys.stdout = output_handle
            sys.stderr = output_handle
            
            # Silence logging root handlers if they exist
            import logging
            logging.getLogger().handlers = []
            logging.basicConfig(stream=output_handle, force=True, level=logging.INFO)
        except Exception:
            output_handle = None

    download_root = os.path.abspath(os.path.expanduser(download_root)) if download_root else os.path.abspath(os.path.expanduser(ExperimentalConfig.DOWNLOAD_FOLDER))
    os.environ['DOWNLOAD_FOLDER'] = download_root
    try:
        ExperimentalConfig.DOWNLOAD_FOLDER = download_root
        from .lib.config import Config
        Config.DOWNLOAD_FOLDER = download_root
    except Exception:
        pass

    folder_manager = FolderHierarchyManager()
    browser_manager = BrowserManager()
    driver = None
    clone_dir = ''

    # Initialize CSV handler if path provided
    csv_handler = None
    if csv_path:
        try:
            from .core.csv_handler import CSVHandler
            csv_handler = CSVHandler(Path(csv_path), sqlite_db_path=sqlite_db_path)
            print(f"[reusable_worker_{worker_id}] 📊 CSV handler initialized for {csv_path} (SQLite: {sqlite_db_path})", flush=True)
        except Exception as e:
            print(f"[reusable_worker_{worker_id}] ⚠️ Failed to initialize CSV handler: {e}", flush=True)

    # Log headless configuration for this worker
    print(f"[reusable_worker_{worker_id}] 🎯 Headless configuration: {headless_config}", flush=True)

    results = []  # Store all results from this worker

    try:
        # Clone and load the selected profile for this worker (isolated user-data-dir)
        # This ensures authentication for ALL modes (Playwright, Direct HTTP, and standard Selenium)
        try:
            base_ud = os.path.expanduser(ExperimentalConfig.EDGE_PROFILE_DIR)
            profile_name = ExperimentalConfig.EDGE_PROFILE_NAME or 'Default'
            session_root = os.path.join(tempfile.gettempdir(), 'edge_profile_clones')
            _ensure_dir(session_root)
            clone_dir = os.path.join(session_root, f"reusable_worker_{worker_id}_{os.getpid()}")
            _create_profile_clone(base_ud, profile_name, clone_dir)
            # Point config to the clone so BrowserManager uses it
            ExperimentalConfig.USE_PROFILE = True
            ExperimentalConfig.EDGE_PROFILE_DIR = clone_dir
            ExperimentalConfig.EDGE_PROFILE_NAME = profile_name
            print(f"[reusable_worker_{worker_id}] 🔐 Profile cloned to: {clone_dir}", flush=True)
        except Exception as e:
            print(f"[reusable_worker_{worker_id}] ⚠️ Profile clone failed, continuing without profile: {e}", flush=True)
            clone_dir = ''
            try:
                # Ensure we don't point to a broken dir
                ExperimentalConfig.EDGE_PROFILE_DIR = ''
            except Exception:
                pass

        # Mode-specific initialization
        pw_manager = None
        playwright_page = None
        httpx_cookies = None
        
        mode_str = getattr(execution_mode, 'value', str(execution_mode))
        print(f"[reusable_worker_{worker_id}] 🔍 DEBUG: execution_mode={execution_mode}, type={type(execution_mode)}, mode_str='{mode_str}'", flush=True)
        print(f"[reusable_worker_{worker_id}] 🔍 DEBUG: mode_str in ('filtered', 'no_js') = {mode_str in ('filtered', 'no_js')}", flush=True)
        
        if mode_str in ("filtered", "no_js"):
            print(f"[reusable_worker_{worker_id}] 🛡️ Using Playwright for mode: {execution_mode}", flush=True)
            from .lib.playwright_manager import PlaywrightManager
            pw_manager = PlaywrightManager()
            playwright_page = pw_manager.start(
                headless=headless_config.get_effective_headless_mode(), 
                execution_mode=execution_mode,
                profile_dir=clone_dir
            )
        
        elif mode_str == "direct_http":
            print(f"[reusable_worker_{worker_id}] 🚀 Getting cookies for Direct HTTP (Turbo)...", flush=True)
            browser_manager.initialize_driver_with_profile(
                headless=headless_config.get_effective_headless_mode(),
                profile_dir=clone_dir,
                download_dir=download_root
            )
            driver = browser_manager.driver
            # Navigate to get cookies
            from .lib.config import Config as LibConfig
            driver.get(LibConfig.BASE_URL)
            selenium_cookies = driver.get_cookies()
            httpx_cookies = {c['name']: c['value'] for c in selenium_cookies}
            print(f"[reusable_worker_{worker_id}] 🍪 Cookies captured, releasing browser.", flush=True)
            browser_manager.cleanup()
            driver = None
        
        else:
            # Standard Selenium
            browser_manager.initialize_driver_with_profile(
                headless=headless_config.get_effective_headless_mode(),
                profile_dir=clone_dir,
                download_dir=download_root
            )
            driver = browser_manager.driver
            print(f"[reusable_worker_{worker_id}] ⚙️ Persistent Selenium WebDriver initialized", flush=True)

        # Process POs from the shared queue until it's empty
        po_count = 0
        while True:
            try:
                # Get next PO from queue (non-blocking)
                po_data = po_queue.get_nowait()
                po_count += 1
                display_po = po_data['po_number']

                print(f"[reusable_worker_{worker_id}] ▶ Processing PO {display_po} (#{po_count})", flush=True)

                # Create folder path without creating directory (JIT)
                folder_path = folder_manager.create_folder_path(po_data, hierarchy_cols, has_hierarchy_data, create_dir=False)
                
                # Callback to create folder when attachments are found
                def _ensure_folder_exists(_findings=None):
                    try:
                        os.makedirs(folder_path, exist_ok=True)
                        return folder_path
                    except Exception as e:
                        print(f"[reusable_worker_{worker_id}] ⚠️ Failed to create JIT folder: {e}", flush=True)
                        return folder_path
                
                # Setup progress emitter
                start_time = time.time()
                def _emit_progress(payload: Dict[str, Any]) -> None:
                    if not communication_manager:
                        return
                    try:
                        duration = time.time() - start_time
                        metric_data = {
                            'worker_id': worker_id,
                            'po_id': display_po,
                            'status': payload.get('status', 'PROCESSING'),
                            'timestamp': time.time(),
                            'duration': duration,
                            'attachments_found': payload.get('attachments_found', 0),
                            'attachments_downloaded': payload.get('attachments_downloaded', 0),
                            'message': payload.get('message', ''),
                        }
                        communication_manager.send_metric(metric_data)
                    except Exception:
                        pass

                # Selection of downloader
                if playwright_page:
                    from .lib.playwright_downloader import PlaywrightDownloader
                    downloader = PlaywrightDownloader(playwright_page, progress_callback=_emit_progress)
                    print(f"[reusable_worker_{worker_id}] 🌐 Starting Playwright download for {display_po}", flush=True)
                    result_payload = downloader.download_attachments_for_po(display_po, on_attachments_found=_ensure_folder_exists)
                
                elif httpx_cookies:
                    from .lib.direct_http_downloader import DirectHTTPDownloader
                    downloader = DirectHTTPDownloader(httpx_cookies, progress_callback=_emit_progress)
                    print(f"[reusable_worker_{worker_id}] 🌐 Starting Direct HTTP download for {display_po}", flush=True)
                    result_payload = downloader.download_attachments_for_po(display_po, on_attachments_found=_ensure_folder_exists)
                    downloader.close() # Close client for each PO or keep? Keeping is better for performance? 
                    # Actually creation of client is cheap enough here compared to other overheads.
                
                else:
                    # Selenium
                    browser_manager.update_download_directory(folder_path)
                    from .lib.downloader import Downloader
                    downloader = Downloader(driver, browser_manager, progress_callback=_emit_progress)
                    print(f"[reusable_worker_{worker_id}] 🌐 Starting Selenium download for {display_po}", flush=True)
                    # Pass on_attachments_found callback for JIT folder creation
                    result_payload = downloader.download_attachments_for_po(display_po, on_attachments_found=_ensure_folder_exists)

                message = result_payload.get('message', '')
                print(f"[reusable_worker_{worker_id}] ✅ Download routine finished for {display_po}", flush=True)

                # Wait for downloads to finish
                _wait_for_downloads_complete(folder_path, expected_count=result_payload.get('attachments_downloaded'))
                print(f"[reusable_worker_{worker_id}] ⏳ Downloads settled for {display_po}", flush=True)

                # Calculate duration
                duration = time.time() - start_time

                # Send completion metric
                if communication_manager:
                    try:
                        metric_data = {
                            'worker_id': worker_id,
                            'po_id': display_po,
                            'status': result_payload.get('status_code', 'COMPLETED'),
                            'timestamp': time.time(),
                            'duration': duration,
                            'attachments_found': result_payload.get('attachments_found', 0),
                            'attachments_downloaded': result_payload.get('attachments_downloaded', 0),
                            'message': message
                        }
                        communication_manager.send_metric(metric_data)
                    except Exception as e:
                        print(f"[reusable_worker_{worker_id}] ⚠️ Failed to send completion metric: {e}")

                status_code = _derive_status_label(result_payload)
                
                # Check for batch finalization setting
                batch_enabled = getattr(ExperimentalConfig, 'BATCH_FINALIZATION_ENABLED', False)
                # Also check standard Config if not in Experimental
                if not batch_enabled:
                    try:
                        from .lib.config import Config
                        batch_enabled = getattr(Config, 'BATCH_FINALIZATION_ENABLED', False)
                    except ImportError:
                        pass

                final_folder = folder_path
                if batch_enabled and folder_path.endswith('__WORK'):
                     # Skip finalization here; let the batch loop handle it (if running)
                     # Check if we should warn? We assume a batch finalizer is running elsewhere.
                     print(f"[reusable_worker_{worker_id}] ⏳ Skipping finalization (Batch Enabled) for {display_po}", flush=True)
                     # Ensure we return the __WORK path so it can be picked up
                     final_folder = folder_path
                     # We must NOT rename it here.
                else:
                    try:
                        final_folder = folder_manager.finalize_folder(folder_path, status_code)
                    except Exception:
                        final_folder = _legacy_rename_folder_with_status(folder_path, status_code)

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

                # Send metrics to communication manager
                if communication_manager:
                    try:
                        metric_data = {
                            'worker_id': worker_id,
                            'po_id': display_po,
                            'status': status_code,
                            'timestamp': time.time(),
                            'duration': duration,
                            'attachments_found': result_payload.get('attachments_found', 0),
                            'attachments_downloaded': result_payload.get('attachments_downloaded', 0),
                            'message': message
                        }
                        communication_manager.send_metric(metric_data)
                        
                        # Signal real-time finalization if this was a WORK folder
                        if communication_manager and final_folder and final_folder.endswith('__WORK'):
                            communication_manager.signal_finalization(final_folder, status_code)
                    except Exception as e:
                        print(f"[reusable_worker_{worker_id}] ⚠️ Failed to send metric: {e}")

                # Persist to CSV incrementally (new handler API) if available
                if csv_handler:
                    try:
                        attachment_names_list = result_payload.get('attachment_names', []) or []
                        attachment_names_str = ', '.join(attachment_names_list)
                        updates = {
                            'STATUS': result_payload.get('status_code', status_code),
                            'SUPPLIER': result_payload.get('supplier_name', ''),
                            'ATTACHMENTS_FOUND': result_payload.get('attachments_found', 0),
                            'ATTACHMENTS_DOWNLOADED': result_payload.get('attachments_downloaded', 0),
                            'AttachmentName': attachment_names_str,
                            'ERROR_MESSAGE': message,
                            'DOWNLOAD_FOLDER': final_folder,
                            'COUPA_URL': result_payload.get('coupa_url', ''),
                        }
                        csv_handler.update_record(display_po, updates)
                        print(f"[reusable_worker_{worker_id}] 💾 Incremental CSV update for {display_po}", flush=True)
                    except Exception as e:
                        print(f"[reusable_worker_{worker_id}] ⚠️ Failed incremental CSV update: {e}", flush=True)

                print(f"[reusable_worker_{worker_id}] 🏁 Done {display_po} → {status_code}", flush=True)

                # Add result to list
                results.append(result)

                # Clear session between POs to prevent contamination
                if hasattr(browser_manager, 'clear_session'):
                    browser_manager.clear_session()

            except queue.Empty:
                # Queue is empty, break the loop
                print(f"[reusable_worker_{worker_id}] Queue empty, worker finishing after processing {po_count} POs", flush=True)
                break
            except Exception as e:
                # Log unexpected error but CONTINUE processing the next PO!
                print(f"[reusable_worker_{worker_id}] ❌ Unexpected error processing PO: {e}", flush=True)
                import traceback
                traceback.print_exc()
                # If it's a critical browser error, we might want to break, but let's try to continue first.
                # However, if it's the SAME PO causing issues, we need to avoid infinite retry.
                # Since we already called get_nowait(), the PO is popped. We can just continue.
                continue

    except Exception as e:
        print(f"[reusable_worker_{worker_id}] ❌ Worker failed: {e}")
        # Add error result if we have a specific PO that caused the error
        if 'display_po' in locals():
            results.append({
                'po_number_display': display_po,
                'status_code': 'FAILED',
                'message': str(e),
                'final_folder': '',
                'status_reason': 'UNEXPECTED_EXCEPTION',
                'errors': [{'filename': '', 'reason': str(e)}],
                'success': False,
            })

    finally:
        try:
            browser_manager.cleanup()
        except Exception:
            pass

        # Cleanup Playwright if used
        try:
            if 'pw_manager' in locals() and pw_manager:
                pw_manager.cleanup()
        except Exception:
            pass

        # Best-effort cleanup of clone directory
        if clone_dir:
            try:
                shutil.rmtree(clone_dir, ignore_errors=True)
            except Exception:
                pass
        if output_handle:
            try:
                output_handle.close()
            except Exception:
                pass

    return results


class WorkerManager:
    """
    Manages PO processing workers and execution modes.
    Handles both parallel (process pool) and sequential processing.
    """

    def __init__(self, enable_parallel: bool = True, max_workers: int = 4, stagger_delay: float = 0.5):
        """
        Initialize WorkerManager with optional parallel processing support.

        Args:
            enable_parallel: Whether to enable parallel processing for multiple POs
            max_workers: Maximum number of parallel workers (>=1). No implicit hard cap.
        """
        # Validate parallel processing parameters
        if not isinstance(enable_parallel, bool):
            raise TypeError("enable_parallel must be a boolean")

        if not (isinstance(max_workers, int) and max_workers >= 1):
            raise ValueError(f"max_workers must be a positive integer, got {max_workers}")

        # Parallel processing configuration
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.stagger_delay = stagger_delay
        self._processing_session: Optional[ProcessingSession] = None
        self._last_parallel_report: Optional[Dict[str, Any]] = None
        self._active_executor = None  # Track ProcessPoolExecutor for shutdown

    def shutdown(self, wait: bool = True, emergency: bool = False):
        """
        Shutdown the worker manager and release resources.
        
        Args:
            wait: Whether to wait for pending tasks to complete
            emergency: If True, skip graceful shutdown and exit immediately
        """
        print(f"🔄 WorkerManager shutdown initiated (emergency={emergency})...")
        
        # Shutdown ProcessingSession if active
        if self._processing_session:
            try:
                self._processing_session.stop_processing(emergency=emergency)
            except Exception as e:
                print(f"⚠️ Error stopping processing session: {e}")
            self._processing_session = None
        
        # Note: ProcessPoolExecutor manages its own lifecycle
        # We just clear our reference here
        self._active_executor = None
        
        print("✅ WorkerManager shutdown complete")

    def process_pos(
        self,
        po_data_list: list[dict],
        hierarchy_cols: list[str],
        has_hierarchy_data: bool,
        headless_config,
        storage_manager=None,
        folder_manager=None,
        messenger=None,
        sqlite_db_path: Optional[str] = None,
        execution_mode: Any = None,
    ) -> tuple[int, int, dict]:
        """
        Public entry point for parallel processing called by ProcessingController.

        Routes to process_parallel_with_reusable_workers using a shared Queue.
        """
        import multiprocessing as _mp
        # Use Manager().Queue() for spawn compatibility on macOS
        # Regular mp.Queue() can't be shared between spawned processes
        manager = _mp.Manager()
        po_queue: _mp.Queue = manager.Queue()
        for po in po_data_list:
            po_queue.put(po)
        return self.process_parallel_with_reusable_workers(
            po_queue=po_queue,
            hierarchy_cols=hierarchy_cols,
            has_hierarchy_data=has_hierarchy_data,
            headless_config=headless_config,
            communication_manager=messenger,
            queue_size=len(po_data_list),
            csv_handler=storage_manager,
            folder_hierarchy=folder_manager,
            sqlite_db_path=sqlite_db_path,
            execution_mode=execution_mode,
        )

    def process_parallel_with_session(
        self,
        po_data_list: list[dict],
        hierarchy_cols: list[str],
        has_hierarchy_data: bool,
        headless_config: HeadlessConfiguration,
        csv_handler: Optional[CSVHandler] = None,
        folder_hierarchy: Optional[FolderHierarchyManager] = None,
        sqlite_db_path: Optional[str] = None,
        execution_mode: Any = None,
        communication_manager: Optional[Any] = None,
    ) -> tuple[int, int, dict]:
        """
        Process PO entries using ProcessingSession for intelligent parallel processing.

        Returns:
            tuple: (successful_count, failed_count, session_report)
        """
        try:
            print(f"🚀 Using ProcessingSession with parallel processing ({self.max_workers} workers)")

            # Create ProcessingSession for intelligent mode selection
            self._processing_session = ProcessingSession(
                headless_config=headless_config,
                enable_parallel=self.enable_parallel,
                max_workers=self.max_workers,
                progress_callback=None,  # Will be set by caller if needed
                hierarchy_columns=hierarchy_cols,
                has_hierarchy_data=has_hierarchy_data,
                stagger_delay=self.stagger_delay,
                execution_mode=execution_mode,
                communication_manager=communication_manager,
            )

            # Configure CSV path for workers if CSV handler is available
            if csv_handler and hasattr(csv_handler, 'csv_path'):
                self._processing_session.set_csv_path(str(csv_handler.csv_path))
            
            # Configure SQLite DB path for workers if available
            effective_sqlite_db_path = sqlite_db_path
            if not effective_sqlite_db_path and csv_handler and hasattr(csv_handler, 'sqlite_db_path') and csv_handler.sqlite_db_path:
                effective_sqlite_db_path = str(csv_handler.sqlite_db_path)
            if effective_sqlite_db_path:
                self._processing_session.set_sqlite_db_path(effective_sqlite_db_path)

            # Convert po_data_list to the format expected by ProcessingSession
            processed_po_list = []
            for po_data in po_data_list:
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

            # Update CSV with results
            self._update_csv_from_session_results(
                session_report, csv_handler, folder_hierarchy or FolderHierarchyManager()
            )

            return successful, failed, session_report

        except Exception as e:
            print(f"⚠️  ProcessingSession failed: {e}")
            raise

    def process_parallel_with_reusable_workers(
        self,
        po_queue: mp.Queue,
        hierarchy_cols: list[str],
        has_hierarchy_data: bool,
        headless_config: HeadlessConfiguration,
        communication_manager,
        queue_size: Optional[int] = None,
        csv_handler: Optional[CSVHandler] = None,
        folder_hierarchy: Optional[FolderHierarchyManager] = None,
        sqlite_db_path: Optional[str] = None,
        execution_mode: Any = None,
    ) -> tuple[int, int, dict]:
        """
        Process PO entries using reusable workers that compete for POs from a shared queue.
        Each worker initializes a driver once and processes multiple POs.

        Args:
            po_queue: Shared queue containing PO data to process
            hierarchy_cols: Hierarchy columns for folder structure
            has_hierarchy_data: Whether hierarchy data is available
            headless_config: Headless configuration
            communication_manager: Communication manager for metrics
            csv_handler: CSV handler for incremental updates
            folder_hierarchy: Folder hierarchy manager
            sqlite_db_path: Optional SQLite DB path for persistence

        Returns:
            tuple: (successful_count, failed_count, session_report)
        """
        from .core.communication_manager import CommunicationManager

        successful = 0
        failed = 0
        results: List[Dict[str, Any]] = []

        # Calculate number of workers
        if queue_size is not None:
            num_workers = min(self.max_workers, max(1, queue_size))
        else:
            try:
                queue_len = po_queue.qsize() if hasattr(po_queue, 'qsize') else None
            except (NotImplementedError, OSError):
                queue_len = None
            num_workers = min(self.max_workers, queue_len) if queue_len else self.max_workers
        print(f"📊 Using {num_workers} reusable worker(s), each with persistent driver")

        # Global safeguard: Ensure workers are silent when UI is active to prevent TTY pollution
        if communication_manager:
            os.environ['SUPPRESS_WORKER_OUTPUT'] = 'true'

        # Use the ExperimentalConfig.DOWNLOAD_FOLDER that was updated during setup
        from .lib.config import Config as ExperimentalConfig
        download_root = os.path.abspath(os.path.expanduser(ExperimentalConfig.DOWNLOAD_FOLDER))

        # Use incoming sqlite_db_path or derive from handler
        effective_sqlite_db_path = sqlite_db_path
        if not effective_sqlite_db_path and csv_handler and hasattr(csv_handler, 'sqlite_db_path'):
            effective_sqlite_db_path = csv_handler.sqlite_db_path

        # --- Batch Finalization Setup ---
        finalization_queue = queue.Queue()
        stop_finalizer = threading.Event()

        def _batch_finalizer_thread():
            """Background thread to batch finalize folders."""
            interval = getattr(ExperimentalConfig, 'BATCH_FINALIZATION_INTERVAL', 30)
            print(f"🔄 Batch finalizer thread started (Interval: {interval}s)")
            
            while not stop_finalizer.is_set():
                try:
                    # Collect pending items
                    batch = []
                    while True:
                        try:
                            item = finalization_queue.get_nowait()
                            batch.append(item)
                        except queue.Empty:
                            break
                    
                    if batch:
                        if folder_hierarchy:
                            print(f"📦 Batch finalizing {len(batch)} folders...")
                            for folder_path, status_code in batch:
                                try:
                                    folder_hierarchy.finalize_folder(folder_path, status_code)
                                except Exception as e:
                                    print(f"⚠️ Batch finalization failed for {folder_path}: {e}")
                                    # Fallback
                                    try:
                                        _legacy_rename_folder_with_status(folder_path, status_code)
                                    except:
                                        pass
                    
                    # Sleep for interval or untill stopped
                    stop_finalizer.wait(timeout=interval)
                    
                except Exception as e:
                    print(f"⚠️ Error in batch finalizer thread: {e}")
                    time.sleep(1)

        final_thread = threading.Thread(target=_batch_finalizer_thread, daemon=True)
        final_thread.start()
        # -------------------------------

        try:
            with ProcessPoolExecutor(max_workers=num_workers, mp_context=mp.get_context("spawn")) as executor:
                # Submit initial tasks for each worker
                future_map: dict = {}
                try:
                    with open('/tmp/worker_debug.log', 'a') as f:
                        f.write(f"[WORKER_MANAGER] Using ProcessPoolExecutor (Legacy Path). Workers: {num_workers}\n")
                except:
                    pass

                # Submit initial tasks equal to number of workers
                for i in range(num_workers):
                    # Determine CSV path for worker
                    csv_path = None
                    if csv_handler and hasattr(csv_handler, 'csv_path'):
                        csv_path = str(csv_handler.csv_path)

                    task_args = (
                        po_queue,
                        hierarchy_cols,
                        has_hierarchy_data,
                        headless_config,
                        download_root,
                        csv_path,
                        i,  # worker_id
                        communication_manager,
                        effective_sqlite_db_path,
                        execution_mode.value if hasattr(execution_mode, 'value') else str(execution_mode) if execution_mode else "standard"
                    )

                    future = executor.submit(process_reusable_worker, task_args)
                    future_map[future] = i  # Track worker ID

                # Collect results as workers complete tasks
                for future in as_completed(future_map):
                    worker_id = future_map[future]

                    try:
                        worker_results = future.result()

                        # Process results from this worker
                        for result in worker_results:
                            # Handle batch finalization queueing
                            final_folder = result.get('final_folder')
                            status_code = result.get('status_code', 'COMPLETED')
                            if final_folder and final_folder.endswith('__WORK'):
                                 # Queue for finalization
                                 finalization_queue.put((final_folder, status_code))
                            
                            results.append(result)

                            if result.get('success', False) or result.get('status_code') in {'COMPLETED', 'NO_ATTACHMENTS'}:
                                successful += 1
                            else:
                                failed += 1

                    except Exception as exc:
                        print(f"❌ Worker {worker_id} failed: {exc}")
                        failed += 1

        finally:
             # Stop finalizer thread
             stop_finalizer.set()
             final_thread.join(timeout=5)
             
             # Process any remaining items in queue
             while not finalization_queue.empty():
                 try:
                     folder_path, status_code = finalization_queue.get_nowait()
                     if folder_hierarchy:
                         try:
                             folder_hierarchy.finalize_folder(folder_path, status_code)
                         except:
                             _legacy_rename_folder_with_status(folder_path, status_code)
                 except:
                     break

        session_report = {
            'processing_mode': 'parallel_reusable_workers',
            'worker_count': num_workers,
            'session_duration': (datetime.now() - datetime.now()).total_seconds(),  # Placeholder
            'results': results,
        }

        return successful, failed, session_report

    def process_parallel_legacy(
        self,
        po_data_list: list[dict],
        hierarchy_cols: list[str],
        has_hierarchy_data: bool,
        headless_config: HeadlessConfiguration,
        csv_handler: Optional[CSVHandler] = None,
        folder_hierarchy: Optional[FolderHierarchyManager] = None,
        sqlite_db_path: Optional[str] = None,
        execution_mode: Any = None,
    ) -> tuple[int, int, dict]:
        """
        Process PO entries using legacy ProcessPoolExecutor approach.

        Returns:
            tuple: (successful_count, failed_count)
        """
        successful = 0
        failed = 0

        default_workers = min(2, len(po_data_list))
        from .lib.config import Config as ExperimentalConfig
        env_procs = int(getattr(ExperimentalConfig, 'PROC_WORKERS', default_workers))
        hard_cap = int(getattr(ExperimentalConfig, 'PROC_WORKERS_CAP', 0) or 0)
        if hard_cap > 0:
            proc_workers = max(1, min(env_procs, hard_cap, len(po_data_list)))
        else:
            proc_workers = max(1, min(env_procs, len(po_data_list)))
        print(f"📊 Using {proc_workers} process worker(s) (cap={'unlimited' if hard_cap == 0 else hard_cap}), one WebDriver per process")

        # Use the ExperimentalConfig.DOWNLOAD_FOLDER that was updated during setup
        download_root = os.path.abspath(os.path.expanduser(ExperimentalConfig.DOWNLOAD_FOLDER))

        # --- Batch Finalization Setup ---
        finalization_queue = queue.Queue()
        stop_finalizer = threading.Event()

        def _batch_finalizer_thread():
            """Background thread to batch finalize folders."""
            interval = getattr(ExperimentalConfig, 'BATCH_FINALIZATION_INTERVAL', 30)
            print(f"🔄 (Legacy) Batch finalizer thread started (Interval: {interval}s)")
            
            while not stop_finalizer.is_set():
                try:
                    # Collect pending items
                    batch = []
                    while True:
                        try:
                            item = finalization_queue.get_nowait()
                            batch.append(item)
                        except queue.Empty:
                            break
                    
                    if batch:
                        if folder_hierarchy:
                            print(f"📦 (Legacy) Batch finalizing {len(batch)} folders...")
                            for folder_path, status_code in batch:
                                try:
                                    folder_hierarchy.finalize_folder(folder_path, status_code)
                                except Exception as e:
                                    print(f"⚠️ Batch finalization failed for {folder_path}: {e}")
                                    try:
                                        _legacy_rename_folder_with_status(folder_path, status_code)
                                    except:
                                        pass
                    
                    stop_finalizer.wait(timeout=interval)
                except Exception as e:
                    print(f"⚠️ Error in legacy batch finalizer thread: {e}")
                    time.sleep(1)

        final_thread = threading.Thread(target=_batch_finalizer_thread, daemon=True)
        final_thread.start()
        # -------------------------------

        try:
            with ProcessPoolExecutor(max_workers=proc_workers, mp_context=mp.get_context("spawn")) as executor:
                future_map: dict = {}
                for po_data in po_data_list:
                    if po_data.get('po_number'):
                        # Determine CSV path for worker
                        csv_path = None
                        if csv_handler and hasattr(csv_handler, 'csv_path'):
                            csv_path = str(csv_handler.csv_path)

                        future = executor.submit(
                            process_po_worker,
                            (po_data, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path, sqlite_db_path, execution_mode.value if hasattr(execution_mode, 'value') else str(execution_mode) if execution_mode else "standard"),
                        )
                        future_map[future] = po_data

                for future in as_completed(future_map):
                    po_data = future_map[future]
                    display_po = po_data.get('po_number', '')
                    try:
                        result = future.result()
                        
                        # Handle batch finalization queueing
                        final_folder = result.get('final_folder')
                        status_code = result.get('status_code', 'COMPLETED')
                        if final_folder and final_folder.endswith('__WORK'):
                             finalization_queue.put((final_folder, status_code))
                    except Exception as exc:
                        friendly = _humanize_exception(exc)
                        print("-" * 60)
                        print(f"   ❌ Worker error for {display_po}: {friendly}")
                        if csv_handler:
                            try:
                                csv_handler.update_record(display_po, {
                                    'STATUS': 'FAILED',
                                    'ERROR_MESSAGE': friendly,
                                })
                            except Exception as e:
                                print(f"[procpool] ⚠️ Failed incremental CSV update (worker error path): {e}")
                        failed += 1
                        continue

                    # Process successful result
                    successful += 1
                    self._process_worker_result(result, csv_handler, folder_hierarchy or FolderHierarchyManager())

        finally:
            # Stop finalizer thread
            stop_finalizer.set()
            final_thread.join(timeout=5)
            
            # Flush queue
            while not finalization_queue.empty():
                try:
                    folder_path, status_code = finalization_queue.get_nowait()
                    if folder_hierarchy:
                        try:
                            folder_hierarchy.finalize_folder(folder_path, status_code)
                        except:
                            _legacy_rename_folder_with_status(folder_path, status_code)
                except:
                    break

        return successful, failed

    def _update_csv_from_session_results(
        self,
        session_report: dict,
        csv_handler: Optional[CSVHandler],
        folder_hierarchy: FolderHierarchyManager
    ) -> None:
        """Update CSV with results from ProcessingSession."""
        results_payload = session_report.get('results', []) or []
        if not results_payload:
            return

        for result in results_payload:
            display_po = result.get('po_number_display') or result.get('po_number', '')
            status_code = result.get('status_code', 'FAILED')
            message = result.get('message', '')
            status_reason = result.get('status_reason', '')
            final_folder = result.get('final_folder', '')

            formatted_names = folder_hierarchy.format_attachment_names(
                result.get('attachment_names', [])
            )
            csv_message = self._compose_csv_message(result)

            if csv_handler:
                try:
                    csv_handler.update_record(display_po, {
                        'STATUS': status_code,
                        'SUPPLIER': result.get('supplier_name', ''),
                        'ATTACHMENTS_FOUND': result.get('attachments_found', 0),
                        'ATTACHMENTS_DOWNLOADED': result.get('attachments_downloaded', 0),
                        'AttachmentName': formatted_names,
                        'ERROR_MESSAGE': csv_message,
                        'DOWNLOAD_FOLDER': final_folder,
                        'COUPA_URL': result.get('coupa_url', ''),
                    })
                except Exception as e:
                    print(f"[parallel-session] ⚠️ Failed incremental CSV update: {e}")

            # Log result
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

    def _process_worker_result(
        self,
        result: dict,
        csv_handler: Optional[CSVHandler],
        folder_hierarchy: FolderHierarchyManager
    ) -> None:
        """Process a single worker result and update CSV."""
        display_po = result['po_number_display']
        status_code = result['status_code']
        message = result.get('message', '')
        final_folder = result.get('final_folder', '')
        status_reason = result.get('status_reason', '')

        formatted_names = folder_hierarchy.format_attachment_names(
            result.get('attachment_names', [])
        )
        csv_message = self._compose_csv_message(result)

        if csv_handler:
            try:
                csv_handler.update_record(display_po, {
                    'STATUS': status_code,
                    'SUPPLIER': result.get('supplier_name', ''),
                    'ATTACHMENTS_FOUND': result.get('attachments_found', 0),
                    'ATTACHMENTS_DOWNLOADED': result.get('attachments_downloaded', 0),
                    'AttachmentName': formatted_names,
                    'ERROR_MESSAGE': csv_message,
                    'DOWNLOAD_FOLDER': final_folder,
                    'COUPA_URL': result.get('coupa_url', ''),
                })
            except Exception as e:
                print(f"[procpool] ⚠️ Failed incremental CSV update: {e}")

        # Log result
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

    def _compose_csv_message(self, result: dict) -> str:
        """Compose a message for CSV logging from result dict."""
        message = result.get('message', '')
        status_reason = result.get('status_reason', '')
        if message and status_reason:
            return f"{message} ({status_reason})"
        return message or status_reason or result.get('status_code', 'UNKNOWN')
