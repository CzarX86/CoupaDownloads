"""
GracefulShutdown service for coordinated shutdown management.
Orchestrates shutdown sequence across all worker pool components.
"""

import time
import threading
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from .signal_handler import SignalHandler
from ..models.worker_pool import PersistentWorkerPool, PoolStatus


@dataclass
class ShutdownPhase:
    """Represents a phase in the shutdown sequence."""
    name: str
    description: str
    timeout: int
    action: Callable[[], bool]
    required: bool = True  # If False, failure won't stop shutdown
    

class GracefulShutdown:
    """
    Service for coordinating graceful shutdown of worker pool.
    
    Responsibilities:
    - Orchestrate shutdown sequence across all components
    - Ensure tasks are completed or safely failed
    - Clean up resources in proper order
    - Provide shutdown progress and status
    - Handle timeout scenarios with fallback strategies
    """
    
    def __init__(self, 
                 worker_pool: PersistentWorkerPool,
                 total_timeout: int = 60,
                 task_completion_timeout: int = 30):
        """
        Initialize GracefulShutdown.
        
        Args:
            worker_pool: Worker pool to manage shutdown for
            total_timeout: Total shutdown timeout in seconds
            task_completion_timeout: Time to wait for task completion
        """
        self.worker_pool = worker_pool
        self.total_timeout = total_timeout
        self.task_completion_timeout = task_completion_timeout
        
        # Signal handler integration
        self.signal_handler = SignalHandler(shutdown_timeout=total_timeout)
        
        # Shutdown state
        self.shutdown_started = threading.Event()
        self.shutdown_completed = threading.Event()
        self.shutdown_failed = threading.Event()
        
        # Progress tracking
        self.current_phase: Optional[str] = None
        self.completed_phases: List[str] = []
        self.failed_phases: List[str] = []
        
        # Shutdown phases
        self.phases = [
            ShutdownPhase(
                name="stop_task_acceptance",
                description="Stop accepting new tasks",
                timeout=5,
                action=self._stop_task_acceptance
            ),
            ShutdownPhase(
                name="complete_active_tasks",
                description="Wait for active tasks to complete",
                timeout=task_completion_timeout,
                action=self._complete_active_tasks
            ),
            ShutdownPhase(
                name="stop_workers",
                description="Stop all worker processes",
                timeout=20,
                action=self._stop_workers
            ),
            ShutdownPhase(
                name="cleanup_resources",
                description="Clean up profiles and temporary files",
                timeout=10,
                action=self._cleanup_resources,
                required=False  # Don't fail shutdown if cleanup fails
            ),
            ShutdownPhase(
                name="stop_monitoring",
                description="Stop monitoring threads",
                timeout=10,
                action=self._stop_monitoring,
                required=False
            )
        ]
        
        # Statistics
        self.stats = {
            'shutdown_start_time': None,
            'shutdown_end_time': None,
            'total_shutdown_time': 0.0,
            'phases_completed': 0,
            'phases_failed': 0,
            'tasks_completed_during_shutdown': 0,
            'tasks_failed_during_shutdown': 0,
            'workers_stopped': 0
        }
        
        # Register signal handlers
        self.signal_handler.register_shutdown_handler(
            "worker_pool_shutdown",
            self.shutdown,
            timeout=total_timeout,
            priority=1
        )
        
    def initialize(self) -> bool:
        """
        Initialize signal handling.
        
        Returns:
            True if initialization was successful
        """
        return self.signal_handler.register_signals()
        
    def shutdown(self, timeout: Optional[int] = None) -> bool:
        """
        Execute graceful shutdown sequence.
        
        Args:
            timeout: Override default shutdown timeout
            
        Returns:
            True if shutdown completed successfully
        """
        if self.shutdown_started.is_set():
            return self.wait_for_completion(timeout)
            
        self.shutdown_started.set()
        self.stats['shutdown_start_time'] = time.time()
        
        if timeout is None:
            timeout = self.total_timeout
            
        start_time = time.time()
        success = True
        
        try:
            for phase in self.phases:
                if self.signal_handler.is_emergency_shutdown():
                    break  # Skip remaining phases for emergency shutdown
                    
                elapsed = time.time() - start_time
                remaining_time = timeout - elapsed
                
                if remaining_time <= 0:
                    success = False
                    break
                    
                phase_timeout = min(phase.timeout, remaining_time)
                phase_success = self._execute_phase(phase, phase_timeout)
                
                if not phase_success and phase.required:
                    success = False
                    if not self.signal_handler.is_emergency_shutdown():
                        break  # Stop on required phase failure
                        
        except Exception:
            success = False
            
        finally:
            self.stats['shutdown_end_time'] = time.time()
            self.stats['total_shutdown_time'] = self.stats['shutdown_end_time'] - self.stats['shutdown_start_time']
            
            if success:
                self.shutdown_completed.set()
            else:
                self.shutdown_failed.set()
                
        return success
        
    def wait_for_completion(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for shutdown to complete.
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            True if shutdown completed successfully
        """
        if timeout is None:
            timeout = self.total_timeout
            
        if self.shutdown_completed.wait(timeout):
            return True
        elif self.shutdown_failed.is_set():
            return False
        else:
            # Timeout
            return False
            
    def get_progress(self) -> Dict[str, Any]:
        """
        Get shutdown progress information.
        
        Returns:
            Dictionary with progress details
        """
        return {
            'shutdown_started': self.shutdown_started.is_set(),
            'shutdown_completed': self.shutdown_completed.is_set(),
            'shutdown_failed': self.shutdown_failed.is_set(),
            'current_phase': self.current_phase,
            'completed_phases': self.completed_phases.copy(),
            'failed_phases': self.failed_phases.copy(),
            'total_phases': len(self.phases),
            'progress_percent': round((len(self.completed_phases) / len(self.phases)) * 100, 1),
            'emergency_shutdown': self.signal_handler.is_emergency_shutdown(),
            'statistics': self.stats.copy()
        }
        
    def _execute_phase(self, phase: ShutdownPhase, timeout: float) -> bool:
        """
        Execute a shutdown phase.
        
        Args:
            phase: Phase to execute
            timeout: Timeout for this phase
            
        Returns:
            True if phase completed successfully
        """
        self.current_phase = phase.name
        
        try:
            # Execute phase action with timeout
            result_container = {'success': False}
            
            def phase_wrapper():
                try:
                    result_container['success'] = phase.action()
                except Exception:
                    result_container['success'] = False
                    
            phase_thread = threading.Thread(
                target=phase_wrapper,
                name=f"Shutdown-{phase.name}"
            )
            
            phase_thread.start()
            phase_thread.join(timeout)
            
            if phase_thread.is_alive():
                # Phase timed out
                self.failed_phases.append(phase.name)
                self.stats['phases_failed'] += 1
                return False
                
            success = result_container['success']
            
            if success:
                self.completed_phases.append(phase.name)
                self.stats['phases_completed'] += 1
            else:
                self.failed_phases.append(phase.name)
                self.stats['phases_failed'] += 1
                
            return success
            
        except Exception:
            self.failed_phases.append(phase.name)
            self.stats['phases_failed'] += 1
            return False
            
    def _stop_task_acceptance(self) -> bool:
        """
        Stop accepting new tasks.
        
        Returns:
            True if successful
        """
        try:
            # Mark pool as stopping to prevent new tasks
            self.worker_pool.status = PoolStatus.STOPPING
            return True
        except Exception:
            return False
            
    def _complete_active_tasks(self) -> bool:
        """
        Wait for active tasks to complete.
        
        Returns:
            True if all tasks completed or timed out gracefully
        """
        try:
            start_time = time.time()
            check_interval = 2  # Check every 2 seconds
            
            while time.time() - start_time < self.task_completion_timeout:
                status = self.worker_pool.get_status()
                
                # Check if any workers are still processing
                processing_workers = status['processing_workers']
                if processing_workers == 0:
                    return True
                    
                # Check for emergency shutdown
                if self.signal_handler.is_emergency_shutdown():
                    return True  # Skip waiting for emergency
                    
                time.sleep(check_interval)
                
            # Timeout reached - fail any remaining tasks
            for worker in self.worker_pool.workers.values():
                for task_id in list(worker.current_tasks.keys()):
                    worker.complete_task(task_id, success=False)
                    self.stats['tasks_failed_during_shutdown'] += 1
                    
            return True
            
        except Exception:
            return False
            
    def _stop_workers(self) -> bool:
        """
        Stop all worker processes.
        
        Returns:
            True if all workers stopped successfully
        """
        try:
            stopped_count = 0
            
            for worker in self.worker_pool.workers.values():
                try:
                    worker.stop()
                    stopped_count += 1
                except Exception:
                    pass
                    
            self.stats['workers_stopped'] = stopped_count
            return stopped_count == len(self.worker_pool.workers)
            
        except Exception:
            return False
            
    def _cleanup_resources(self) -> bool:
        """
        Clean up profiles and temporary resources.
        
        Returns:
            True if cleanup was successful
        """
        try:
            cleanup_success = True
            
            # Clean up profiles
            for profile in self.worker_pool.available_profiles:
                try:
                    profile.cleanup()
                except Exception:
                    cleanup_success = False
                    
            return cleanup_success
            
        except Exception:
            return False
            
    def _stop_monitoring(self) -> bool:
        """
        Stop monitoring threads.
        
        Returns:
            True if monitoring stopped successfully
        """
        try:
            # Signal shutdown to monitoring threads
            self.worker_pool.shutdown_event.set()
            
            # Wait for threads to stop
            if self.worker_pool.monitor_thread and self.worker_pool.monitor_thread.is_alive():
                self.worker_pool.monitor_thread.join(timeout=5)
                
            if self.worker_pool.maintenance_thread and self.worker_pool.maintenance_thread.is_alive():
                self.worker_pool.maintenance_thread.join(timeout=5)
                
            return True
            
        except Exception:
            return False