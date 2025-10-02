"""
Worker entity for persistent worker management.
Represents a worker process that manages browser sessions and processes PO tasks.
"""

import time
import os
import multiprocessing
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from queue import Queue
from .profile import Profile
from .browser_session import BrowserSession
from .tab import POTask


class WorkerStatus(Enum):
    """Status of a worker."""
    CREATING = "creating"
    STARTING = "starting"
    READY = "ready"
    PROCESSING = "processing"
    IDLE = "idle"
    RESTARTING = "restarting"
    ERROR = "error"
    CRASHED = "crashed"
    STOPPING = "stopping"
    STOPPED = "stopped"


class WorkerError(Enum):
    """Types of worker errors."""
    PROCESS_LAUNCH_FAILED = "process_launch_failed"
    BROWSER_LAUNCH_FAILED = "browser_launch_failed"
    PROFILE_CREATION_FAILED = "profile_creation_failed"
    SESSION_CRASHED = "session_crashed"
    MEMORY_EXHAUSTED = "memory_exhausted"
    COMMUNICATION_LOST = "communication_lost"
    TASK_PROCESSING_FAILED = "task_processing_failed"
    WEBDRIVER_ERROR = "webdriver_error"
    SYSTEM_RESOURCE_ERROR = "system_resource_error"
    UNEXPECTED_TERMINATION = "unexpected_termination"


