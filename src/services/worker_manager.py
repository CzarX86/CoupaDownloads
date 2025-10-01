"""
WorkerManager service for worker lifecycle orchestration.
Manages worker creation, monitoring, restart, and coordination.
"""

import time
import threading
import multiprocessing
from typing import Optional, Dict, Any, List, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models.worker import Worker, WorkerConfiguration, WorkerStatus, WorkerError
from ..models.profile import Profile
from ..models.browser_session import BrowserSession
from .profile_manager import ProfileManager
from .memory_monitor import MemoryMonitor


class WorkerManager:
    """
    Service for managing worker lifecycle and coordination.
    
    Responsibilities:
    - Create and initialize workers with profiles
    - Monitor worker health and performance
    - Handle worker restarts and recovery
    - Coordinate worker scaling (up/down)
    - Manage worker resource allocation
    - Provide worker status and metrics
    """
    
    def __init__(self, 
                 profile_manager: ProfileManager,
                 memory_monitor: MemoryMonitor,
                 max_workers: int = 10,
                 restart_delay: int = 5,
                 health_check_interval: int = 30):
        """
        Initialize WorkerManager.
        
        Args:
            profile_manager: Profile management service
            memory_monitor: Memory monitoring service
            max_workers: Maximum number of workers
            restart_delay: Delay between restart attempts
            health_check_interval: Health check interval in seconds
        """
        self.profile_manager = profile_manager
        self.memory_monitor = memory_monitor
        self.max_workers = max_workers
        self.restart_delay = restart_delay
        self.health_check_interval = health_check_interval
        
        # Worker tracking
        self.workers: Dict[str, Worker] = {}
        self.worker_processes: Dict[str, multiprocessing.Process] = {}
        
        # Threading
        self._lock = threading.RLock()
        self._health_thread: Optional[threading.Thread] = None
        self._restart_executor = ThreadPoolExecutor(
            max_workers=3, 
            thread_name_prefix="worker_restart"
        )
        self._stop_event = threading.Event()
        
        # Callbacks
        self.worker_status_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None
        
        # Statistics
        self.stats = {
            'total_workers_created': 0,
            'total_workers_restarted': 0,
            'total_workers_failed': 0,
            'successful_restarts': 0,
            'failed_restarts': 0,
            'health_checks_performed': 0,
            'average_worker_uptime': 0.0
        }
        
    def start_health_monitoring(self) -> bool:
        """
        Start worker health monitoring.
        
        Returns:
            True if monitoring started successfully
        """
        with self._lock:
            if self._health_thread and self._health_thread.is_alive():
                return True
                
            self._stop_event.clear()
            self._health_thread = threading.Thread(
                target=self._health_monitoring_loop,
                name="WorkerManager-Health",
                daemon=True
            )
            self._health_thread.start()
            return True
            
    def stop_health_monitoring(self) -> bool:
        """
        Stop worker health monitoring.
        
        Returns:
            True if monitoring stopped successfully
        """
        with self._lock:
            if not self._health_thread or not self._health_thread.is_alive():
                return True
                
            self._stop_event.set()
            self._health_thread.join(timeout=10)
            
            return not self._health_thread.is_alive()
            
    def create_worker(self, worker_config: WorkerConfiguration) -> Optional[Worker]:
        """
        Create a new worker with configuration.
        
        Args:
            worker_config: Configuration for the new worker
            
        Returns:
            Worker instance if successful, None otherwise
        """
        with self._lock:
            if len(self.workers) >= self.max_workers:
                return None
                
            if worker_config.worker_id in self.workers:
                raise ValueError(f"Worker {worker_config.worker_id} already exists")
                
            try:
                # Create worker instance
                worker = Worker(
                    worker_id=worker_config.worker_id,
                    configuration=worker_config
                )
                
                # Get profile from profile manager
                profile = self.profile_manager.get_available_profile()
                if not profile:
                    return None
                    
                worker.initialize_profile(profile)
                
                # Register with memory monitor
                self.memory_monitor.register_worker(worker)
                
                # Store worker
                self.workers[worker_config.worker_id] = worker
                self.stats['total_workers_created'] += 1
                
                return worker
                
            except Exception:
                return None
                
    def start_worker(self, worker_id: str) -> bool:
        """
        Start a worker process.
        
        Args:
            worker_id: ID of worker to start
            
        Returns:
            True if worker started successfully
        """
        with self._lock:
            if worker_id not in self.workers:
                return False
                
            worker = self.workers[worker_id]
            
            if worker.has_process:
                return True  # Already started
                
            try:
                # Create browser session
                if worker.profile:
                    session = BrowserSession(
                        session_id=f"{worker_id}_session",
                        profile=worker.profile
                    )
                    worker.initialize_browser_session(session)
                    
                # Simulate process start (in real implementation, would spawn actual process)
                import os
                worker.start_process(os.getpid())
                
                # Notify status change
                self._notify_worker_status(worker_id, 'started', {'uptime': 0})
                
                return True
                
            except Exception as e:
                worker.record_error(WorkerError.PROCESS_LAUNCH_FAILED, f"Start failed: {e}")
                return False
                
    def stop_worker(self, worker_id: str) -> bool:
        """
        Stop a worker process.
        
        Args:
            worker_id: ID of worker to stop
            
        Returns:
            True if worker stopped successfully
        """
        with self._lock:
            if worker_id not in self.workers:
                return False
                
            worker = self.workers[worker_id]
            
            try:
                # Stop worker
                worker.stop()
                
                # Return profile to manager
                if worker.profile:
                    self.profile_manager.return_profile(
                        worker.profile.profile_id, 
                        corrupted=worker.profile.is_corrupted
                    )
                    
                # Unregister from memory monitor
                self.memory_monitor.unregister_worker(worker_id)
                
                # Clean up process tracking
                if worker_id in self.worker_processes:
                    del self.worker_processes[worker_id]
                    
                # Notify status change
                self._notify_worker_status(worker_id, 'stopped', {'final_status': worker.status.value})
                
                return True
                
            except Exception:
                return False
                
    def restart_worker(self, worker_id: str) -> bool:
        """
        Restart a worker (async operation).
        
        Args:
            worker_id: ID of worker to restart
            
        Returns:
            True if restart was initiated
        """
        if worker_id not in self.workers:
            return False
            
        # Submit restart task to executor
        future = self._restart_executor.submit(self._perform_worker_restart, worker_id)
        return True
        
    def remove_worker(self, worker_id: str) -> bool:
        """
        Remove a worker from management.
        
        Args:
            worker_id: ID of worker to remove
            
        Returns:
            True if worker was removed
        """
        with self._lock:
            if worker_id not in self.workers:
                return False
                
            # Stop worker first
            self.stop_worker(worker_id)
            
            # Remove from tracking
            del self.workers[worker_id]
            
            return True
            
    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """
        Get a worker by ID.
        
        Args:
            worker_id: Worker ID
            
        Returns:
            Worker instance or None
        """
        return self.workers.get(worker_id)
        
    def get_available_workers(self) -> List[Worker]:
        """
        Get list of workers available for tasks.
        
        Returns:
            List of available workers
        """
        with self._lock:
            return [w for w in self.workers.values() if w.is_available_for_tasks]
            
    def get_unhealthy_workers(self) -> List[Worker]:
        """
        Get list of workers that need restart.
        
        Returns:
            List of unhealthy workers
        """
        with self._lock:
            return [w for w in self.workers.values() if w.should_restart()]
            
    def scale_workers(self, target_count: int) -> bool:
        """
        Scale workers to target count.
        
        Args:
            target_count: Target number of workers
            
        Returns:
            True if scaling operation initiated
        """
        with self._lock:
            current_count = len(self.workers)
            
            if target_count > self.max_workers:
                target_count = self.max_workers
                
            if target_count == current_count:
                return True
                
            elif target_count > current_count:
                # Scale up
                return self._scale_up(target_count - current_count)
            else:
                # Scale down
                return self._scale_down(current_count - target_count)
                
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive worker manager status.
        
        Returns:
            Dictionary with status information
        """
        with self._lock:
            worker_summaries = []
            total_uptime = 0.0
            
            for worker in self.workers.values():
                uptime = worker.uptime_seconds
                total_uptime += uptime
                
                worker_summaries.append({
                    'worker_id': worker.worker_id,
                    'status': worker.status.value,
                    'uptime_seconds': uptime,
                    'current_tasks': len(worker.current_tasks),
                    'total_tasks_processed': worker.total_tasks_processed,
                    'success_rate': worker.success_rate,
                    'memory_usage_mb': round(worker.memory_usage_bytes / 1024 / 1024, 2),
                    'is_available': worker.is_available_for_tasks,
                    'should_restart': worker.should_restart()
                })
                
            # Calculate average uptime
            if self.workers:
                self.stats['average_worker_uptime'] = total_uptime / len(self.workers)
                
            return {
                'total_workers': len(self.workers),
                'active_workers': len([w for w in self.workers.values() if w.is_active]),
                'available_workers': len(self.get_available_workers()),
                'unhealthy_workers': len(self.get_unhealthy_workers()),
                'max_workers': self.max_workers,
                'health_monitoring_active': self._health_thread and self._health_thread.is_alive(),
                'worker_summaries': worker_summaries,
                'statistics': self.stats.copy()
            }
            
    def shutdown(self) -> None:
        """
        Shutdown worker manager and all workers.
        """
        with self._lock:
            # Stop health monitoring
            self.stop_health_monitoring()
            
            # Stop all workers
            worker_ids = list(self.workers.keys())
            for worker_id in worker_ids:
                self.stop_worker(worker_id)
                
            # Shutdown restart executor
            self._restart_executor.shutdown(wait=True)
            
    def _perform_worker_restart(self, worker_id: str) -> bool:
        """
        Perform worker restart operation.
        
        Args:
            worker_id: ID of worker to restart
            
        Returns:
            True if restart was successful
        """
        try:
            self.stats['total_workers_restarted'] += 1
            
            with self._lock:
                if worker_id not in self.workers:
                    return False
                    
                worker = self.workers[worker_id]
                worker.start_restart()
                
            # Notify restart started
            self._notify_worker_status(worker_id, 'restarting', {'reason': 'health_check_failed'})
            
            # Wait for restart delay
            time.sleep(self.restart_delay)
            
            # Stop worker
            stop_success = self.stop_worker(worker_id)
            
            # Start worker
            start_success = self.start_worker(worker_id)
            
            if stop_success and start_success:
                self.stats['successful_restarts'] += 1
                self._notify_worker_status(worker_id, 'restart_completed', {'success': True})
                return True
            else:
                self.stats['failed_restarts'] += 1
                self._notify_worker_status(worker_id, 'restart_failed', {'success': False})
                return False
                
        except Exception:
            self.stats['failed_restarts'] += 1
            return False
            
    def _scale_up(self, count: int) -> bool:
        """
        Scale up by creating new workers.
        
        Args:
            count: Number of workers to add
            
        Returns:
            True if scaling completed
        """
        created = 0
        
        for i in range(count):
            worker_id = f"worker_{int(time.time())}_{i}"
            config = WorkerConfiguration(worker_id=worker_id)
            
            worker = self.create_worker(config)
            if worker and self.start_worker(worker_id):
                created += 1
            else:
                break
                
        return created == count
        
    def _scale_down(self, count: int) -> bool:
        """
        Scale down by removing workers.
        
        Args:
            count: Number of workers to remove
            
        Returns:
            True if scaling completed
        """
        # Remove least busy workers first
        workers_by_load = sorted(
            self.workers.values(),
            key=lambda w: len(w.current_tasks)
        )
        
        removed = 0
        for worker in workers_by_load[:count]:
            if not worker.is_processing:  # Don't remove busy workers
                if self.remove_worker(worker.worker_id):
                    removed += 1
                    
        return removed == count
        
    def _health_monitoring_loop(self) -> None:
        """
        Main health monitoring loop.
        """
        while not self._stop_event.wait(self.health_check_interval):
            try:
                self._perform_health_check()
            except Exception:
                # Continue monitoring even if health check fails
                pass
                
    def _perform_health_check(self) -> None:
        """
        Perform health check on all workers.
        """
        self.stats['health_checks_performed'] += 1
        
        unhealthy_workers = self.get_unhealthy_workers()
        
        for worker in unhealthy_workers:
            # Trigger restart for unhealthy workers
            self.restart_worker(worker.worker_id)
            
    def _notify_worker_status(self, worker_id: str, event: str, data: Dict[str, Any]) -> None:
        """
        Notify worker status change.
        
        Args:
            worker_id: Worker ID
            event: Status event
            data: Additional event data
        """
        if self.worker_status_callback:
            try:
                self.worker_status_callback(worker_id, event, data)
            except Exception:
                # Don't let callback errors affect worker management
                pass
