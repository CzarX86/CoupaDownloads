"""
PersistentWorkerPool entity - main orchestrator for worker pool management.
Coordinates workers, manages resources, and provides the primary interface.
"""

import time
import os
import tempfile
import threading
import multiprocessing
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from queue import Queue, Empty
from .worker import Worker, WorkerConfiguration, WorkerStatus, WorkerError
from .profile import Profile, ProfileStatus
from .browser_session import BrowserSession
from .tab import POTask


class PoolStatus(Enum):
    """Status of the worker pool."""
    CREATING = "creating"
    INITIALIZING = "initializing"
    STARTING = "starting"
    READY = "ready"
    ACTIVE = "active"
    DEGRADED = "degraded"  # Some workers failed
    MAINTENANCE = "maintenance"  # Performing maintenance
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class PoolError(Enum):
    """Types of pool errors."""
    INITIALIZATION_FAILED = "initialization_failed"
    INSUFFICIENT_WORKERS = "insufficient_workers"
    MEMORY_THRESHOLD_EXCEEDED = "memory_threshold_exceeded"
    ALL_WORKERS_FAILED = "all_workers_failed"
    PROFILE_CREATION_FAILED = "profile_creation_failed"
    SYSTEM_RESOURCE_EXHAUSTED = "system_resource_exhausted"
    GRACEFUL_SHUTDOWN_TIMEOUT = "graceful_shutdown_timeout"


@dataclass
class PoolConfiguration:
    """Configuration for the worker pool."""
    worker_count: int = 3
    headless_mode: bool = True
    base_profile_path: str = ""
    memory_threshold: float = 0.75  # 75% of system RAM
    shutdown_timeout: int = 60  # seconds
    max_restart_attempts: int = 3
    restart_delay_seconds: int = 5
    maintenance_interval_minutes: int = 30
    task_timeout_seconds: int = 300  # 5 minutes
    max_queue_size: int = 1000
    enable_monitoring: bool = True
    monitoring_interval_seconds: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.worker_count < 1:
            raise ValueError("worker_count must be at least 1")
        if not 0.1 <= self.memory_threshold <= 0.95:
            raise ValueError("memory_threshold must be between 0.1 and 0.95")
        if self.shutdown_timeout < 10:
            raise ValueError("shutdown_timeout must be at least 10 seconds")
        if not self.base_profile_path:
            self.base_profile_path = tempfile.mkdtemp(prefix="coupa_profiles_")