@dataclass
class WorkerConfiguration:
    """Configuration for a worker."""
    worker_id: str
    headless_mode: bool = True
    max_tabs_per_session: int = 5
    max_session_uptime_hours: int = 8
    max_idle_minutes: int = 30
    restart_on_memory_mb: int = 2048  # 2GB
    restart_on_error_count: int = 5
    browser_timeout_seconds: int = 60
    task_timeout_seconds: int = 300  # 5 minutes
    profile_base_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Worker:
    """
    Worker entity for persistent worker management.
    
    Each worker runs in its own process and manages:
    - A browser session with multiple tabs
    - PO task processing and coordination
    - Profile management and corruption handling
    - Resource monitoring and self-management
    """
    
    worker_id: str
    configuration: WorkerConfiguration
    status: WorkerStatus = WorkerStatus.CREATING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    last_activity_at: float = field(default_factory=time.time)
    last_restart_at: Optional[float] = None
    process_id: Optional[int] = None
    
    # Current state
    profile: Optional[Profile] = None
    browser_session: Optional[BrowserSession] = None
    current_tasks: Dict[str, POTask] = field(default_factory=dict)  # task_id -> task
    
    # Counters and metrics
    restart_count: int = 0
    error_count: int = 0
    total_tasks_processed: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    total_processing_time: float = 0.0
    
    # Error tracking
    last_error: Optional[WorkerError] = None
    last_error_message: Optional[str] = None
    last_error_at: Optional[float] = None
    
    # Resource monitoring
    memory_usage_bytes: int = 0
    cpu_usage_percent: float = 0.0
    
    # Communication
    task_queue: Optional[Queue] = None
    result_queue: Optional[Queue] = None
    control_queue: Optional[Queue] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize worker state."""
        if not self.worker_id:
            raise ValueError("worker_id is required")
        if not isinstance(self.configuration, WorkerConfiguration):
            raise ValueError("configuration must be a WorkerConfiguration instance")
            
    @property
    def is_active(self) -> bool:
        """Check if worker is active and ready for work."""
        return self.status in [WorkerStatus.READY, WorkerStatus.PROCESSING, WorkerStatus.IDLE]
        
    @property
    def is_processing(self) -> bool:
        """Check if worker is currently processing tasks."""
        return self.status == WorkerStatus.PROCESSING and len(self.current_tasks) > 0
        
    @property
    def is_error_state(self) -> bool:
        """Check if worker is in an error state."""
        return self.status in [WorkerStatus.ERROR, WorkerStatus.CRASHED]
        
    @property
    def is_available_for_tasks(self) -> bool:
        """Check if worker can accept new tasks."""
        if not self.is_active:
            return False
        if not self.browser_session or not self.browser_session.is_active:
            return False
        return len(self.browser_session.available_tabs) > 0
        
    @property
    def has_process(self) -> bool:
        """Check if worker has an active process."""
        if self.process_id is None:
            return False
        try:
            os.kill(self.process_id, 0)  # Check if process exists
            return True
        except (OSError, ProcessLookupError):
            return False
            
    @property
    def idle_seconds(self) -> float:
        """Seconds since last activity."""
        return time.time() - self.last_activity_at
        
    @property
    def age_seconds(self) -> float:
        """Age of worker in seconds."""
        return time.time() - self.created_at
        
    @property
    def uptime_seconds(self) -> float:
        """Uptime since worker started."""
        if self.started_at is None:
            return 0.0
        return time.time() - self.started_at
        
    @property
    def average_task_time(self) -> float:
        """Average time per completed task."""
        if self.total_tasks_completed == 0:
            return 0.0
        return self.total_processing_time / self.total_tasks_completed
        
    @property
    def success_rate(self) -> float:
        """Task success rate (0.0 to 1.0)."""
        if self.total_tasks_processed == 0:
            return 1.0
        return self.total_tasks_completed / self.total_tasks_processed
        
    def start_process(self, process_id: int) -> None:
        """Mark worker as started with process information."""
        self.process_id = process_id
        self.started_at = time.time()
        self.status = WorkerStatus.STARTING
        self.last_activity_at = time.time()
        
    def initialize_profile(self, profile: Profile) -> None:
        """Initialize worker with a profile."""
        if self.status != WorkerStatus.STARTING:
            raise RuntimeError(f"Cannot initialize profile for worker in status: {self.status}")
            
        self.profile = profile
        self.last_activity_at = time.time()
        
    def initialize_browser_session(self, session: BrowserSession) -> None:
        """Initialize worker with a browser session."""
        if self.profile is None:
            raise RuntimeError("Profile must be initialized before browser session")
            
        self.browser_session = session
        self.status = WorkerStatus.READY
        self.last_activity_at = time.time()
        
    def assign_task(self, task: POTask) -> bool:
        """
        Assign a task to this worker.
        Returns True if task was assigned successfully.
        """
        if not self.is_available_for_tasks:
            return False
            
        if task.task_id in self.current_tasks:
            raise ValueError(f"Task {task.task_id} is already assigned to this worker")
            
        # Assign task to an available tab
        if self.browser_session:
            assigned_tab = self.browser_session.assign_task_to_tab(task)
            if assigned_tab:
                self.current_tasks[task.task_id] = task
                self.status = WorkerStatus.PROCESSING
                self.last_activity_at = time.time()
                return True
                
        return False
        
    def complete_task(self, task_id: str, success: bool = True, processing_time: Optional[float] = None) -> Optional[POTask]:
        """
        Complete a task and update metrics.
        Returns the completed task if found.
        """
        if task_id not in self.current_tasks:
            return None
            
        task = self.current_tasks.pop(task_id)
        
        # Update counters
        self.total_tasks_processed += 1
        if success:
            self.total_tasks_completed += 1
        else:
            self.total_tasks_failed += 1
            
        # Update processing time
        if processing_time:
            self.total_processing_time += processing_time
        elif task.duration_seconds:
            self.total_processing_time += task.duration_seconds
            
        # Update status
        if len(self.current_tasks) == 0:
            self.status = WorkerStatus.IDLE
        else:
            self.status = WorkerStatus.PROCESSING
            
        self.last_activity_at = time.time()
        
        return task
        
    def record_error(self, error: WorkerError, message: str) -> None:
        """Record an error for this worker."""
        self.error_count += 1
        self.last_error = error
        self.last_error_message = message
        self.last_error_at = time.time()
        self.status = WorkerStatus.ERROR
        self.last_activity_at = time.time()
        
        # Store error in metadata for debugging
        if 'errors' not in self.metadata:
            self.metadata['errors'] = []
            
        self.metadata['errors'].append({
            'error': error.value,
            'message': message,
            'timestamp': time.time(),
            'process_id': self.process_id,
            'current_tasks': len(self.current_tasks)
        })
        
        # Keep only last 10 errors to prevent unbounded growth
        if len(self.metadata['errors']) > 10:
            self.metadata['errors'] = self.metadata['errors'][-10:]
            
    def mark_crashed(self) -> None:
        """Mark worker as crashed."""
        self.status = WorkerStatus.CRASHED
        self.record_error(WorkerError.UNEXPECTED_TERMINATION, "Worker process crashed or became unresponsive")
        
        # Fail all current tasks
        for task_id in list(self.current_tasks.keys()):
            self.complete_task(task_id, success=False)
            
    def start_restart(self) -> None:
        """Start restart process."""
        self.status = WorkerStatus.RESTARTING
        self.last_restart_at = time.time()
        self.restart_count += 1
        self.last_activity_at = time.time()
        
        # Fail all current tasks
        for task_id in list(self.current_tasks.keys()):
            self.complete_task(task_id, success=False)
            
    def update_resource_usage(self, memory_bytes: int, cpu_percent: float) -> None:
        """Update resource usage metrics."""
        self.memory_usage_bytes = memory_bytes
        self.cpu_usage_percent = cpu_percent
        self.last_activity_at = time.time()
        
    def cleanup_session(self) -> None:
        """Clean up browser session and profile."""
        if self.browser_session:
            self.browser_session.stop()
            
        if self.profile:
            self.profile.mark_ready()  # Make available for reuse
            
    def stop(self) -> None:
        """Stop the worker gracefully."""
        self.status = WorkerStatus.STOPPING
        
        # Fail all current tasks
        for task_id in list(self.current_tasks.keys()):
            self.complete_task(task_id, success=False)
            
        # Cleanup session and profile
        self.cleanup_session()
        
        self.status = WorkerStatus.STOPPED
        self.last_activity_at = time.time()
        
    def should_restart(self) -> bool:
        """
        Determine if worker should be restarted based on configuration and state.
        """
        config = self.configuration
        
        # Process is gone
        if not self.has_process and self.status != WorkerStatus.STOPPED:
            return True
            
        # Too many errors
        if self.error_count >= config.restart_on_error_count:
            return True
            
        # Memory usage too high
        memory_mb = self.memory_usage_bytes / 1024 / 1024
        if memory_mb > config.restart_on_memory_mb:
            return True
            
        # Worker has been idle too long
        idle_minutes = self.idle_seconds / 60
        if idle_minutes > config.max_idle_minutes and not self.is_processing:
            return True
            
        # In error or crashed state
        if self.is_error_state:
            return True
            
        # Profile is corrupted
        if self.profile and self.profile.is_corrupted:
            return True
            
        # Browser session should restart
        if self.browser_session and self.browser_session.should_restart():
            return True
            
        return False
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this worker."""
        return {
            'uptime_seconds': self.uptime_seconds,
            'restart_count': self.restart_count,
            'error_count': self.error_count,
            'total_tasks_processed': self.total_tasks_processed,
            'total_tasks_completed': self.total_tasks_completed,
            'total_tasks_failed': self.total_tasks_failed,
            'current_tasks': len(self.current_tasks),
            'success_rate': self.success_rate,
            'average_task_time': self.average_task_time,
            'memory_usage_bytes': self.memory_usage_bytes,
            'memory_usage_mb': round(self.memory_usage_bytes / 1024 / 1024, 2),
            'cpu_usage_percent': self.cpu_usage_percent,
            'idle_seconds': self.idle_seconds,
            'age_seconds': self.age_seconds,
            'has_process': self.has_process,
            'is_available_for_tasks': self.is_available_for_tasks,
            'browser_session_status': self.browser_session.status.value if self.browser_session else None,
            'profile_status': self.profile.status.value if self.profile else None
        }
        
    def get_current_tasks_info(self) -> List[Dict[str, Any]]:
        """Get information about current tasks."""
        return [
            {
                'task_id': task.task_id,
                'po_number': task.po_number,
                'started_at': task.started_at,
                'duration_seconds': task.duration_seconds,
                'retry_count': task.retry_count
            }
            for task in self.current_tasks.values()
        ]
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert worker to dictionary representation."""
        return {
            'worker_id': self.worker_id,
            'configuration': {
                'worker_id': self.configuration.worker_id,
                'headless_mode': self.configuration.headless_mode,
                'max_tabs_per_session': self.configuration.max_tabs_per_session,
                'max_session_uptime_hours': self.configuration.max_session_uptime_hours,
                'max_idle_minutes': self.configuration.max_idle_minutes,
                'restart_on_memory_mb': self.configuration.restart_on_memory_mb,
                'restart_on_error_count': self.configuration.restart_on_error_count,
                'metadata': self.configuration.metadata
            },
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'last_activity_at': self.last_activity_at,
            'last_restart_at': self.last_restart_at,
            'process_id': self.process_id,
            'restart_count': self.restart_count,
            'error_count': self.error_count,
            'total_tasks_processed': self.total_tasks_processed,
            'total_tasks_completed': self.total_tasks_completed,
            'total_tasks_failed': self.total_tasks_failed,
            'total_processing_time': self.total_processing_time,
            'last_error': self.last_error.value if self.last_error else None,
            'last_error_message': self.last_error_message,
            'last_error_at': self.last_error_at,
            'memory_usage_bytes': self.memory_usage_bytes,
            'cpu_usage_percent': self.cpu_usage_percent,
            'current_tasks': self.get_current_tasks_info(),
            'profile': self.profile.to_dict() if self.profile else None,
            'browser_session': self.browser_session.to_dict() if self.browser_session else None,
            'performance_metrics': self.get_performance_metrics(),
            'metadata': self.metadata.copy()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Worker':
        """Create worker from dictionary representation."""
        config_data = data['configuration']
        config = WorkerConfiguration(
            worker_id=config_data['worker_id'],
            headless_mode=config_data.get('headless_mode', True),
            max_tabs_per_session=config_data.get('max_tabs_per_session', 5),
            max_session_uptime_hours=config_data.get('max_session_uptime_hours', 8),
            max_idle_minutes=config_data.get('max_idle_minutes', 30),
            restart_on_memory_mb=config_data.get('restart_on_memory_mb', 2048),
            restart_on_error_count=config_data.get('restart_on_error_count', 5),
            metadata=config_data.get('metadata', {})
        )
        
        worker = cls(
            worker_id=data['worker_id'],
            configuration=config,
            status=WorkerStatus(data['status']),
            created_at=data.get('created_at', time.time()),
            started_at=data.get('started_at'),
            last_activity_at=data.get('last_activity_at', time.time()),
            last_restart_at=data.get('last_restart_at'),
            process_id=data.get('process_id'),
            restart_count=data.get('restart_count', 0),
            error_count=data.get('error_count', 0),
            total_tasks_processed=data.get('total_tasks_processed', 0),
            total_tasks_completed=data.get('total_tasks_completed', 0),
            total_tasks_failed=data.get('total_tasks_failed', 0),
            total_processing_time=data.get('total_processing_time', 0.0),
            last_error=WorkerError(data['last_error']) if data.get('last_error') else None,
            last_error_message=data.get('last_error_message'),
            last_error_at=data.get('last_error_at'),
            memory_usage_bytes=data.get('memory_usage_bytes', 0),
            cpu_usage_percent=data.get('cpu_usage_percent', 0.0),
            metadata=data.get('metadata', {})
        )
        
        # Restore profile and session (simplified - would need proper restoration in real implementation)
        if data.get('profile'):
            worker.profile = Profile.from_dict(data['profile'])
            
        if data.get('browser_session') and worker.profile:
            worker.browser_session = BrowserSession.from_dict(data['browser_session'], worker.profile)
            
        return worker
        
    def __str__(self) -> str:
        """String representation of worker."""
        return f"Worker(id={self.worker_id}, status={self.status.value}, tasks={len(self.current_tasks)})"
        
    def __repr__(self) -> str:
        """Detailed representation of worker."""
        return (f"Worker(worker_id='{self.worker_id}', status={self.status.value}, "
                f"process_id={self.process_id}, current_tasks={len(self.current_tasks)}, "
                f"uptime={self.uptime_seconds:.1f}s)")