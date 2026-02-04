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
                        from csv_handler import CSVHandler
                        from pathlib import Path
                        csv_handler = CSVHandler(Path(self.csv_path))
                        print(f"[PersistentWorkerPool] CSV handler created for: {self.csv_path}")
                    except Exception as e:
                        print(f"[PersistentWorkerPool] Failed to create CSV handler: {e}")
                self.worker_pool = PersistentWorkerPool(config, csv_handler=csv_handler)
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
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
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
                # Get status from task queue
                queue_stats = self.worker_pool.task_queue.get_queue_status()
                
                self.completed_tasks = queue_stats.get('completed_tasks', 0)
                self.failed_tasks = queue_stats.get('failed_tasks', 0)
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


def _legacy_rename_folder_with_status(folder_path: str, status_code: str) -> str:
    """Legacy fallback for folder renaming - now with aggressive __WORK normalization."""
    try:
        folder_name = os.path.basename(folder_path)
        parent_dir = os.path.dirname(folder_path)

        # Normalize __WORK suffix aggressively
        if folder_name.endswith('__WORK'):
            folder_name = folder_name[:-6]  # Remove __WORK

        suffix = _suffix_for_status(status_code)
        new_name = f"{folder_name}{suffix}"
        new_path = os.path.join(parent_dir, new_name)
        os.rename(folder_path, new_path)
        return new_path
    except Exception:
        return folder_path


