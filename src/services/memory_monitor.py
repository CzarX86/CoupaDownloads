"""
MemoryMonitor service for system and worker memory tracking.
Monitors system memory usage and triggers worker restarts when thresholds are exceeded.
"""

import time
import psutil
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from ..models.worker import Worker


@dataclass
class MemoryThreshold:
    """Memory threshold configuration."""
    percentage: float  # 0.0 to 1.0
    action: str       # 'warn', 'restart_worker', 'restart_pool'
    cooldown_seconds: int = 60
    

class MemoryMonitor:
    """
    Service for monitoring system and worker memory usage.
    
    Responsibilities:
    - Monitor system memory usage against thresholds
    - Track individual worker memory consumption
    - Trigger appropriate actions when limits are exceeded
    - Provide memory usage statistics and alerts
    - Handle memory pressure scenarios gracefully
    """
    
    def __init__(self, 
                 memory_threshold: float = 0.75,
                 monitoring_interval: int = 5,
                 alert_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        """
        Initialize MemoryMonitor.
        
        Args:
            memory_threshold: System memory threshold (0.0 to 1.0)
            monitoring_interval: Monitoring interval in seconds
            alert_callback: Optional callback for memory alerts
        """
        self.memory_threshold = memory_threshold
        self.monitoring_interval = monitoring_interval
        self.alert_callback = alert_callback
        
        # Threading
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # Worker tracking
        self.workers: Dict[str, Worker] = {}
        
        # Memory tracking
        self.system_memory_history: List[Dict[str, Any]] = []
        self.worker_memory_history: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history_entries = 100
        
        # Threshold tracking
        self.thresholds = [
            MemoryThreshold(0.75, 'warn'),
            MemoryThreshold(0.85, 'restart_worker'),
            MemoryThreshold(0.95, 'restart_pool')
        ]
        self.last_threshold_action: Dict[str, float] = {}
        
        # Statistics
        self.stats = {
            'monitoring_cycles': 0,
            'threshold_violations': 0,
            'worker_restarts_triggered': 0,
            'pool_restarts_triggered': 0,
            'peak_system_memory_percent': 0.0,
            'peak_worker_memory_bytes': 0
        }
        
    def start_monitoring(self) -> bool:
        """
        Start memory monitoring thread.
        
        Returns:
            True if monitoring started successfully
        """
        with self._lock:
            if self._monitor_thread and self._monitor_thread.is_alive():
                return True
                
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                name="MemoryMonitor",
                daemon=True
            )
            self._monitor_thread.start()
            return True
            
    def stop_monitoring(self) -> bool:
        """
        Stop memory monitoring thread.
        
        Returns:
            True if monitoring stopped successfully
        """
        with self._lock:
            if not self._monitor_thread or not self._monitor_thread.is_alive():
                return True
                
            self._stop_event.set()
            self._monitor_thread.join(timeout=10)
            
            return not self._monitor_thread.is_alive()
            
    def register_worker(self, worker: Worker) -> None:
        """
        Register a worker for memory monitoring.
        
        Args:
            worker: Worker instance to monitor
        """
        with self._lock:
            self.workers[worker.worker_id] = worker
            self.worker_memory_history[worker.worker_id] = []
            
    def unregister_worker(self, worker_id: str) -> None:
        """
        Unregister a worker from memory monitoring.
        
        Args:
            worker_id: ID of worker to unregister
        """
        with self._lock:
            if worker_id in self.workers:
                del self.workers[worker_id]
            if worker_id in self.worker_memory_history:
                del self.worker_memory_history[worker_id]
                
    def get_system_memory_info(self) -> Dict[str, Any]:
        """
        Get current system memory information.
        
        Returns:
            Dictionary with memory information
        """
        memory = psutil.virtual_memory()
        
        return {
            'total_bytes': memory.total,
            'available_bytes': memory.available,
            'used_bytes': memory.used,
            'free_bytes': memory.free,
            'percent_used': memory.percent,
            'threshold_bytes': int(memory.total * self.memory_threshold),
            'threshold_exceeded': memory.percent / 100.0 > self.memory_threshold,
            'timestamp': time.time()
        }
        
    def get_worker_memory_info(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Get memory information for a specific worker.
        
        Args:
            worker_id: ID of worker to check
            
        Returns:
            Dictionary with worker memory info, or None if worker not found
        """
        with self._lock:
            if worker_id not in self.workers:
                return None
                
            worker = self.workers[worker_id]
            
            if not worker.has_process or worker.process_id is None:
                return {
                    'worker_id': worker_id,
                    'memory_bytes': 0,
                    'memory_mb': 0.0,
                    'cpu_percent': 0.0,
                    'process_exists': False,
                    'timestamp': time.time()
                }
                
            try:
                process = psutil.Process(worker.process_id)
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()
                
                return {
                    'worker_id': worker_id,
                    'process_id': worker.process_id,
                    'memory_bytes': memory_info.rss,
                    'memory_mb': round(memory_info.rss / 1024 / 1024, 2),
                    'cpu_percent': cpu_percent,
                    'process_exists': True,
                    'timestamp': time.time()
                }
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                return {
                    'worker_id': worker_id,
                    'memory_bytes': 0,
                    'memory_mb': 0.0,
                    'cpu_percent': 0.0,
                    'process_exists': False,
                    'timestamp': time.time()
                }
                
    def get_total_worker_memory(self) -> int:
        """
        Get total memory usage of all workers in bytes.
        
        Returns:
            Total memory usage in bytes
        """
        total_memory = 0
        
        for worker_id in self.workers.keys():
            worker_info = self.get_worker_memory_info(worker_id)
            if worker_info:
                total_memory += worker_info['memory_bytes']
                
        return total_memory
        
    def check_memory_thresholds(self) -> List[Dict[str, Any]]:
        """
        Check if any memory thresholds are exceeded.
        
        Returns:
            List of threshold violations with recommended actions
        """
        violations = []
        system_info = self.get_system_memory_info()
        current_percent = system_info['percent_used'] / 100.0
        
        for threshold in self.thresholds:
            if current_percent > threshold.percentage:
                # Check cooldown
                action_key = f"{threshold.action}_{threshold.percentage}"
                last_action_time = self.last_threshold_action.get(action_key, 0)
                
                if time.time() - last_action_time > threshold.cooldown_seconds:
                    violation = {
                        'threshold_percent': threshold.percentage,
                        'current_percent': current_percent,
                        'action': threshold.action,
                        'system_info': system_info,
                        'timestamp': time.time()
                    }
                    
                    violations.append(violation)
                    self.last_threshold_action[action_key] = time.time()
                    self.stats['threshold_violations'] += 1
                    
        return violations
        
    def get_highest_memory_worker(self) -> Optional[str]:
        """
        Get the worker ID with the highest memory usage.
        
        Returns:
            Worker ID with highest memory usage, or None if no workers
        """
        highest_memory = 0
        highest_worker_id = None
        
        for worker_id in self.workers.keys():
            worker_info = self.get_worker_memory_info(worker_id)
            if worker_info and worker_info['memory_bytes'] > highest_memory:
                highest_memory = worker_info['memory_bytes']
                highest_worker_id = worker_id
                
        return highest_worker_id
        
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive memory monitoring status.
        
        Returns:
            Dictionary with monitoring status
        """
        system_info = self.get_system_memory_info()
        total_worker_memory = self.get_total_worker_memory()
        
        worker_summaries = []
        for worker_id in self.workers.keys():
            worker_info = self.get_worker_memory_info(worker_id)
            if worker_info:
                worker_summaries.append({
                    'worker_id': worker_id,
                    'memory_mb': worker_info['memory_mb'],
                    'cpu_percent': worker_info['cpu_percent'],
                    'process_exists': worker_info['process_exists']
                })
                
        return {
            'monitoring_active': self._monitor_thread and self._monitor_thread.is_alive(),
            'system_memory': system_info,
            'total_worker_memory_bytes': total_worker_memory,
            'total_worker_memory_mb': round(total_worker_memory / 1024 / 1024, 2),
            'registered_workers': len(self.workers),
            'worker_summaries': worker_summaries,
            'memory_threshold': self.memory_threshold,
            'monitoring_interval': self.monitoring_interval,
            'statistics': self.stats.copy()
        }
        
    def _monitoring_loop(self) -> None:
        """
        Main memory monitoring loop.
        """
        while not self._stop_event.wait(self.monitoring_interval):
            try:
                self._perform_monitoring_cycle()
            except Exception as e:
                if self.alert_callback:
                    self.alert_callback('monitoring_error', {'error': str(e)})
                    
    def _perform_monitoring_cycle(self) -> None:
        """
        Perform one monitoring cycle.
        """
        self.stats['monitoring_cycles'] += 1
        
        # Get system memory info
        system_info = self.get_system_memory_info()
        
        # Update peak system memory
        current_percent = system_info['percent_used']
        if current_percent > self.stats['peak_system_memory_percent']:
            self.stats['peak_system_memory_percent'] = current_percent
            
        # Update worker memory info
        for worker_id in list(self.workers.keys()):
            worker_info = self.get_worker_memory_info(worker_id)
            if worker_info:
                # Update worker's memory in the worker object
                worker = self.workers[worker_id]
                worker.update_resource_usage(
                    worker_info['memory_bytes'],
                    worker_info['cpu_percent']
                )
                
                # Update peak worker memory
                if worker_info['memory_bytes'] > self.stats['peak_worker_memory_bytes']:
                    self.stats['peak_worker_memory_bytes'] = worker_info['memory_bytes']
                    
        # Store history
        self._store_memory_history(system_info)
        
        # Check thresholds
        violations = self.check_memory_thresholds()
        
        # Handle violations
        for violation in violations:
            self._handle_threshold_violation(violation)
            
    def _store_memory_history(self, system_info: Dict[str, Any]) -> None:
        """
        Store memory usage history.
        
        Args:
            system_info: System memory information
        """
        with self._lock:
            # Store system memory history
            self.system_memory_history.append(system_info)
            if len(self.system_memory_history) > self.max_history_entries:
                self.system_memory_history.pop(0)
                
            # Store worker memory history
            for worker_id in self.workers.keys():
                worker_info = self.get_worker_memory_info(worker_id)
                if worker_info:
                    if worker_id not in self.worker_memory_history:
                        self.worker_memory_history[worker_id] = []
                        
                    self.worker_memory_history[worker_id].append(worker_info)
                    if len(self.worker_memory_history[worker_id]) > self.max_history_entries:
                        self.worker_memory_history[worker_id].pop(0)
                        
    def _handle_threshold_violation(self, violation: Dict[str, Any]) -> None:
        """
        Handle a memory threshold violation.
        
        Args:
            violation: Threshold violation information
        """
        action = violation['action']
        
        if self.alert_callback:
            self.alert_callback('threshold_violation', violation)
            
        if action == 'restart_worker':
            highest_worker_id = self.get_highest_memory_worker()
            if highest_worker_id:
                self.stats['worker_restarts_triggered'] += 1
                if self.alert_callback:
                    self.alert_callback('restart_worker', {
                        'worker_id': highest_worker_id,
                        'reason': 'memory_threshold_exceeded',
                        'violation': violation
                    })
                    
        elif action == 'restart_pool':
            self.stats['pool_restarts_triggered'] += 1
            if self.alert_callback:
                self.alert_callback('restart_pool', {
                    'reason': 'memory_threshold_exceeded',
                    'violation': violation
                })
