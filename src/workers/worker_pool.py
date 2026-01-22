"""
Worker Pool Implementation for Parallel PO Processing

This module provides the WorkerPool class and supporting components for managing
multiple worker processes with isolated browser profiles for parallel downloading.
"""

import os
import time
import multiprocessing
import threading
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field

try:
    # Prefer absolute package imports when EXPERIMENTAL is a package
    from ..lib.models import HeadlessConfiguration
    from workers.exceptions import (
        WorkerPoolError,
        WorkerCreationError,
        WorkerTimeoutError,
        ProfileConflictError,
    )
    from workers.profile_manager import ProfileManager
    from workers.task_queue import TaskQueue
    from workers.resource_monitor import (
        create_default_monitor,
        ResourceMonitor,
    )
except ImportError:
    try:
        # Fallback to package-relative imports when imported within EXPERIMENTAL package
        from ..corelib.models import HeadlessConfiguration
        from .exceptions import (
            WorkerPoolError,
            WorkerCreationError,
            WorkerTimeoutError,
            ProfileConflictError,
        )
        from .profile_manager import ProfileManager
        from .task_queue import TaskQueue
        from .resource_monitor import (
            create_default_monitor,
            ResourceMonitor,
        )
    except ImportError:
        # Handle direct script execution or tests invoking this module standalone
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from ..lib.models import HeadlessConfiguration
        from workers.exceptions import (
            WorkerPoolError,
            WorkerCreationError,
            WorkerTimeoutError,
            ProfileConflictError,
        )
        from workers.profile_manager import ProfileManager
        from workers.task_queue import TaskQueue
        from workers.resource_monitor import (
            create_default_monitor,
            ResourceMonitor,
        )
from ..specs.parallel_profile_clone.contracts.worker_integration_contract import (
    WorkerConfig as _WorkerConfig,
    WorkerStartupResult as _WorkerStartupResult,
)


class WorkerStatus(Enum):
    """Status enumeration for individual workers."""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PoolStatus(Enum):
    """Status enumeration for the worker pool."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class WorkerInstance:
    """
    Represents an individual worker process with isolated browser profile.
    
    This is the core model for T019 - WorkerInstance with all required attributes
    and state management for parallel processing workers.
    """
    worker_id: str
    process_id: Optional[int] = None
    profile_path: Optional[str] = None
    status: WorkerStatus = WorkerStatus.INITIALIZING
    current_task: Optional[str] = None  # Task ID currently being processed
    processed_count: int = 0
    failed_count: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Initialize worker instance with unique ID if not provided."""
        if not self.worker_id:
            self.worker_id = f"worker_{uuid.uuid4().hex[:8]}"
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def assign_task(self, task_id: str):
        """Assign a task to this worker."""
        self.current_task = task_id
        self.status = WorkerStatus.PROCESSING
        self.update_activity()
    
    def complete_task(self, success: bool = True, error_message: Optional[str] = None):
        """Mark current task as completed."""
        if success:
            self.processed_count += 1
        else:
            self.failed_count += 1
            self.error_message = error_message
        
        self.current_task = None
        self.status = WorkerStatus.READY if success else WorkerStatus.FAILED
        self.update_activity()
    
    def mark_failed(self, error_message: str):
        """Mark worker as failed with error message."""
        self.status = WorkerStatus.FAILED
        self.error_message = error_message
        self.current_task = None
        self.update_activity()
    
    def is_healthy(self, timeout_seconds: int = 300) -> bool:
        """Check if worker is healthy based on last activity."""
        if self.status in [WorkerStatus.COMPLETED, WorkerStatus.FAILED]:
            return False
        
        time_since_activity = (datetime.now() - self.last_activity).total_seconds()
        return time_since_activity < timeout_seconds
    
    def get_runtime(self) -> float:
        """Get worker runtime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert worker instance to dictionary for serialization."""
        return {
            'worker_id': self.worker_id,
            'process_id': self.process_id,
            'profile_path': self.profile_path,
            'status': self.status.value,
            'current_task': self.current_task,
            'processed_count': self.processed_count,
            'failed_count': self.failed_count,
            'start_time': self.start_time.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'error_message': self.error_message,
            'runtime_seconds': self.get_runtime(),
            'is_healthy': self.is_healthy()
        }