def process_po_worker(args):
    """Run a single PO in its own process, with its own Edge driver.

    Args tuple: (po_data, hierarchy_cols, has_hierarchy_data, headless_config[, download_root, csv_path])
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
            csv_handler = CSVHandler(Path(csv_path))
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
                    final_folder = folder_manager.finalize_folder(folder_path, 'FAILED')
                except Exception:
                    final_folder = _legacy_rename_folder_with_status(folder_path, 'FAILED')
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

    Args tuple: (po_queue, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path, worker_id, communication_manager)
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

    po_queue, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path, worker_id, communication_manager = args

    output_handle = None
    suppress_output = os.environ.get('SUPPRESS_WORKER_OUTPUT', '').strip().lower() in {'1', 'true', 'yes'}
    if suppress_output:
        try:
            log_dir = os.path.join(tempfile.gettempdir(), 'coupadownloads_logs')
            _ensure_dir(log_dir)
            log_path = os.path.join(log_dir, f"worker_{worker_id}_{os.getpid()}.log")
            output_handle = open(log_path, 'a', buffering=1)
            sys.stdout = output_handle
            sys.stderr = output_handle
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
            csv_handler = CSVHandler(Path(csv_path))
            print(f"[reusable_worker_{worker_id}] 📊 CSV handler initialized for {csv_path}", flush=True)
        except Exception as e:
            print(f"[reusable_worker_{worker_id}] ⚠️ Failed to initialize CSV handler: {e}", flush=True)

    # Log headless configuration for this worker
    print(f"[reusable_worker_{worker_id}] 🎯 Headless configuration: {headless_config}", flush=True)

    results = []  # Store all results from this worker

    try:
        # Start browser for this worker once and reuse for multiple POs
        print(f"[reusable_worker_{worker_id}] 🚀 Initializing persistent WebDriver...", flush=True)
        # Clone and load the selected profile for this worker (isolated user-data-dir)
        try:
            base_ud = os.path.expanduser(ExperimentalConfig.EDGE_PROFILE_DIR)
            profile_name = ExperimentalConfig.EDGE_PROFILE_NAME or 'Default'
            session_root = os.path.join(tempfile.gettempdir(), 'edge_profile_clones')
            _ensure_dir(session_root)
            clone_dir = os.path.join(session_root, f"proc_{worker_id}_{os.getpid()}_{int(time.time()*1000)}")
            _create_profile_clone(base_ud, profile_name, clone_dir)
            # Point config to the clone so BrowserManager uses it
            ExperimentalConfig.USE_PROFILE = True
            ExperimentalConfig.EDGE_PROFILE_DIR = clone_dir
            ExperimentalConfig.EDGE_PROFILE_NAME = profile_name
        except Exception as e:
            print(f"[reusable_worker_{worker_id}] ⚠️ Profile clone failed, continuing without profile: {e}")
            try:
                # Ensure we don't point to a broken dir
                ExperimentalConfig.EDGE_PROFILE_DIR = ''
            except Exception:
                pass

        browser_manager.initialize_driver(headless=headless_config.get_effective_headless_mode())
        driver = browser_manager.driver
        print(f"[reusable_worker_{worker_id}] ⚙️ Persistent WebDriver initialized", flush=True)

        # Process POs from the shared queue until it's empty
        po_count = 0
        while True:
            try:
                # Get next PO from queue (non-blocking)
                po_data = po_queue.get_nowait()
                po_count += 1
                display_po = po_data['po_number']

                print(f"[reusable_worker_{worker_id}] ▶ Processing PO {display_po} (#{po_count})", flush=True)

                # Create folder without suffix
                folder_path = folder_manager.create_folder_path(po_data, hierarchy_cols, has_hierarchy_data)
                print(f"[reusable_worker_{worker_id}] 📁 Folder ready: {folder_path}", flush=True)

                # Set download directory for this PO
                browser_manager.update_download_directory(folder_path)
                print(f"[reusable_worker_{worker_id}] 📥 Download dir set for {display_po}", flush=True)

                # Send "starting" metric
                if communication_manager:
                    try:
                        metric_data = {
                            'worker_id': worker_id,
                            'po_id': display_po,
                            'status': 'STARTED',
                            'timestamp': time.time(),
                            'duration': 0.0,
                            'attachments_found': 0,
                            'attachments_downloaded': 0,
                            'message': f'Starting processing for {display_po}'
                        }
                        communication_manager.send_metric(metric_data)
                    except Exception as e:
                        print(f"[reusable_worker_{worker_id}] ⚠️ Failed to send STARTED metric: {e}")

                # Download
                def _emit_progress(payload: Dict[str, Any]) -> None:
                    if not communication_manager:
                        return
                    try:
                        duration = time.time() - start_time if start_time else 0.0
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

                downloader = Downloader(driver, browser_manager, progress_callback=_emit_progress)
                po_number = po_data['po_number']
                print(f"[reusable_worker_{worker_id}] 🌐 Starting download for {po_number}", flush=True)

                # Record start time for metrics
                start_time = time.time()

                result_payload = downloader.download_attachments_for_po(po_number)
                message = result_payload.get('message', '')
                print(f"[reusable_worker_{worker_id}] ✅ Download routine finished for {po_number}", flush=True)

                # Wait for downloads to finish
                _wait_for_downloads_complete(folder_path)
                print(f"[reusable_worker_{worker_id}] ⏳ Downloads settled for {po_number}", flush=True)

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

            except Exception as queue_empty:
                # Queue is empty, break the loop
                print(f"[reusable_worker_{worker_id}] Queue empty, worker finishing after processing {po_count} POs", flush=True)
                break

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
        # Best-effort cleanup of clone directory
        if clone_dir:
            try:
                shutil.rmtree(clone_dir, ignore_errors=True)
            except Exception:
                pass

    return results


class WorkerManager:
    """
    Manages PO processing workers and execution modes.
    Handles both parallel (process pool) and sequential processing.
    """

    def __init__(self, enable_parallel: bool = True, max_workers: int = 4):
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
        self._processing_session: Optional[ProcessingSession] = None
        self._last_parallel_report: Optional[Dict[str, Any]] = None

    def process_parallel_with_session(
        self,
        po_data_list: list[dict],
        hierarchy_cols: list[str],
        has_hierarchy_data: bool,
        headless_config: HeadlessConfiguration,
        csv_handler: Optional[CSVHandler] = None,
        folder_hierarchy: Optional[FolderHierarchyManager] = None,
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
            )

            # Configure CSV path for workers if CSV handler is available
            if csv_handler and hasattr(csv_handler, 'csv_path'):
                self._processing_session.set_csv_path(str(csv_handler.csv_path))

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

        # Use the ExperimentalConfig.DOWNLOAD_FOLDER that was updated during setup
        from .lib.config import Config as ExperimentalConfig
        download_root = os.path.abspath(os.path.expanduser(ExperimentalConfig.DOWNLOAD_FOLDER))

        with ProcessPoolExecutor(max_workers=num_workers, mp_context=mp.get_context("spawn")) as executor:
            # Submit initial tasks for each worker
            future_map: dict = {}

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
                    communication_manager
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
                        results.append(result)

                        if result.get('success', False) or result.get('status_code') in {'COMPLETED', 'NO_ATTACHMENTS'}:
                            successful += 1
                        else:
                            failed += 1

                except Exception as exc:
                    print(f"❌ Worker {worker_id} failed: {exc}")
                    failed += 1

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
    ) -> tuple[int, int]:
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
                        (po_data, hierarchy_cols, has_hierarchy_data, headless_config, download_root, csv_path),
                    )
                    future_map[future] = po_data

            for future in as_completed(future_map):
                po_data = future_map[future]
                display_po = po_data.get('po_number', '')
                try:
                    result = future.result()
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
