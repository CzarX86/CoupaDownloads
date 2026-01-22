"""
Enhanced Worker model with process management capabilities.

This module provides the Worker data model with support for:
- Process lifecycle management
- Status tracking and transitions
- Memory usage monitoring
- Task processing coordination
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
from datetime import datetime
import uuid


class WorkerStatus(Enum):
    """Worker operational status enumeration."""
    STARTING = "starting"
    READY = "ready"
    PROCESSING = "processing"
    IDLE = "idle"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    CRASHED = "crashed"
    RESTARTING = "restarting"


@dataclass
class Worker:
    """
    Enhanced Worker model with process management.
    
    Represents a long-running worker process that maintains a browser session
    and processes POs via tabs. Includes comprehensive state tracking and
    resource monitoring.
    """
    
    # Core identification
    worker_id: str = field(default_factory=lambda: f"worker-{uuid.uuid4().hex[:8]}")
    profile_path: str = ""
    
    # Process management
    process_id: Optional[int] = None
    browser_session: Optional[Any] = None  # BrowserSession instance
    current_task: Optional[Any] = None     # POTask instance
    
    # Status tracking
    status: WorkerStatus = WorkerStatus.STARTING
    startup_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    # Resource monitoring
    memory_usage: int = 0  # Memory consumption in bytes
    processed_count: int = 0  # Number of POs completed by this worker
    
    # Error tracking
    last_error: Optional[str] = None
    error_count: int = 0
    restart_attempts: int = 0
    max_restart_attempts: int = 3
    
    # Configuration
    headless_mode: bool = True
    task_timeout: float = 300.0  # 5 minutes per PO
    
    def __post_init__(self):
        """Validate worker configuration after initialization."""
        if not self.worker_id:
            raise ValueError("Worker ID cannot be empty")
        
        if not self.profile_path:
            raise ValueError("Profile path cannot be empty")
        
        if self.max_restart_attempts < 0:
            raise ValueError("Max restart attempts must be non-negative")
        
        if self.task_timeout <= 0:
            raise ValueError("Task timeout must be positive")
    
    def is_available(self) -> bool:
        """Check if worker is available for new tasks."""
        return self.status in [WorkerStatus.READY, WorkerStatus.IDLE]
    
    def is_processing(self) -> bool:
        """Check if worker is currently processing a task."""
        return self.status == WorkerStatus.PROCESSING
    
    def is_healthy(self) -> bool:
        """Check if worker is in a healthy operational state."""
        return self.status not in [WorkerStatus.CRASHED, WorkerStatus.TERMINATED]
    
    def can_restart(self) -> bool:
        """Check if worker can be restarted after failure."""
        return (self.restart_attempts < self.max_restart_attempts and 
                self.status in [WorkerStatus.CRASHED, WorkerStatus.TERMINATED])
    
    def update_status(self, new_status: WorkerStatus, error_message: Optional[str] = None):
        """
        Update worker status with validation and error tracking.
        
        Args:
            new_status: New status to transition to
            error_message: Optional error message for failure states
        """
        if not self._is_valid_transition(self.status, new_status):
            raise ValueError(f"Invalid status transition: {self.status} -> {new_status}")
        
        old_status = self.status
        self.status = new_status
        self.last_activity = datetime.now()
        
        # Handle error states
        if new_status == WorkerStatus.CRASHED:
            self.error_count += 1
            if error_message:
                self.last_error = error_message
        
        # Handle restart attempts
        if new_status == WorkerStatus.RESTARTING:
            self.restart_attempts += 1
        
        # Reset error tracking on successful recovery
        if old_status in [WorkerStatus.CRASHED, WorkerStatus.RESTARTING] and new_status == WorkerStatus.READY:
            self.last_error = None
    
    def _is_valid_transition(self, from_status: WorkerStatus, to_status: WorkerStatus) -> bool:
        """
        Validate worker status transitions.
        
        Valid transitions based on worker lifecycle:
        - STARTING → READY, CRASHED
        - READY → PROCESSING, TERMINATING, CRASHED
        - PROCESSING → IDLE, READY, TERMINATING, CRASHED
        - IDLE → READY, TERMINATING, CRASHED  
        - TERMINATING → TERMINATED
        - CRASHED → RESTARTING, TERMINATED
        - RESTARTING → READY, CRASHED
        - TERMINATED → (no transitions allowed)
        """
        valid_transitions = {
            WorkerStatus.STARTING: [WorkerStatus.READY, WorkerStatus.CRASHED],
            WorkerStatus.READY: [WorkerStatus.PROCESSING, WorkerStatus.TERMINATING, WorkerStatus.CRASHED],
            WorkerStatus.PROCESSING: [WorkerStatus.IDLE, WorkerStatus.READY, WorkerStatus.TERMINATING, WorkerStatus.CRASHED],
            WorkerStatus.IDLE: [WorkerStatus.READY, WorkerStatus.TERMINATING, WorkerStatus.CRASHED],
            WorkerStatus.TERMINATING: [WorkerStatus.TERMINATED],
            WorkerStatus.CRASHED: [WorkerStatus.RESTARTING, WorkerStatus.TERMINATED],
            WorkerStatus.RESTARTING: [WorkerStatus.READY, WorkerStatus.CRASHED],
            WorkerStatus.TERMINATED: []  # No transitions from terminated state
        }
        
        return to_status in valid_transitions.get(from_status, [])
    
    def assign_task(self, task: Any):
        """
        Assign a PO task to this worker.
        
        Args:
            task: POTask instance to assign
            
        Raises:
            ValueError: If worker is not available for tasks
        """
        if not self.is_available():
            raise ValueError(f"Worker {self.worker_id} is not available (status: {self.status})")
        
        self.current_task = task
        self.update_status(WorkerStatus.PROCESSING)
    
    def complete_task(self, success: bool = True):
        """
        Mark current task as completed and update worker state.
        
        Args:
            success: Whether the task completed successfully
        """
        if not self.current_task:
            raise ValueError("No task currently assigned to complete")
        
        if success:
            self.processed_count += 1
        
        self.current_task = None
        self.update_status(WorkerStatus.READY)
    
    def update_memory_usage(self, memory_bytes: int):
        """
        Update worker memory usage tracking.
        
        Args:
            memory_bytes: Current memory consumption in bytes
        """
        if memory_bytes < 0:
            raise ValueError("Memory usage cannot be negative")
        
        self.memory_usage = memory_bytes
        self.last_activity = datetime.now()
    
    def get_health_status(self) -> dict:
        """
        Get comprehensive health status for monitoring.
        
        Returns:
            Dictionary containing health metrics
        """
        uptime = (datetime.now() - self.startup_time).total_seconds()
        last_activity_seconds = (datetime.now() - self.last_activity).total_seconds()
        
        return {
            'worker_id': self.worker_id,
            'status': self.status.value,
            'is_healthy': self.is_healthy(),
            'is_available': self.is_available(),
            'memory_usage': self.memory_usage,
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'restart_attempts': self.restart_attempts,
            'uptime_seconds': uptime,
            'last_activity_seconds': last_activity_seconds,
            'last_error': self.last_error,
            'current_task': self.current_task.task_id if self.current_task else None,
            'can_restart': self.can_restart()
        }
    
    def to_dict(self) -> dict:
        """Convert worker to dictionary representation."""
        return {
            'worker_id': self.worker_id,
            'profile_path': self.profile_path,
            'process_id': self.process_id,
            'status': self.status.value,
            'startup_time': self.startup_time.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'memory_usage': self.memory_usage,
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'restart_attempts': self.restart_attempts,
            'max_restart_attempts': self.max_restart_attempts,
            'headless_mode': self.headless_mode,
            'task_timeout': self.task_timeout,
            'last_error': self.last_error,
            'current_task_id': self.current_task.task_id if self.current_task else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Worker':
        """Create worker from dictionary representation."""
        # Convert string status back to enum
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = WorkerStatus(data['status'])
        
        # Convert ISO datetime strings back to datetime objects
        if 'startup_time' in data and isinstance(data['startup_time'], str):
            data['startup_time'] = datetime.fromisoformat(data['startup_time'])
        
        if 'last_activity' in data and isinstance(data['last_activity'], str):
            data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        
        # Remove fields that can't be directly set
        excluded_fields = ['current_task_id']
        worker_data = {k: v for k, v in data.items() if k not in excluded_fields}
        
        return cls(**worker_data)
    
    def __str__(self) -> str:
        """String representation of worker."""
        return f"Worker({self.worker_id}, {self.status.value}, processed={self.processed_count})"
    
    def __repr__(self) -> str:
        """Detailed representation of worker."""
        return (f"Worker(worker_id='{self.worker_id}', status={self.status}, "
                f"processed_count={self.processed_count}, memory_usage={self.memory_usage})")