class WorkerPool:
    """
    Manages lifecycle and coordination of multiple worker processes for parallel PO processing.
    
    This class implements the WorkerPool API contract for managing worker processes,
    task distribution, and resource coordination in parallel processing mode.
    """
    
    def __init__(
        self,
        headless_config: HeadlessConfiguration,
        pool_size: int = 4,
        profile_manager: Optional[ProfileManager] = None,
        max_task_timeout: int = 300,
        resource_monitor: Optional["ResourceMonitor"] = None,
    ):
        """Initialize worker pool with specified configuration."""
        # Validate parameters
        self._max_pool_cap: Optional[int] = self._get_env_worker_cap()
        self._validate_pool_size(pool_size, param_name="pool_size")

        if not isinstance(headless_config, HeadlessConfiguration):
            raise TypeError("headless_config must be HeadlessConfiguration instance")

        # Core configuration
        self.pool_size = pool_size
        self.max_workers = pool_size  # Compatibility alias
        self.headless_config = headless_config
        self.max_task_timeout = max_task_timeout
        self.task_timeout = max_task_timeout  # Compatibility alias
        
        # Resource management
        profile_capacity = max(
            pool_size,
            self._max_pool_cap or pool_size,
            8,
        )
        self.profile_manager = profile_manager or ProfileManager(max_profiles=profile_capacity)
        self.task_queue = TaskQueue()
        self.resource_monitor = resource_monitor or create_default_monitor(monitoring_interval=0.5)
        
        # Worker management
        self.workers: Dict[str, WorkerInstance] = {}
        self.worker_processes: Dict[str, multiprocessing.Process] = {}
        
        # State management
        self.status = PoolStatus.IDLE
        self.created_at = datetime.now()
        self.start_time: Optional[datetime] = None
        self.stop_time: Optional[datetime] = None
        
        # Thread safety
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()
        
        # Performance tracking
        self.performance_metrics = {
            'total_tasks_processed': 0,
            'total_tasks_failed': 0,
            'average_task_duration': 0.0,
            'worker_utilization': {},
            'peak_active_workers': 0
        }

    def _get_uptime(self) -> float:
        """Get pool uptime in seconds."""
        if not self.start_time:
            return 0.0
        end_time = self.stop_time or datetime.now()
        return (end_time - self.start_time).total_seconds()

    def _calculate_worker_utilization(self) -> Dict[str, float]:
        """Calculate utilization for each worker."""
        utilization: Dict[str, float] = {}
        for worker_id, worker in self.workers.items():
            runtime = worker.get_runtime()
            if runtime > 0:
                active_time = worker.processed_count * self.performance_metrics.get('average_task_duration', 0)
                utilization[worker_id] = min(1.0, active_time / runtime) if runtime else 0.0
            else:
                utilization[worker_id] = 0.0
        return utilization

    def _calculate_throughput(self) -> float:
        """Calculate tasks per second throughput."""
        uptime = self._get_uptime()
        if uptime <= 0:
            return 0.0
        total_completed = self.performance_metrics['total_tasks_processed']
        return total_completed / uptime
    
    def start(self) -> bool:
        """Start the worker pool and initialize all workers."""
        with self._lock:
            if self.status != PoolStatus.IDLE:
                raise RuntimeError(f"Cannot start pool in {self.status.value} state")
            
            try:
                self.status = PoolStatus.STARTING
                self.start_time = datetime.now()
                self._shutdown_event.clear()
                
                # Start resource monitoring
                try:
                    if self.resource_monitor:
                        self.resource_monitor.start_monitoring()
                except Exception as _:
                    # Non-fatal: monitoring is auxiliary
                    pass

                # Create and initialize workers
                self._create_workers()
                
                # Start monitoring
                self._start_monitoring()
                
                self.status = PoolStatus.RUNNING
                return True
                
            except Exception as e:
                self.status = PoolStatus.ERROR
                self._cleanup_resources()
                raise WorkerPoolError(f"Failed to start worker pool: {e}")
    
    def stop(self, timeout: int = 30) -> bool:
        """Stop all workers gracefully and cleanup resources."""
        with self._lock:
            if self.status == PoolStatus.IDLE:
                return True
            
            try:
                self.status = PoolStatus.STOPPING
                self._shutdown_event.set()
                
                # Signal workers to stop
                self._signal_workers_stop()
                
                # Wait for graceful shutdown
                shutdown_complete = self._wait_for_shutdown(timeout)
                
                # Force cleanup if needed
                if not shutdown_complete:
                    self._force_shutdown()
                
                # Final cleanup
                self._cleanup_resources()
                
                self.status = PoolStatus.IDLE
                self.stop_time = datetime.now()

                # Stop resource monitoring
                try:
                    if self.resource_monitor:
                        self.resource_monitor.stop_monitoring()
                except Exception:
                    pass
                return shutdown_complete
                
            except Exception as e:
                self.status = PoolStatus.ERROR
                raise WorkerPoolError(f"Failed to stop worker pool: {e}")
    
    def submit_task(self, task_function: Callable, task_data: Dict[str, Any]) -> str:
        """Submit a task for processing by available worker."""
        if self.status != PoolStatus.RUNNING:
            raise WorkerPoolError(f"Cannot submit task to pool in {self.status.value} state")
        
        # Create task and add to queue
        task_id = self.task_queue.add_task(task_function, task_data)
        return task_id
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pool and worker status information."""
        with self._lock:
            worker_details = [worker.to_dict() for worker in self.workers.values()]

            # Augment with basic profile metrics
            profile_count = 0
            total_profile_size_bytes = 0
            try:
                if hasattr(self.profile_manager, "temp_profiles"):
                    profile_count = len(getattr(self.profile_manager, "temp_profiles", {}))
                    for wid in list(getattr(self.profile_manager, "temp_profiles", {}).keys()):
                        try:
                            total_profile_size_bytes += int(self.profile_manager.get_profile_size(wid))
                        except Exception:
                            pass
            except Exception:
                pass
            
            return {
                'pool_status': self.status.value,
                'active_workers': len([w for w in self.workers.values() if w.status == WorkerStatus.READY]),
                'total_workers': len(self.workers),
                'tasks_pending': self.task_queue.get_pending_count(),
                'tasks_active': self.task_queue.get_active_count(),
                'tasks_completed': self.task_queue.get_completed_count(),
                'tasks_failed': self.task_queue.get_failed_count(),
                'worker_details': worker_details,
                'performance_metrics': self.performance_metrics.copy(),
                'profile_metrics': {
                    'profile_count': profile_count,
                    'total_profile_size_mb': round(total_profile_size_bytes / (1024 * 1024), 2) if total_profile_size_bytes else 0.0,
                },
                'resource_status': (self.resource_monitor.get_current_status() if getattr(self, 'resource_monitor', None) else None),
                'uptime_seconds': self._get_uptime(),
                'created_at': self.created_at.isoformat(),
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'stop_time': self.stop_time.isoformat() if self.stop_time else None
            }
    
    def get_results(self) -> Tuple[int, int, Dict[str, Any]]:
        """Get processing results summary and performance metrics."""
        status = self.get_status()
        
        successful_count = status['tasks_completed']
        failed_count = status['tasks_failed']
        
        performance_data = {
            'processing_time': self._get_uptime(),
            'worker_utilization': self._calculate_worker_utilization(),
            'average_task_duration': self.performance_metrics['average_task_duration'],
            'peak_workers': self.performance_metrics['peak_active_workers'],
            'tasks_per_second': self._calculate_throughput()
        }
        
        return successful_count, failed_count, performance_data
    
    def start_processing(self, po_list: List[dict]) -> bool:
        """Start parallel processing of PO list using worker pool."""
        with self._lock:
            if self.status != PoolStatus.IDLE:
                raise RuntimeError(f"Cannot start processing in {self.status.value} state")
            
            if not po_list:
                raise ValueError("PO list cannot be empty")
            
            try:
                # Validate PO data
                try:
                    self._validate_po_list(po_list)
                except ValueError as ve:
                    # Contract: bubble up standardized validation error
                    raise ValueError(f"invalid PO data: {ve}")

                # Start the pool
                if not self.start():
                    return False
                
                # Add all POs as tasks
                for po_data in po_list:
                    self.task_queue.add_task(
                        task_function=self._process_po_task,
                        po_data=po_data
                    )
                
                return True
                
            except Exception as e:
                self.status = PoolStatus.ERROR
                if isinstance(e, ValueError):
                    # Bubble up validation errors per contract
                    raise
                raise WorkerPoolError(f"Failed to start processing: {e}")
    
    def stop_processing(self, timeout: int = 30) -> bool:
        """Stop all workers gracefully and cleanup resources."""
        return self.stop(timeout)
    
    def pause_processing(self) -> bool:
        """Pause processing after current tasks complete."""
        with self._lock:
            if self.status != PoolStatus.RUNNING:
                return False
            
            self.status = PoolStatus.PAUSED
            # Signal workers to pause after completing current tasks
            self._signal_workers_pause()
            return True
    
    def resume_processing(self) -> bool:
        """Resume paused processing."""
        with self._lock:
            if self.status != PoolStatus.PAUSED:
                raise RuntimeError(f"Cannot resume from {self.status.value} state")
            
            self.status = PoolStatus.RUNNING
            # Signal workers to resume processing
            self._signal_workers_resume()
            return True
    
    def scale_workers(self, new_size: int) -> bool:
        """Dynamically adjust worker count during processing."""
        # Delegate to existing resize method
        return self.resize(new_size)
    
    def resize(self, new_size: int) -> bool:
        """Dynamically adjust worker count during processing."""
        self._validate_pool_size(new_size, param_name="Worker count")

        with self._lock:
            current_size = len(self.workers)

            if new_size == current_size:
                return True
            
            try:
                if new_size > current_size:
                    # Scale up - add workers
                    self._add_workers(new_size - current_size)
                else:
                    # Scale down - remove workers
                    self._remove_workers(current_size - new_size)
                
                self.max_workers = new_size
                return True

            except Exception as e:
                raise WorkerPoolError(f"Failed to resize pool: {e}")

    @staticmethod
    def _get_env_worker_cap() -> Optional[int]:
        """Return optional worker cap configured via environment variable."""
        cap_value = os.environ.get('MAX_PARALLEL_WORKERS_CAP')
        if not cap_value:
            return None
        try:
            cap_int = int(cap_value)
        except ValueError:
            return None
        return cap_int if cap_int > 0 else None

    def _validate_pool_size(self, requested: int, *, param_name: str) -> None:
        """Validate requested worker count against basic and env-driven constraints."""
        if requested < 1:
            raise ValueError(f"{param_name} must be at least 1, got {requested}")

        cap = self._get_env_worker_cap()
        self._max_pool_cap = cap

        if cap is not None and requested > cap:
            raise ValueError(f"{param_name} {requested} exceeds configured cap {cap}")
    
    def is_active(self) -> bool:
        """Check if the worker pool is currently active."""
        return self.status in [PoolStatus.STARTING, PoolStatus.RUNNING, PoolStatus.PAUSED]
    
    def get_worker_count(self) -> int:
        """Get current number of workers."""
        return len(self.workers)
    
    def get_worker_details(self) -> List[Dict[str, Any]]:
        """Get detailed information about all workers."""
        return [worker.to_dict() for worker in self.workers.values()]
    
    def pause(self) -> bool:
        """Pause processing after current tasks complete."""
        with self._lock:
            if self.status != PoolStatus.RUNNING:
                return False
            
            self.status = PoolStatus.PAUSED
            self.task_queue.pause()
            return True
    
    def resume(self) -> bool:
        """Resume paused processing."""
        with self._lock:
            if self.status != PoolStatus.PAUSED:
                return False
            
            self.status = PoolStatus.RUNNING
            self.task_queue.resume()
            return True
    
    # Private helper methods
    
    def _create_workers(self):
        """Create and initialize worker processes."""
        for i in range(self.max_workers):
            worker_id = f"worker_{i+1:03d}"
            
            try:
                # Create worker instance
                worker = WorkerInstance(worker_id=worker_id)
                
                # Create profile for worker
                profile_path = self.profile_manager.create_profile(worker_id)
                worker.profile_path = profile_path

                # Optional: verify profile (non-fatal if stubbed)
                try:
                    _ = self.profile_manager.verify_profile(worker_id)
                except Exception:
                    # Verification issues should not prevent worker creation at this stage
                    pass

                # Register worker in resource monitor
                try:
                    if self.resource_monitor:
                        self.resource_monitor.register_worker(worker_id)
                except Exception:
                    pass
                
                # Create worker process
                process = multiprocessing.Process(
                    target=self._worker_main,
                    args=(worker_id, profile_path, self.headless_config)
                )
                
                # Start process
                process.start()
                worker.process_id = process.pid
                worker.status = WorkerStatus.READY
                
                # Store worker and process
                self.workers[worker_id] = worker
                self.worker_processes[worker_id] = process
                
            except Exception as e:
                raise WorkerCreationError(worker_id, f"Failed to create worker {worker_id}: {e}")
    
    def _signal_workers_stop(self):
        """Signal all workers to stop gracefully."""
        self.task_queue.stop()
        # Additional signaling logic would go here
    
    def _wait_for_shutdown(self, timeout: int) -> bool:
        """Wait for all workers to shutdown gracefully."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_stopped = True
            for process in self.worker_processes.values():
                if process.is_alive():
                    all_stopped = False
                    break
            
            if all_stopped:
                return True
            
            time.sleep(0.5)
        
        return False
    
    def _force_shutdown(self):
        """Force shutdown of remaining worker processes."""
        for worker_id, process in self.worker_processes.items():
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                
                if process.is_alive():
                    process.kill()
                    process.join()
                
                # Mark worker as failed
                if worker_id in self.workers:
                    self.workers[worker_id].mark_failed("Force shutdown")
    
    def _cleanup_resources(self):
        """Clean up all resources."""
        # Clean up profiles
        for worker_id in list(self.workers.keys()):
            try:
                self.profile_manager.cleanup_profile(worker_id)
            except Exception:
                pass  # Best effort cleanup
        
        # Attempt a manager-wide shutdown to catch any externally tracked profiles
        try:
            if hasattr(self.profile_manager, 'shutdown'):
                self.profile_manager.shutdown()
        except Exception:
            pass

        # Unregister workers from resource monitor
        try:
            if self.resource_monitor:
                for worker_id in list(self.workers.keys()):
                    self.resource_monitor.unregister_worker(worker_id)
        except Exception:
            pass

        # Clear collections
        self.workers.clear()
        self.worker_processes.clear()
    
    def _add_workers(self, count: int):
        """Add additional workers to the pool."""
        current_count = len(self.workers)
        
        for i in range(count):
            worker_id = f"worker_{current_count + i + 1:03d}"
            
            # Create worker instance
            worker = WorkerInstance(worker_id=worker_id)
            
            # Create profile for worker
            profile_path = self.profile_manager.create_profile(worker_id)
            worker.profile_path = profile_path
            
            # Optional: verify and register in monitor
            try:
                _ = self.profile_manager.verify_profile(worker_id)
            except Exception:
                pass
            try:
                if self.resource_monitor:
                    self.resource_monitor.register_worker(worker_id)
            except Exception:
                pass
            
            # Create worker process
            process = multiprocessing.Process(
                target=self._worker_main,
                args=(worker_id, profile_path, self.headless_config)
            )
            
            # Start process
            process.start()
            worker.process_id = process.pid
            worker.status = WorkerStatus.READY
            
            # Store worker and process
            self.workers[worker_id] = worker
            self.worker_processes[worker_id] = process
    
    def _remove_workers(self, count: int):
        """Remove workers from the pool."""
        workers_to_remove = list(self.workers.keys())[-count:]
        
        for worker_id in workers_to_remove:
            # Signal worker to stop
            if worker_id in self.worker_processes:
                process = self.worker_processes[worker_id]
                process.terminate()
                process.join(timeout=10)
                
                if process.is_alive():
                    process.kill()
                    process.join()
            
            # Cleanup profile
            try:
                self.profile_manager.cleanup_profile(worker_id)
            except Exception:
                pass
            
            # Unregister from monitor
            try:
                if self.resource_monitor:
                    self.resource_monitor.unregister_worker(worker_id)
            except Exception:
                pass
            
            # Remove from collections
            self.workers.pop(worker_id, None)
            self.worker_processes.pop(worker_id, None)
    
    def _start_monitoring(self):
        """Start background monitoring of workers."""
        # Placeholder for monitoring thread
        pass

    @staticmethod
    def _worker_main(worker_id: str, profile_path: str, headless_config: HeadlessConfiguration):
        """Main function for worker process."""
        # This would contain the actual worker logic
        # For now, this is a placeholder that will be implemented later
        print(f"Worker {worker_id} started with profile {profile_path}")
        # Simulate worker activity
        time.sleep(1)
        print(f"Worker {worker_id} finished")

    # Helper methods for task distribution and worker management
    def _validate_po_list(self, po_list: List[dict]) -> None:
        """Validate PO list structure and required fields."""
        required_fields = ['po_number', 'supplier', 'url', 'amount']
        for i, po_data in enumerate(po_list):
            if not isinstance(po_data, dict):
                raise ValueError(f"PO at index {i} must be a dictionary")
            for field in required_fields:
                if field not in po_data:
                    raise ValueError(f"PO at index {i} missing required field: {field}")
                if not po_data[field]:
                    raise ValueError(f"PO at index {i} has empty value for field: {field}")

    def _process_po_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single PO task (placeholder for actual implementation)."""
        # This will be implemented when the actual processing logic is integrated
        return {
            'success': True,
            'po_number': task_data.get('po_number'),
            'message': 'Task processed successfully'
        }

    def _signal_workers_pause(self) -> None:
        """Signal workers to pause after completing current tasks."""
        # Implementation would signal worker processes to pause
        # For now, this is a placeholder
        pass

    def _signal_workers_resume(self) -> None:
        """Signal workers to resume processing tasks."""
        # Implementation would signal worker processes to resume
        # For now, this is a placeholder
        pass


class ProfileAwareWorkerPool(WorkerPool):
    """Minimal contract-aligned extension that exposes profile-aware worker operations.

    Delegates core pooling to WorkerPool while providing per-worker lifecycle
    that uses ProfileManager to create/verify/cleanup profiles.
    """

    def __init__(self, max_workers: int, profile_manager: ProfileManager, worker_config_template: Optional[Any] = None, startup_timeout: float = 60.0):
        # Use HeadlessConfiguration with explicit 'enabled' flag
        default_headless = HeadlessConfiguration(enabled=True)
        super().__init__(headless_config=default_headless, pool_size=max_workers, profile_manager=profile_manager)
        self.worker_config_template = worker_config_template or _WorkerConfig(worker_id=1)
        self.startup_timeout = startup_timeout

    def start_worker(self, worker_config: Any) -> Any:
        start_ts = time.time()
        wid = str(worker_config.worker_id)
        try:
            # Create profile
            profile_path = self.profile_manager.create_profile(wid)

            verification_result = None
            if worker_config.verification_required:
                try:
                    verification_result = self.profile_manager.verify_profile(wid)
                except Exception:
                    verification_result = None

            # Register worker in pool structures if not present
            if wid not in self.workers:
                self.workers[wid] = WorkerInstance(worker_id=wid, profile_path=profile_path, status=WorkerStatus.READY)

            # Return startup result
            return _WorkerStartupResult(
                worker_id=worker_config.worker_id,
                success=True,
                profile=None,
                verification_result=verification_result,
                error_message=None,
                startup_duration_seconds=time.time() - start_ts,
            )
        except Exception as e:
            return _WorkerStartupResult(
                worker_id=worker_config.worker_id,
                success=False,
                profile=None,
                verification_result=None,
                error_message=str(e),
                startup_duration_seconds=time.time() - start_ts,
            )

    def start_all_workers(self, worker_configs: List[Any]) -> List[Any]:
        results: List[Any] = []
        for cfg in worker_configs:
            results.append(self.start_worker(cfg))
        return results

    def restart_worker(self, worker_id: int, new_profile: bool = True) -> Any:
        # Cleanup existing profile optionally and start again
        wid = str(worker_id)
        try:
            if new_profile:
                try:
                    self.profile_manager.cleanup_profile(wid)
                except Exception:
                    pass
            return self.start_worker(_WorkerConfig(worker_id=worker_id))
        except Exception as e:
            return _WorkerStartupResult(worker_id=worker_id, success=False, error_message=str(e))

    def stop_worker(self, worker_id: int, cleanup_profile: bool = True) -> None:
        wid = str(worker_id)
        # Stop underlying process if tracked
        if wid in self.worker_processes:
            proc = self.worker_processes[wid]
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=5)
        if cleanup_profile:
            try:
                self.profile_manager.cleanup_profile(wid)
            except Exception:
                pass
        # Remove from tracking
        self.workers.pop(wid, None)
        self.worker_processes.pop(wid, None)

    def stop_all_workers(self, cleanup_profiles: bool = True) -> None:
        for wid in list(self.workers.keys()):
            self.stop_worker(int(wid), cleanup_profile=cleanup_profiles)

    def get_worker_status(self, worker_id: int) -> Dict[str, Any]:
        wid = str(worker_id)
        worker = self.workers.get(wid)
        return worker.to_dict() if worker else {}

    def get_all_worker_status(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self.workers.values()]

    def verify_all_profiles(self) -> Dict[int, Any]:
        results: Dict[int, Any] = {}
        for wid in list(self.workers.keys()):
            try:
                res = self.profile_manager.verify_profile(wid)
            except Exception as e:  # fallback
                res = {'error': str(e)}
            results[int(wid)] = res
        return results

    def get_performance_metrics(self) -> Dict[str, Any]:
        status = self.get_status()
        return status.get('performance_metrics', {})
