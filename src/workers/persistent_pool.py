"""
PersistentWorkerPool orchestrator for managing worker processes.

This module provides the main orchestrator class for the persistent worker pool
with support for:
- Dynamic worker process management
- Task queue coordination
- Resource monitoring and scaling
- Graceful shutdown handling
- Error recovery and resilience
"""

import asyncio
import multiprocessing as mp
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import structlog
import psutil

from .models import (
    PoolConfig, TaskHandle, POTask, Worker, Profile,
    TaskStatus, WorkerStatus, TaskPriority
)
from .worker_process import WorkerProcess
from .task_queue import TaskQueue, ProcessingTask, TaskResult
from .profile_manager import ProfileManager
from .shutdown_handler import GracefulShutdown
from ..core.protocols import StorageManager, Messenger

logger = structlog.get_logger(__name__)



# Debug helper
def _debug_log(msg: str):
    try:
        with open('/tmp/worker_debug.log', 'a') as f:
            import datetime
            ts = datetime.datetime.now().isoformat()
            f.write(f"[{ts}] [POOL] {msg}\n")
    except:
        pass

class PersistentWorkerPool:
    """
    Main orchestrator for the persistent worker pool.
    
    Manages a pool of persistent browser worker processes for efficient
    PO downloading with resource monitoring, dynamic scaling, and graceful shutdown.

        TIMEOUT handling enhancement:
        - Individual worker restart always triggered on RATE_LIMIT / ACCESS_DENIED / TIMEOUT
        - On TIMEOUT the pool attempts a global restart of all workers if the cooldown
            window (TIMEOUT_GLOBAL_RESTART_COOLDOWN, default 60s) has elapsed, to recover
            from systemic driver hangs or port starvation.
    """
    
    def __init__(
        self,
        config: PoolConfig,
        storage_manager: Optional[StorageManager] = None,
        result_callbacks: Optional[List[Callable[[POTask, Dict[str, Any]], None]]] = None,
        messenger: Optional[Messenger] = None,
    ):
        """
        Initialize the persistent worker pool.
        
        Args:
            config: Pool configuration and constraints
        """
        self.config = config
        self._validate_config()
        
        # Core components
        self.task_queue = TaskQueue()
        profile_cap = max(config.worker_count, 8)
        try:
            env_cap_val = os.environ.get('PERSISTENT_WORKERS_MAX')
            if env_cap_val:
                env_cap = int(env_cap_val)
                if env_cap > 0:
                    profile_cap = max(profile_cap, env_cap)
        except (TypeError, ValueError):
            pass

        self.profile_manager = ProfileManager(
            config.base_profile_path,
            base_profile_name=getattr(config, 'base_profile_name', None),
            max_profiles=profile_cap,
        )
        self.shutdown_handler = GracefulShutdown(config.shutdown_timeout)
        
        # Worker management
        self.workers: Dict[str, WorkerProcess] = {}
        self.worker_threads: Dict[str, threading.Thread] = {}
        self._po_tasks: Dict[str, POTask] = {}
        self._task_handles: Dict[str, TaskHandle] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # State tracking
        self._running = False
        self._startup_complete = False
        self._shutdown_initiated = False
        
        # Statistics
        self.start_time: Optional[float] = None
        self.completed_tasks = 0
        self.failed_tasks = 0

        # Transient/global restart coordination
        self._last_global_timeout_restart: Optional[float] = None
        try:
            self._timeout_global_restart_cooldown = float(os.environ.get('TIMEOUT_GLOBAL_RESTART_COOLDOWN', '60'))
        except Exception:
            self._timeout_global_restart_cooldown = 60.0
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=config.worker_count + 2)
        
        self.storage_manager = storage_manager
        self._result_callbacks: List[Callable[[POTask, Dict[str, Any]], None]] = []
        if result_callbacks:
            self._result_callbacks.extend(result_callbacks)
        if storage_manager is not None:
            self._result_callbacks.append(self._persist_result_to_csv)

        logger.info(
            "PersistentWorkerPool initialized",
            worker_count=config.worker_count,
            headless_mode=config.headless_mode,
            memory_threshold=config.memory_threshold,
            storage_manager_attached=storage_manager is not None,
            result_callback_count=len(self._result_callbacks),
        )

        # Pending finalization registry (PO_TASK, RESULT)
        self._pending_finalizations: List[tuple[POTask, Dict[str, Any]]] = []
        self._finalizer_lock = threading.Lock()
        self.messenger = messenger
    
    def _validate_config(self) -> None:
        """Validate pool configuration."""
        if not isinstance(self.config, PoolConfig):
            raise TypeError("Config must be a PoolConfig instance")
        
        # Additional runtime validation
        available_memory = psutil.virtual_memory().total
        threshold_bytes = self.config.get_memory_threshold_bytes(available_memory)
        
        if threshold_bytes > available_memory * 0.95:
            raise ValueError("Memory threshold too high for available system memory")
        
        logger.debug("Configuration validated", 
                    memory_threshold_gb=threshold_bytes // (1024**3))
    
    async def start(self) -> None:
        """
        Start the worker pool and initialize all components.
        
        Raises:
            RuntimeError: If pool is already running or startup fails
        """
        if self._running:
            raise RuntimeError("Worker pool is already running")
        
        try:
            logger.info("Starting PersistentWorkerPool...")
            _debug_log(f"Starting pool. Config execution_mode: {getattr(self.config, 'execution_mode', 'UNKNOWN')}")
            # Extended startup diagnostics (previous version had bad indentation causing error)
            env_cap = os.environ.get('PERSISTENT_WORKERS_MAX')
            logger.info(
                "PersistentWorkerPool startup parameters",
                requested_workers=self.config.worker_count,
                cpu_cores=mp.cpu_count(),
                env_cap=env_cap,
            )
            self.start_time = time.time()
            self._running = True
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None
            
            # Initialize components in order
            await self._initialize_profile_manager()
            await self._setup_shutdown_handlers()
            await self._start_workers()
            
            self._startup_complete = True
            
            # Start background tasks
            asyncio.create_task(self._monitor_worker_health())
            asyncio.create_task(self._process_task_queue())
            
            # Start batch finalizer if enabled
            from ..lib.config import Config
            if getattr(Config, 'BATCH_FINALIZATION_ENABLED', False):
                asyncio.create_task(self._batch_finalizer_loop())
            
            uptime = time.time() - self.start_time
            logger.info("PersistentWorkerPool started successfully", 
                       startup_time_seconds=f"{uptime:.2f}",
                       active_workers=len(self.workers))
            
        except Exception as e:
            self._running = False
            self._startup_complete = False
            logger.error("Failed to start PersistentWorkerPool", error=str(e))
            await self._emergency_cleanup()
            raise RuntimeError(f"Pool startup failed: {e}") from e

    def register_result_callback(
        self, callback: Callable[[POTask, Dict[str, Any]], None]
    ) -> None:
        """Register a callback invoked when a task finishes processing."""
        if callback not in self._result_callbacks:
            self._result_callbacks.append(callback)

    def _dispatch_task_result(self, po_task: POTask, result: Dict[str, Any]) -> None:
        """Notify registered callbacks about completed task results."""
        if not self._result_callbacks:
            return

        callbacks_snapshot = list(self._result_callbacks)
        for callback in callbacks_snapshot:
            try:
                callback(po_task, result)
            except Exception as callback_error:  # pragma: no cover - defensive logging
                logger.error(
                    "Result callback failed",
                    error=str(callback_error),
                    po_number=po_task.po_number,
                    callback=getattr(callback, "__name__", repr(callback)),
                )

    def _persist_result_to_csv(self, po_task: POTask, result: Dict[str, Any]) -> None:
        """Persist worker result into storage manager if configured."""
        if not self.storage_manager:
            return

        po_number = po_task.po_number or result.get("po_number")
        if not po_number:
            logger.warning("Skipping CSV update: missing PO number", task_id=po_task.task_id)
            return

        try:
            status_code = result.get("status_code") or ("COMPLETED" if result.get("success") else "FAILED")
            attachment_names = result.get("attachment_names") or []
            if isinstance(attachment_names, list):
                attachment_field = ";".join(str(name) for name in attachment_names if name)
            else:
                attachment_field = str(attachment_names)

            last_processed = datetime.utcnow().isoformat()

            # Track transient attempts if present
            rl_attempts = result.get('rate_limit_attempts') or result.get('rl_attempts') or ''
            to_attempts = result.get('timeout_attempts') or ''

            updates: Dict[str, Any] = {
                "STATUS": status_code,
                "ATTACHMENTS_FOUND": result.get("attachments_found", 0),
                "ATTACHMENTS_DOWNLOADED": result.get("attachments_downloaded", 0),
                "AttachmentName": attachment_field,
                "LAST_PROCESSED": last_processed,
                "DOWNLOAD_FOLDER": result.get("final_folder", ""),
                "COUPA_URL": result.get("coupa_url", ""),
                "ERROR_MESSAGE": "" if result.get("success") else result.get("message", ""),
            }
            if rl_attempts:
                try:
                    # Note: Leaky abstraction check, keeping for compatibility during refactoring
                    if hasattr(self.storage_manager, '_dataframe') and 'RATE_LIMIT_ATTEMPTS' in self.storage_manager._dataframe.columns:
                        updates['RATE_LIMIT_ATTEMPTS'] = rl_attempts
                except Exception:
                    pass
            if to_attempts:
                try:
                    if hasattr(self.storage_manager, '_dataframe') and 'TIMEOUT_ATTEMPTS' in self.storage_manager._dataframe.columns:
                        updates['TIMEOUT_ATTEMPTS'] = to_attempts
                except Exception:
                    pass

            supplier_name = result.get("supplier_name")
            if supplier_name:
                updates["SUPPLIER"] = supplier_name

            self.storage_manager.update_record(po_number, updates)
        except Exception as csv_error:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to update CSV record",
                error=str(csv_error),
                po_number=po_number,
            )
    
    async def _initialize_profile_manager(self) -> None:
        """Initialize profile manager and create base profiles."""
        logger.debug("Initializing ProfileManager...")
        
        if self.config.base_profile_path:
            # Set base profile path in profile manager
            self.profile_manager.set_base_profile(
                self.config.base_profile_path, 
                self.config.base_profile_name or "Default"
            )
        
        # Pre-create worker profiles
        for i in range(self.config.worker_count):
            worker_id = f"worker-{i+1}"
            profile_path = self.profile_manager.create_profile(worker_id)
            logger.debug("Created worker profile", worker_id=worker_id, 
                        profile_path=profile_path)
    

    async def _setup_shutdown_handlers(self) -> None:
        """Setup graceful shutdown signal handlers."""
        logger.debug("Setting up shutdown handlers...")
        
        def shutdown_callback():
            logger.info("Shutdown signal received")
            asyncio.create_task(self.shutdown())
        
        self.shutdown_handler.register_shutdown_callback(shutdown_callback)
        self.shutdown_handler.install_signal_handlers()
    
    async def _start_workers(self) -> None:
        """Start all worker processes."""
        logger.info("Starting worker processes...", count=self.config.worker_count)
        
        for i in range(self.config.worker_count):
            worker_id = f"worker-{i+1}"
            await self._start_worker(worker_id)
            
            # Apply stagger delay between worker starts (except for the last one)
            if i < self.config.worker_count - 1 and self.config.stagger_delay > 0:
                logger.debug(f"Waiting {self.config.stagger_delay}s before starting next worker", 
                             worker_id=worker_id)
                await asyncio.sleep(self.config.stagger_delay)
        
        # Wait for all workers to be ready
        max_wait = self.config.worker_startup_timeout
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            ready_workers = sum(1 for w in self.workers.values() 
                              if w.get_status()['status'] == WorkerStatus.READY.value)
            
            if ready_workers == self.config.worker_count:
                break
                
            await asyncio.sleep(0.5)
        
        ready_count = sum(1 for w in self.workers.values() 
                         if w.get_status()['status'] == WorkerStatus.READY.value)
        
        if ready_count < self.config.worker_count:
            logger.warning("Not all workers started successfully", 
                          ready=ready_count, expected=self.config.worker_count)
        else:
            logger.info("All workers started successfully", count=ready_count)
    
    async def _start_worker(self, worker_id: str) -> None:
        """Start a single worker process."""
        try:
            # Get or create worker profile path
            profile_path = self.profile_manager.get_profile_path(worker_id)
            if not profile_path or not os.path.isdir(profile_path):
                profile_path = self.profile_manager.create_profile(worker_id, force=True)
            elif not self.profile_manager.validate_profile(worker_id):
                self.profile_manager.cleanup_profile(worker_id)
                profile_path = self.profile_manager.create_profile(worker_id, force=True)
            
            profile = Profile(
                base_profile_path=self.config.base_profile_path,
                worker_profile_path=profile_path,
                worker_id=worker_id,
                profile_name=self.config.base_profile_name or "Default"
            )

            # Create worker process
            worker = WorkerProcess(
                worker_id=worker_id,
                profile=profile,
                config=self.config,
                storage_manager=self.storage_manager,
                messenger=self.messenger,
            )

            logger.info(
                "Starting worker thread",
                worker_id=worker_id,
                profile_path=profile_path,
            )
            
            # Start worker in thread
            worker_thread = threading.Thread(
                target=self._run_worker_process,
                args=(worker,),
                name=f"Worker-{worker_id}",
                daemon=True
            )
            
            self.workers[worker_id] = worker
            self.worker_threads[worker_id] = worker_thread
            
            worker_thread.start()
            
            logger.debug("Started worker process", worker_id=worker_id)
            
        except Exception as e:
            logger.error("Failed to start worker", worker_id=worker_id, error=str(e))
            raise
    
    def _run_worker_process(self, worker: WorkerProcess) -> None:
        """Run worker process in dedicated thread."""
        try:
            worker.start()
            
            while self._running and not worker.should_stop():
                # Get task from queue
                task = self.task_queue.get_next_task(worker.worker_id)
                
                if task:
                    # Reuse the live POTask that the handle tracks, or create one if missing
                    po_task = self._po_tasks.get(task.task_id)
                    if not po_task:
                        po_task = POTask(
                            po_number=task.po_data.get('po_number', 'unknown'),
                            priority=TaskPriority.NORMAL,
                            metadata={'task_id': task.task_id}
                        )
                        po_task.task_id = task.task_id
                        self._po_tasks[task.task_id] = po_task

                    if task.po_data:
                        po_task.metadata.update(task.po_data)

                    if po_task.status == TaskStatus.RETRYING:
                        try:
                            po_task.reset_for_retry()
                        except ValueError:
                            po_task.status = TaskStatus.PENDING
                            po_task.assigned_worker_id = None
                        else:
                            po_task.status = TaskStatus.PENDING
                            po_task.assigned_worker_id = None
                            po_task.assigned_time = None
                            po_task.started_time = None
                            po_task.error_message = None
                    elif po_task.status not in (TaskStatus.PENDING, TaskStatus.ASSIGNED):
                        po_task.status = TaskStatus.PENDING
                        po_task.assigned_worker_id = None
                        po_task.assigned_time = None
                        po_task.started_time = None
                        po_task.error_message = None

                    po_task.assign_to_worker(worker.worker_id)
                    po_task.start_processing()

                    handle = self._task_handles.get(task.task_id)
                    if handle:
                        handle._task_ref = po_task

                    try:
                        print(f"[Pool] {worker.worker_id} starting task {task.task_id} (PO={po_task.po_number})")
                    except Exception:
                        pass

                    # Process task
                    result = worker.process_task(po_task)
                    
                    # Update statistics
                    if result['success']:
                        self.completed_tasks += 1
                    else:
                        self.failed_tasks += 1
                    
                    # Handle task completion
                    self._handle_task_completion(task, result, po_task)

                    try:
                        print(f"[Pool] {worker.worker_id} finished task {task.task_id} (PO={po_task.po_number}) -> {result.get('status_code', 'UNKNOWN')}")
                    except Exception:
                        pass
                else:
                    # No tasks available, brief sleep
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error("Worker process failed", 
                        worker_id=worker.worker_id, error=str(e))
            
            # Attempt worker restart if not shutting down
            if self._running and not self._shutdown_initiated:
                if self._loop and not self._loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        self._restart_worker(worker.worker_id),
                        self._loop
                    )
                else:
                    logger.error(
                        "Cannot restart worker; event loop unavailable",
                        worker_id=worker.worker_id
                    )
        
        finally:
            logger.debug("Worker process exited", worker_id=worker.worker_id)
    
    async def _restart_worker(self, worker_id: str) -> None:
        """Restart a failed worker process."""
        logger.info("Restarting failed worker", worker_id=worker_id)
        
        # Clean up old worker
        if worker_id in self.workers:
            old_worker = self.workers[worker_id]
            old_worker.stop()
            del self.workers[worker_id]
        
        if worker_id in self.worker_threads:
            # Let thread cleanup naturally
            del self.worker_threads[worker_id]
        
        # Start new worker
        try:
            await self._start_worker(worker_id)
            logger.info("Worker restarted successfully", worker_id=worker_id)
        except Exception as e:
            logger.error("Failed to restart worker", worker_id=worker_id, error=str(e))
    
    def submit_task(
        self,
        po_data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskHandle:
        """
        Submit a PO processing task to the pool.
        
        Args:
            po_data: Dictionary containing PO information
            priority: Task priority level
            metadata: Optional task metadata
            
        Returns:
            TaskHandle for tracking task progress
            
        Raises:
            RuntimeError: If pool is not running
        """
        if not self._running:
            raise RuntimeError("Worker pool is not running")
        
        if isinstance(po_data, str):
            po_data = {'po_number': po_data}

        po_number = po_data.get('po_number', 'unknown')

        # Create POTask
        task = POTask(
            po_number=po_number,
            priority=priority,
            metadata=metadata or {}
        )
        task.metadata.update(po_data)
        
        # Create task function for TaskQueue
        def task_function(po_data: Dict[str, Any]) -> Dict[str, Any]:
            """Task function that processes PO data."""
            # This would be called by the TaskQueue
            # For now, return a mock result since actual processing happens in worker
            return {
                'success': True,
                'data': {'po_number': po_data['po_number']},
                'files': []
            }
        
        # Convert priority to TaskQueue priority (1=highest, 10=lowest)
        queue_priority = {TaskPriority.URGENT: 1, TaskPriority.HIGH: 2, 
                         TaskPriority.NORMAL: 5, TaskPriority.LOW: 8}[priority]
        
        # Add to queue
        task_id = self.task_queue.add_task(
            task_function=task_function,
            po_data=po_data,
            priority=queue_priority
        )
        
        # Store mapping between TaskQueue task_id and POTask
        task.task_id = task_id
        self._po_tasks[task_id] = task
        
        # Create handle tied to the live POTask instance
        handle = TaskHandle(
            task_id=task_id,
            po_number=po_number,
            po_data=po_data.copy(),
            _task_ref=task,
            _pool_ref=self
        )
        self._task_handles[task_id] = handle
        
        logger.debug("Task submitted", po_number=po_number, 
                    priority=priority.value, task_id=task.task_id)
        
        return handle
    
    def submit_tasks(
        self,
        po_list: List[Dict[str, Any]],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> List[TaskHandle]:
        """
        Submit multiple PO processing tasks to the pool.
        
        Args:
            po_list: List of PO data dictionaries
            priority: Priority level for all tasks
            
        Returns:
            List of TaskHandles for tracking progress
        """
        handles: List[TaskHandle] = []

        # Deduplicate by PO number to avoid duplicate processing submissions
        seen_po_numbers: set[str] = set()
        unique_po_list: List[Dict[str, Any]] = []
        for po_data in po_list:
            po_number = str(po_data.get('po_number', '')).strip()
            if not po_number:
                continue
            if po_number in seen_po_numbers:
                logger.debug("Skipping duplicate PO in submission", po_number=po_number)
                continue
            seen_po_numbers.add(po_number)
            unique_po_list.append(po_data)

        for i, po_data in enumerate(unique_po_list):
            handle = self.submit_task(po_data, priority)
            handles.append(handle)
            # Removed verbose task submission messages to reduce terminal output clutter
            # print(f"[Pool] Submitted task {i+1}/{len(unique_po_list)}: PO={po_data.get('po_number', 'unknown')}")

        logger.info(
            "Batch tasks submitted",
            requested=len(po_list),
            deduplicated=len(unique_po_list),
            priority=priority.value,
        )
        print(f"[Pool] Task submission summary: {len(po_list)} requested -> {len(unique_po_list)} unique -> {len(handles)} handles created")

        return handles
    
    async def _monitor_worker_health(self) -> None:
        """Monitor worker health and handle failures."""
        while self._running:
            try:
                failed_workers = []
                
                for worker_id, worker in self.workers.items():
                    status = worker.get_status()
                    
                    if status['status'] in ['failed', 'crashed']:
                        failed_workers.append(worker_id)
                    
                    # Check if worker thread is alive
                    thread = self.worker_threads.get(worker_id)
                    if thread and not thread.is_alive():
                        logger.warning("Worker thread died", worker_id=worker_id)
                        failed_workers.append(worker_id)
                
                # Restart failed workers
                for worker_id in failed_workers:
                    await self._restart_worker(worker_id)
                
                await asyncio.sleep(5)  # Health check every 5 seconds
                
            except Exception as e:
                logger.error("Error in worker health monitoring", error=str(e))
                await asyncio.sleep(1)
    
    async def _process_task_queue(self) -> None:
        """Background task queue processing coordinator."""
        while self._running:
            try:
                # Check queue size and worker utilization
                queue_stats = self.task_queue.get_queue_status()
                
                if queue_stats['pending_tasks'] > 0:
                    logger.debug("Processing task queue", 
                               pending=queue_stats['pending_tasks'])
                
                # Add any queue management logic here
                # (e.g., load balancing, priority reordering)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error("Error in task queue processing", error=str(e))
                await asyncio.sleep(1)

    async def _batch_finalizer_loop(self) -> None:
        """Background loop to process ready_to_finalize tasks in batches."""
        from ..lib.config import Config
        interval = getattr(Config, 'BATCH_FINALIZATION_INTERVAL', 30)
        
        logger.info("Batch finalizer loop started", interval=interval)
        
        while self._running:
            try:
                await asyncio.sleep(interval)
                
                # Snapshot pending tasks
                with self._finalizer_lock:
                    if not self._pending_finalizations:
                        continue
                    to_process = list(self._pending_finalizations)
                    self._pending_finalizations.clear()
                
                logger.info("Batch finalization cycle starting", count=len(to_process))
                
                # Process each task in the executor to avoid blocking the loop
                for po_task, result in to_process:
                    await self._loop.run_in_executor(
                        self.executor,
                        self._finalize_task_folder,
                        po_task,
                        result
                    )
                    
                logger.info("Batch finalization cycle completed", count=len(to_process))
                
            except Exception as e:
                logger.error("Error in batch finalizer loop", error=str(e))

    def _finalize_task_folder(self, po_task: POTask, result: Dict[str, Any]) -> None:
        """Perform actual folder renaming for a task."""
        from ..lib.po_processing import _rename_folder_with_status
        
        folder_path = result.get('final_folder')
        status_code = result.get('status_code', 'FAILED')
        po_number = po_task.po_number
        
        if not folder_path or not os.path.exists(folder_path):
            logger.warning("Cannot finalize folder: path missing or non-existent", 
                         po_number=po_number, path=folder_path)
            # Finalize the POTask anyway
            po_task.status = TaskStatus.COMPLETED
            return

        try:
            logger.info("Finalizing folder for PO", po_number=po_number, old_path=folder_path)
            new_path = _rename_folder_with_status(folder_path, status_code)
            result['final_folder'] = new_path
            
            # Update POTask
            po_task.status = TaskStatus.COMPLETED
            logger.info("Folder finalized for PO", po_number=po_number, new_path=new_path)
        except Exception as e:
            logger.error("Failed to finalize folder for PO", po_number=po_number, error=str(e))
            po_task.status = TaskStatus.FAILED
    
    def _handle_task_completion(self, task: ProcessingTask, result: Dict[str, Any], po_task: POTask) -> None:
        """Handle task completion and update tracking."""
        handle = self._task_handles.get(task.task_id)
        if handle and handle._task_ref is not po_task:
            handle._task_ref = po_task

        if result['success']:
            # Determine if we should defer finalization
            from ..lib.config import Config
            batch_enabled = getattr(Config, 'BATCH_FINALIZATION_ENABLED', False)
            
            po_task.complete_successfully(
                result_data=result.get('data', {}),
                downloaded_files=result.get('files', [])
            )
            # If batching is enabled and it IS a work folder (might not be for NO_ATTACHMENTS)
            if batch_enabled and result.get('final_folder', '').endswith('__WORK'):
                po_task.status = TaskStatus.READY_TO_FINALIZE
                with self._finalizer_lock:
                    self._pending_finalizations.append((po_task, result))
                logger.info("Task ready to finalize (deferred)", po_number=po_task.po_number)
            
            po_task.metadata['result_payload'] = result

            task_result = TaskResult(
                success=True,
                processing_time=result.get('processing_time', 0.0),
                download_count=len(result.get('files', [])),
                file_paths=result.get('files', []),
                additional_data=result.get('data', {})
            )

            self.task_queue.complete_task(
                task_id=task.task_id,
                worker_id=task.assigned_worker or 'unknown',
                result=task_result
            )
            
            # Send metric to communication manager if available
            if self.communication_manager:
                metric_data = {
                    'worker_id': task.assigned_worker or 0,
                    'po_id': po_task.po_number,
                    'status': 'COMPLETED',
                    'timestamp': time.time(),
                    'duration': result.get('processing_time', 0.0),
                    'attachments_found': result.get('attachments_found', 0),
                    'attachments_downloaded': result.get('attachments_downloaded', 0),
                    'message': result.get('message', ''),
                }
                self.communication_manager.send_metric(metric_data)

            if handle:
                handle._result = result

            self._task_handles.pop(task.task_id, None)
            self._po_tasks.pop(task.task_id, None)

            logger.debug("Task completed successfully", 
                        po_number=task.po_data.get('po_number', 'unknown'), 
                        task_id=task.task_id)
        else:
            error_message = result.get('error', 'Unknown error')
            requeued = self.task_queue.retry_task(
                task_id=task.task_id,
                error_details={'error_message': error_message}
            )

            po_task.fail_with_error(error_message, allow_retry=requeued)
            if not requeued:
                po_task.metadata['result_payload'] = result
            
            # Send metric to communication manager if available
            if self.communication_manager:
                metric_data = {
                    'worker_id': task.assigned_worker or 0,
                    'po_id': po_task.po_number,
                    'status': 'FAILED',
                    'timestamp': time.time(),
                    'duration': result.get('processing_time', 0.0),
                    'attachments_found': 0,
                    'attachments_downloaded': 0,
                    'message': error_message,
                }
                self.communication_manager.send_metric(metric_data)

            if requeued:
                try:
                    po_task.reset_for_retry()
                except ValueError:
                    po_task.status = TaskStatus.PENDING
                    po_task.assigned_worker_id = None
                else:
                    po_task.status = TaskStatus.PENDING
                    po_task.assigned_worker_id = None
                    po_task.assigned_time = None
                    po_task.started_time = None
                    po_task.error_message = None

                logger.warning("Task failed, scheduled for retry", 
                              po_number=task.po_data.get('po_number', 'unknown'),
                              error=error_message)
            else:
                if handle:
                    handle._result = result
                self._task_handles.pop(task.task_id, None)
                self._po_tasks.pop(task.task_id, None)

                logger.warning("Task failed", 
                              po_number=task.po_data.get('po_number', 'unknown'),
                              error=error_message)

        # Notify result callbacks (CSV persistence, observers, etc.)
        self._dispatch_task_result(po_task, result)

        # --- Rate limit handling: restart workers to refresh sessions ---
        try:
            status_code = (result.get('status_code') or '').upper()
            transient_flag = bool(result.get('transient'))
            if status_code in {'RATE_LIMIT', 'ACCESS_DENIED', 'TIMEOUT'} or (transient_flag and not status_code):
                worker_id = task.assigned_worker or po_task.assigned_worker_id
                if worker_id and worker_id in self.workers:
                    logger.warning(
                        "Transient condition detected; restarting worker",
                        worker_id=worker_id,
                        status_code=status_code,
                        po_number=po_task.po_number,
                    )
                    # Schedule async restart (don't await inside completion path)
                    if self._loop and not self._loop.is_closed():
                        asyncio.run_coroutine_threadsafe(self._restart_worker(worker_id), self._loop)

                    # If TIMEOUT we escalate to global restart (all workers) with cooldown
                    if status_code == 'TIMEOUT':
                        now = time.time()
                        should_global = False
                        if self._last_global_timeout_restart is None:
                            should_global = True
                        else:
                            if now - self._last_global_timeout_restart >= self._timeout_global_restart_cooldown:
                                should_global = True
                        if should_global:
                            self._last_global_timeout_restart = now
                            logger.warning(
                                "TIMEOUT detected – performing global worker restart",
                                worker_count=len(self.workers),
                                cooldown_seconds=self._timeout_global_restart_cooldown,
                            )
                            if self._loop and not self._loop.is_closed():
                                for wid in list(self.workers.keys()):
                                    # Avoid double scheduling for the already scheduled worker; _restart_worker is idempotent
                                    asyncio.run_coroutine_threadsafe(self._restart_worker(wid), self._loop)
                        else:
                            logger.info(
                                "Global timeout restart suppressed by cooldown",
                                seconds_since_last=now - (self._last_global_timeout_restart or 0.0),
                                cooldown=self._timeout_global_restart_cooldown,
                            )

                    # Automatic requeue policy differentiation
                    # RATE_LIMIT: retry up to 3x with linear backoff 5s,10s,15s
                    # ACCESS_DENIED: single immediate retry (5s) only
                    # TIMEOUT: retry up to 2x with linear backoff 3s,6s
                    rl_meta_key = 'rate_limit_attempts'
                    attempts = int(getattr(po_task, rl_meta_key, 0))
                    if status_code == 'RATE_LIMIT':
                        max_attempts = 3; base_delay = 5
                    elif status_code == 'ACCESS_DENIED':
                        max_attempts = 1; base_delay = 5
                    else:  # TIMEOUT
                        rl_meta_key = 'timeout_attempts'
                        attempts = int(getattr(po_task, rl_meta_key, 0))
                        max_attempts = 2; base_delay = 3

                    if attempts < max_attempts:
                        setattr(po_task, rl_meta_key, attempts + 1)
                        if status_code == 'RATE_LIMIT':
                            delay_seconds = base_delay * (attempts + 1)
                        elif status_code == 'TIMEOUT':
                            delay_seconds = base_delay * (attempts + 1)
                        else:  # ACCESS_DENIED
                            delay_seconds = base_delay
                        logger.warning(
                            "Requeuing task due to transient error",
                            po_number=po_task.po_number,
                            status_code=status_code,
                            attempt=attempts + 1,
                            max_attempts=max_attempts,
                            delay_seconds=delay_seconds,
                        )

                        def _delayed_requeue():
                            time.sleep(delay_seconds)
                            try:
                                handle = self.submit_task(
                                    po_data={'po_number': po_task.po_number},
                                    priority=TaskPriority.HIGH,
                                    metadata=po_task.metadata,
                                )
                                # annotate new submission with attempts for CSV persistence hook
                                if status_code in {'RATE_LIMIT','ACCESS_DENIED'}:
                                    result['rate_limit_attempts'] = attempts + 1
                                elif status_code == 'TIMEOUT':
                                    result['timeout_attempts'] = attempts + 1
                                # store attempts in handle metadata if needed later
                                if status_code in {'RATE_LIMIT','ACCESS_DENIED'}:
                                    handle.po_data['rate_limit_attempts'] = attempts + 1
                                elif status_code == 'TIMEOUT':
                                    handle.po_data['timeout_attempts'] = attempts + 1
                            except Exception as sub_err:
                                logger.error(
                                    "Failed to requeue blocked task",
                                    po_number=po_task.po_number,
                                    error=str(sub_err),
                                )
                        threading.Thread(target=_delayed_requeue, daemon=True).start()
        except Exception as rl_err:  # pragma: no cover - defensive
            logger.error("Rate limit restart path failed", error=str(rl_err))


    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive pool status.
        
        Returns:
            Dictionary containing pool status and statistics
        """
        worker_stats = {}
        for worker_id, worker in self.workers.items():
            worker_stats[worker_id] = worker.get_status()
        
        queue_stats = self.task_queue.get_queue_status()
        memory_info = {}  # Memory monitoring removed
        profile_stats = self.profile_manager.get_stats()
        
        uptime = time.time() - (self.start_time or time.time())
        
        return {
            'pool_status': 'running' if self._running else 'stopped',
            'startup_complete': self._startup_complete,
            'uptime_seconds': uptime,
            'worker_count': len(self.workers),
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'workers': worker_stats,
            'task_queue': queue_stats,
            'memory': memory_info,
            'profiles': profile_stats,
            'config': self.config.to_dict()
        }
    
    async def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all pending tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all tasks completed, False if timeout
        """
        start_time = time.time()
        
        while self._running:
            stats = self.task_queue.get_queue_status()
            
            if stats['pending_tasks'] == 0 and stats['processing_tasks'] == 0:
                logger.info("All tasks completed")
                return True
            
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(
                    "Timeout waiting for task completion",
                    pending=stats['pending_tasks'],
                    active=stats['processing_tasks']
                )
                return False
            
            await asyncio.sleep(1)
        
        return False
    
    async def shutdown(self, emergency: bool = False) -> None:
        """
        Gracefully shutdown the worker pool.
        
        Stops accepting new tasks, completes current tasks, and cleans up resources.
        
        Args:
            emergency: If True, accelerated shutdown with minimal timeouts.
        """
        if not self._running:
            logger.warning("Worker pool is not running")
            return
        
        logger.info("Initiating shutdown...", emergency=emergency)
        self._shutdown_initiated = True
        
        try:
            # Stop accepting new tasks
            self.task_queue.stop()
            
            # Wait for current tasks to complete (with timeout)
            if emergency:
                completion_timeout = 5.0  # Just a few seconds for very quick tasks
            else:
                completion_timeout = min(self.config.shutdown_timeout * 0.7, 120)
                
            completed = await self.wait_for_completion(completion_timeout)
            
            if not completed:
                logger.warning("Some tasks did not complete before shutdown timeout")
            
            # Process remaining pending finalizations before stopping
            if not emergency:
                with self._finalizer_lock:
                    if self._pending_finalizations:
                        logger.info("Processing pending finalizations before shutdown", count=len(self._pending_finalizations))
                        to_process = list(self._pending_finalizations)
                        self._pending_finalizations.clear()
                        
                        for po_task, result in to_process:
                            self._finalize_task_folder(po_task, result)
            
            # Stop workers
            logger.info("Stopping workers...", emergency=emergency)
            await self._stop_workers(emergency=emergency)
            
            # Cleanup components
            await self._cleanup_components()
            
            self._running = False
            self._startup_complete = False
            
            uptime = time.time() - (self.start_time or time.time())
            logger.info("PersistentWorkerPool shutdown completed", 
                       uptime_seconds=f"{uptime:.2f}",
                       completed_tasks=self.completed_tasks,
                       failed_tasks=self.failed_tasks)
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
            await self._emergency_cleanup()
            raise
    
    async def _stop_workers(self, emergency: bool = False) -> None:
        """Stop all worker processes gracefully."""
        # Signal all workers to stop
        for worker in self.workers.values():
            if emergency:
                try:
                    worker.force_stop()
                except Exception:
                    pass
            else:
                worker.stop()
        
        # Wait for worker threads to finish
        if emergency:
            worker_timeout = 5.0
        else:
            worker_timeout = self.config.shutdown_timeout * 0.3
            
        end_time = time.time() + worker_timeout
        
        for worker_id, thread in self.worker_threads.items():
            remaining_time = max(0, end_time - time.time())
            
            if remaining_time > 0:
                thread.join(timeout=remaining_time)
                
                if thread.is_alive():
                    logger.warning("Worker thread did not stop gracefully", 
                                  worker_id=worker_id)
        
        self.workers.clear()
        self.worker_threads.clear()
    
    async def _cleanup_components(self) -> None:
        """Cleanup all pool components."""
        # Memory monitoring removed
        
        # Cleanup profiles if configured
        if self.config.profile_cleanup_on_shutdown:
            self.profile_manager.cleanup_all_profiles()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.debug("Component cleanup completed")
    
    async def _emergency_cleanup(self) -> None:
        """Emergency cleanup for failed startup or shutdown."""
        logger.warning("Performing emergency cleanup")
        
        try:
            # Force stop all workers
            for worker in self.workers.values():
                worker.force_stop()
            
            # Force cleanup profiles
            self.profile_manager.cleanup_all_profiles()
            
            # Memory monitoring removed
            
            # Force shutdown executor
            self.executor.shutdown(wait=False)
            
        except Exception as e:
            logger.error("Error during emergency cleanup", error=str(e))
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        if self._running:
            # Run shutdown in sync context
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.shutdown())
            except RuntimeError:
                # Create new event loop if none exists
                asyncio.run(self.shutdown())
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.shutdown()