@dataclass
class PersistentWorkerPool:
    """
    Main worker pool entity for coordinating persistent browser workers.
    
    Manages:
    - Worker lifecycle (creation, monitoring, restart, shutdown)
    - Task distribution and load balancing
    - Resource monitoring and memory management
    - Profile management and corruption handling
    - Graceful shutdown with cascading recovery
    """
    
    pool_id: str = field(default_factory=lambda: f"pool_{int(time.time())}")
    configuration: Optional[PoolConfiguration] = None
    status: PoolStatus = PoolStatus.CREATING
    created_at: float = field(default_factory=time.time)
    initialized_at: Optional[float] = None
    started_at: Optional[float] = None
    last_activity_at: float = field(default_factory=time.time)
    
    # Worker management
    workers: Dict[str, Worker] = field(default_factory=dict)
    available_profiles: List[Profile] = field(default_factory=list)
    
    # Task management
    task_queue: Queue = field(default_factory=Queue)
    completed_tasks: Dict[str, POTask] = field(default_factory=dict)
    failed_tasks: Dict[str, POTask] = field(default_factory=dict)
    
    # Monitoring and control
    monitor_thread: Optional[threading.Thread] = None
    maintenance_thread: Optional[threading.Thread] = None
    shutdown_event: threading.Event = field(default_factory=threading.Event)
    
    # Error tracking
    error_count: int = 0
    last_error: Optional[PoolError] = None
    last_error_message: Optional[str] = None
    last_error_at: Optional[float] = None
    
    # Performance metrics
    total_tasks_processed: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    total_restart_count: int = 0
    total_uptime_seconds: float = 0.0
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize pool state."""
        if not self.pool_id:
            self.pool_id = f"pool_{int(time.time())}"
            
    @property
    def is_active(self) -> bool:
        """Check if pool is active and ready for work."""
        return self.status in [PoolStatus.READY, PoolStatus.ACTIVE, PoolStatus.DEGRADED]
        
    @property
    def is_healthy(self) -> bool:
        """Check if pool is healthy (not degraded or error state)."""
        return self.status in [PoolStatus.READY, PoolStatus.ACTIVE]
        
    @property
    def active_workers(self) -> List[Worker]:
        """Get list of active workers."""
        return [w for w in self.workers.values() if w.is_active]
        
    @property
    def available_workers(self) -> List[Worker]:
        """Get list of workers available for new tasks."""
        return [w for w in self.active_workers if w.is_available_for_tasks]
        
    @property
    def processing_workers(self) -> List[Worker]:
        """Get list of workers currently processing tasks."""
        return [w for w in self.active_workers if w.is_processing]
        
    @property
    def pending_tasks_count(self) -> int:
        """Get number of pending tasks in queue."""
        return self.task_queue.qsize()
        
    @property
    def current_memory_usage(self) -> int:
        """Get total memory usage of all workers in bytes."""
        return sum(w.memory_usage_bytes for w in self.workers.values())
        
    def initialize(self, configuration: PoolConfiguration) -> None:
        """Initialize the worker pool with configuration."""
        if self.status != PoolStatus.CREATING:
            raise RuntimeError(f"Cannot initialize pool in status: {self.status}")
            
        self.configuration = configuration
        self.status = PoolStatus.INITIALIZING
        self.last_activity_at = time.time()
        
        try:
            # Create worker profiles
            self._create_worker_profiles()
            
            # Initialize workers
            self._initialize_workers()
            
            # Start monitoring if enabled
            if configuration.enable_monitoring:
                self._start_monitoring()
                
            self.initialized_at = time.time()
            self.status = PoolStatus.READY
            
        except Exception as e:
            self.status = PoolStatus.ERROR
            self.record_error(PoolError.INITIALIZATION_FAILED, f"Pool initialization failed: {e}")
            raise
            
    def start(self) -> None:
        """Start the worker pool and all workers."""
        if not self.is_active:
            raise RuntimeError(f"Cannot start pool in status: {self.status}")
            
        self.status = PoolStatus.STARTING
        self.last_activity_at = time.time()
        
        try:
            # Start all workers
            started_workers = 0
            for worker in self.workers.values():
                if self._start_worker(worker):
                    started_workers += 1
                    
            if started_workers == 0:
                self.status = PoolStatus.ERROR
                self.record_error(PoolError.ALL_WORKERS_FAILED, "No workers could be started")
                raise RuntimeError("Failed to start any workers")
                
            elif started_workers < len(self.workers):
                self.status = PoolStatus.DEGRADED
                self.record_error(PoolError.INSUFFICIENT_WORKERS, 
                                f"Only {started_workers}/{len(self.workers)} workers started")
            else:
                self.status = PoolStatus.READY
                
            self.started_at = time.time()
            
        except Exception as e:
            self.status = PoolStatus.ERROR
            self.record_error(PoolError.INITIALIZATION_FAILED, f"Pool start failed: {e}")
            raise
            
    def add_task(self, task: POTask) -> bool:
        """
        Add a single task to the processing queue.
        Returns True if task was added successfully.
        """
        if not self.is_active:
            return False
            
        try:
            if self.configuration and self.task_queue.qsize() >= self.configuration.max_queue_size:
                return False
                
            self.task_queue.put(task, timeout=1.0)
            self.last_activity_at = time.time()
            
            # Update status to active if we have pending work
            if self.status == PoolStatus.READY:
                self.status = PoolStatus.ACTIVE
                
            return True
            
        except Exception:
            return False
            
    def add_tasks(self, tasks: List[POTask]) -> int:
        """
        Add multiple tasks to the processing queue.
        Returns number of tasks successfully added.
        """
        added_count = 0
        for task in tasks:
            if self.add_task(task):
                added_count += 1
            else:
                break  # Stop if queue is full or pool unavailable
                
        return added_count
        
    def restart_worker(self, worker_id: str) -> bool:
        """
        Restart a specific worker.
        Returns True if restart was initiated successfully.
        """
        if worker_id not in self.workers:
            return False
            
        worker = self.workers[worker_id]
        
        try:
            # Stop the worker
            worker.stop()
            
            # Create new profile if needed
            if worker.profile and worker.profile.is_corrupted:
                self._create_worker_profile(worker)
                
            # Start the worker again
            if self._start_worker(worker):
                self.total_restart_count += 1
                self.last_activity_at = time.time()
                return True
                
        except Exception as e:
            worker.record_error(WorkerError.PROCESS_LAUNCH_FAILED, f"Restart failed: {e}")
            
        return False
        
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the worker pool."""
        worker_statuses = []
        for worker in self.workers.values():
            worker_status = {
                'worker_id': worker.worker_id,
                'status': worker.status.value,
                'process_id': worker.process_id,
                'memory_usage': worker.memory_usage_bytes,
                'current_tasks': len(worker.current_tasks),
                'total_tasks_processed': worker.total_tasks_processed,
                'error_count': worker.error_count,
                'is_available': worker.is_available_for_tasks,
                'uptime_seconds': worker.uptime_seconds
            }
            worker_statuses.append(worker_status)
            
        return {
            'pool_id': self.pool_id,
            'pool_status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'uptime_seconds': self.uptime_seconds,
            'workers': worker_statuses,
            'total_workers': len(self.workers),
            'active_workers': len(self.active_workers),
            'available_workers': len(self.available_workers),
            'processing_workers': len(self.processing_workers),
            'pending_tasks': self.pending_tasks_count,
            'total_tasks_processed': self.total_tasks_processed,
            'total_tasks_completed': self.total_tasks_completed,
            'total_tasks_failed': self.total_tasks_failed,
            'total_memory_usage': self.current_memory_usage,
            'memory_threshold': self.configuration.memory_threshold if self.configuration else 0.75,
            'error_count': self.error_count,
            'last_error': self.last_error.value if self.last_error else None,
            'last_activity_at': self.last_activity_at,
            'is_healthy': self.is_healthy
        }
        
    def shutdown(self, timeout: Optional[int] = None) -> bool:
        """
        Shutdown the worker pool gracefully.
        Returns True if shutdown completed within timeout.
        """
        if self.status in [PoolStatus.STOPPING, PoolStatus.STOPPED]:
            return True
            
        self.status = PoolStatus.STOPPING
        self.last_activity_at = time.time()
        
        # Use configured timeout if not provided
        if timeout is None and self.configuration:
            timeout = self.configuration.shutdown_timeout
        elif timeout is None:
            timeout = 60
            
        # Signal shutdown
        self.shutdown_event.set()
        
        try:
            # Stop monitoring threads
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=10)
                
            if self.maintenance_thread and self.maintenance_thread.is_alive():
                self.maintenance_thread.join(timeout=10)
                
            # Stop all workers
            shutdown_start = time.time()
            for worker in self.workers.values():
                remaining_timeout = max(0, timeout - (time.time() - shutdown_start))
                if remaining_timeout > 0:
                    worker.stop()
                    
            # Cleanup profiles
            for profile in self.available_profiles:
                profile.cleanup()
                
            self.status = PoolStatus.STOPPED
            return True
            
        except Exception as e:
            self.record_error(PoolError.GRACEFUL_SHUTDOWN_TIMEOUT, f"Shutdown failed: {e}")
            return False
            
    @property
    def uptime_seconds(self) -> float:
        """Uptime since pool started."""
        if self.started_at is None:
            return 0.0
        return time.time() - self.started_at
        
    def record_error(self, error: PoolError, message: str) -> None:
        """Record an error for the pool."""
        self.error_count += 1
        self.last_error = error
        self.last_error_message = message
        self.last_error_at = time.time()
        self.last_activity_at = time.time()
        
        # Store error in metadata for debugging
        if 'errors' not in self.metadata:
            self.metadata['errors'] = []
            
        self.metadata['errors'].append({
            'error': error.value,
            'message': message,
            'timestamp': time.time(),
            'pool_status': self.status.value,
            'active_workers': len(self.active_workers)
        })
        
        # Keep only last 20 errors to prevent unbounded growth
        if len(self.metadata['errors']) > 20:
            self.metadata['errors'] = self.metadata['errors'][-20:]
            
    def _create_worker_profiles(self) -> None:
        """Create profiles for all workers."""
        if not self.configuration:
            raise RuntimeError("Configuration not set")
            
        for i in range(self.configuration.worker_count):
            profile_id = f"{self.pool_id}_profile_{i+1}"
            profile = Profile(
                profile_id=profile_id,
                base_path=self.configuration.base_profile_path
            )
            
            try:
                profile.create_directories()
                self.available_profiles.append(profile)
            except Exception as e:
                self.record_error(PoolError.PROFILE_CREATION_FAILED, 
                                f"Failed to create profile {profile_id}: {e}")
                
    def _create_worker_profile(self, worker: Worker) -> None:
        """Create a new profile for a specific worker."""
        if not self.configuration:
            return
            
        profile_id = f"{worker.worker_id}_profile_{int(time.time())}"
        profile = Profile(
            profile_id=profile_id,
            base_path=self.configuration.base_profile_path
        )
        
        try:
            profile.create_directories()
            worker.profile = profile
        except Exception as e:
            worker.record_error(WorkerError.PROFILE_CREATION_FAILED, f"Profile creation failed: {e}")
            
    def _initialize_workers(self) -> None:
        """Initialize all worker instances."""
        if not self.configuration:
            raise RuntimeError("Configuration not set")
            
        for i in range(self.configuration.worker_count):
            worker_id = f"{self.pool_id}_worker_{i+1}"
            
            worker_config = WorkerConfiguration(
                worker_id=worker_id,
                headless_mode=self.configuration.headless_mode,
                profile_base_path=self.configuration.base_profile_path
            )
            
            worker = Worker(worker_id=worker_id, configuration=worker_config)
            
            # Assign profile if available
            if self.available_profiles:
                worker.profile = self.available_profiles.pop(0)
                
            self.workers[worker_id] = worker
            
    def _start_worker(self, worker: Worker) -> bool:
        """Start a specific worker process."""
        try:
            # This would be implemented with actual process spawning
            # For now, we simulate the start with current process ID
            current_pid = os.getpid()
            worker.start_process(current_pid)
            
            # Initialize browser session
            if worker.profile:
                session = BrowserSession(
                    session_id=f"{worker.worker_id}_session",
                    profile=worker.profile
                )
                worker.initialize_browser_session(session)
                
            return True
            
        except Exception as e:
            worker.record_error(WorkerError.PROCESS_LAUNCH_FAILED, f"Start failed: {e}")
            return False
            
    def _start_monitoring(self) -> None:
        """Start monitoring threads."""
        if not self.configuration:
            return
            
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self.maintenance_thread.start()
        
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        if not self.configuration:
            return
            
        while not self.shutdown_event.is_set():
            try:
                # Monitor memory usage
                self._check_memory_threshold()
                
                # Monitor worker health
                self._check_worker_health()
                
                # Process task queue
                self._process_task_queue()
                
                # Update metrics
                self._update_metrics()
                
                # Wait for next cycle
                self.shutdown_event.wait(self.configuration.monitoring_interval_seconds)
                
            except Exception as e:
                self.record_error(PoolError.SYSTEM_RESOURCE_EXHAUSTED, f"Monitoring error: {e}")
                time.sleep(5)  # Wait before retrying
                
    def _maintenance_loop(self) -> None:
        """Maintenance loop for cleanup and optimization."""
        if not self.configuration:
            return
            
        while not self.shutdown_event.is_set():
            try:
                # Perform maintenance tasks
                self._cleanup_completed_tasks()
                self._optimize_worker_distribution()
                
                # Wait for next maintenance cycle
                maintenance_wait = self.configuration.maintenance_interval_minutes * 60
                self.shutdown_event.wait(maintenance_wait)
                
            except Exception as e:
                self.record_error(PoolError.SYSTEM_RESOURCE_EXHAUSTED, f"Maintenance error: {e}")
                time.sleep(60)  # Wait before retrying
                
    def _check_memory_threshold(self) -> None:
        """Check if memory threshold is exceeded."""
        # Implementation would check system memory vs threshold
        # For now, this is a placeholder
        pass
        
    def _check_worker_health(self) -> None:
        """Check health of all workers and restart if needed."""
        for worker in list(self.workers.values()):
            if worker.should_restart():
                self.restart_worker(worker.worker_id)
                
    def _process_task_queue(self) -> None:
        """Process pending tasks from the queue."""
        while not self.task_queue.empty():
            available_workers = self.available_workers
            if not available_workers:
                break
                
            try:
                task = self.task_queue.get_nowait()
                
                # Assign to first available worker
                worker = available_workers[0]
                if worker.assign_task(task):
                    self.total_tasks_processed += 1
                else:
                    # Put task back in queue if assignment failed
                    self.task_queue.put(task)
                    break
                    
            except Empty:
                break
                
    def _update_metrics(self) -> None:
        """Update pool performance metrics."""
        # Update completed/failed task counts
        self.total_tasks_completed = sum(w.total_tasks_completed for w in self.workers.values())
        self.total_tasks_failed = sum(w.total_tasks_failed for w in self.workers.values())
        
        # Update uptime
        if self.started_at:
            self.total_uptime_seconds = time.time() - self.started_at
            
    def _cleanup_completed_tasks(self) -> None:
        """Clean up old completed and failed task records."""
        # Keep only recent tasks to prevent memory growth
        max_tasks_to_keep = 1000
        
        if len(self.completed_tasks) > max_tasks_to_keep:
            # Remove oldest tasks
            sorted_tasks = sorted(self.completed_tasks.items(), key=lambda x: x[1].completed_at or 0)
            tasks_to_remove = len(sorted_tasks) - max_tasks_to_keep
            for i in range(tasks_to_remove):
                del self.completed_tasks[sorted_tasks[i][0]]
                
        if len(self.failed_tasks) > max_tasks_to_keep:
            # Remove oldest tasks
            sorted_tasks = sorted(self.failed_tasks.items(), key=lambda x: x[1].completed_at or 0)
            tasks_to_remove = len(sorted_tasks) - max_tasks_to_keep
            for i in range(tasks_to_remove):
                del self.failed_tasks[sorted_tasks[i][0]]
                
    def _optimize_worker_distribution(self) -> None:
        """Optimize task distribution across workers."""
        # Implementation would analyze worker performance and adjust distribution
        # For now, this is a placeholder
        pass