"""
Tab entity for browser tab management within persistent sessions.
Represents individual browser tabs that process PO tasks.
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class TabStatus(Enum):
    """Status of a browser tab."""
    CREATING = "creating"
    READY = "ready"
    NAVIGATING = "navigating"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    CRASHED = "crashed"
    CLOSING = "closing"
    CLOSED = "closed"


class TabError(Enum):
    """Types of tab errors."""
    NAVIGATION_TIMEOUT = "navigation_timeout"
    PAGE_LOAD_FAILED = "page_load_failed"
    ELEMENT_NOT_FOUND = "element_not_found"
    INTERACTION_FAILED = "interaction_failed"
    DOWNLOAD_FAILED = "download_failed"
    JAVASCRIPT_ERROR = "javascript_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_FAILED = "authentication_failed"
    UNEXPECTED_PAGE = "unexpected_page"
    BROWSER_CRASH = "browser_crash"


@dataclass
class POTask:
    """PO processing task for a tab."""
    task_id: str
    po_number: str
    po_data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 0  # Higher numbers = higher priority
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.completed_at is not None
        
    @property
    def is_started(self) -> bool:
        """Check if task has been started."""
        return self.started_at is not None
        
    @property
    def duration_seconds(self) -> Optional[float]:
        """Duration of task processing in seconds."""
        if not self.is_started or self.started_at is None:
            return None
        if not self.is_completed:
            return time.time() - self.started_at
        if self.completed_at is None:
            return None
        return self.completed_at - self.started_at
        
    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries


@dataclass
class Tab:
    """
    Browser tab entity for PO processing.
    
    Each tab operates within a browser session and processes PO tasks sequentially.
    Maintains its own navigation state and error handling.
    """
    
    tab_id: str
    session_id: str
    status: TabStatus = TabStatus.CREATING
    created_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    current_url: Optional[str] = None
    current_task: Optional[POTask] = None
    completed_tasks: List[str] = field(default_factory=list)  # task_ids
    failed_tasks: List[str] = field(default_factory=list)  # task_ids
    error_count: int = 0
    last_error: Optional[TabError] = None
    last_error_message: Optional[str] = None
    last_error_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics
    total_processing_time: float = 0.0
    average_task_time: float = 0.0
    task_success_rate: float = 1.0
    
    def __post_init__(self):
        """Initialize tab state."""
        if not self.tab_id:
            raise ValueError("tab_id is required")
        if not self.session_id:
            raise ValueError("session_id is required")
            
    @property
    def is_available(self) -> bool:
        """Check if tab is available for new tasks."""
        return self.status in [TabStatus.READY, TabStatus.WAITING]
        
    @property
    def is_processing(self) -> bool:
        """Check if tab is currently processing a task."""
        return self.status == TabStatus.PROCESSING
        
    @property
    def is_error_state(self) -> bool:
        """Check if tab is in an error state."""
        return self.status in [TabStatus.ERROR, TabStatus.CRASHED]
        
    @property
    def idle_seconds(self) -> float:
        """Seconds since last activity."""
        return time.time() - self.last_activity_at
        
    @property
    def age_seconds(self) -> float:
        """Age of tab in seconds."""
        return time.time() - self.created_at
        
    @property
    def has_current_task(self) -> bool:
        """Check if tab has a current task."""
        return self.current_task is not None
        
    @property
    def total_tasks_processed(self) -> int:
        """Total number of tasks processed (completed + failed)."""
        return len(self.completed_tasks) + len(self.failed_tasks)
        
    def mark_ready(self) -> None:
        """Mark tab as ready for new tasks."""
        if self.status in [TabStatus.CREATING, TabStatus.WAITING, TabStatus.PROCESSING, TabStatus.NAVIGATING]:
            self.status = TabStatus.READY
            self.last_activity_at = time.time()
        else:
            raise RuntimeError(f"Cannot mark tab ready from status: {self.status}")
            
    def start_task(self, task: POTask) -> None:
        """Start processing a new task."""
        if not self.is_available:
            raise RuntimeError(f"Tab {self.tab_id} is not available for new tasks (status: {self.status})")
            
        if self.current_task is not None:
            raise RuntimeError(f"Tab {self.tab_id} already has a current task: {self.current_task.task_id}")
            
        self.current_task = task
        self.current_task.started_at = time.time()
        self.status = TabStatus.PROCESSING
        self.last_activity_at = time.time()
        
    def complete_task(self, success: bool = True) -> Optional[POTask]:
        """
        Complete the current task.
        Returns the completed task, or None if no task was active.
        """
        if self.current_task is None:
            return None
            
        task = self.current_task
        task.completed_at = time.time()
        
        # Update task success tracking
        if success:
            self.completed_tasks.append(task.task_id)
        else:
            self.failed_tasks.append(task.task_id)
            
        # Update performance metrics
        if task.duration_seconds:
            self.total_processing_time += task.duration_seconds
            self._update_average_task_time()
            
        self._update_success_rate()
        
        # Clear current task
        self.current_task = None
        self.status = TabStatus.READY
        self.last_activity_at = time.time()
        
        return task
        
    def fail_task(self, error: TabError, error_message: str) -> Optional[POTask]:
        """
        Fail the current task with an error.
        Returns the failed task, or None if no task was active.
        """
        if self.current_task is None:
            return None
            
        self.record_error(error, error_message)
        return self.complete_task(success=False)
        
    def record_error(self, error: TabError, message: str) -> None:
        """Record an error for this tab."""
        self.error_count += 1
        self.last_error = error
        self.last_error_message = message
        self.last_error_at = time.time()
        self.status = TabStatus.ERROR
        self.last_activity_at = time.time()
        
        # Store error in metadata for debugging
        if 'errors' not in self.metadata:
            self.metadata['errors'] = []
            
        self.metadata['errors'].append({
            'error': error.value,
            'message': message,
            'timestamp': time.time(),
            'task_id': self.current_task.task_id if self.current_task else None
        })
        
        # Keep only last 10 errors to prevent unbounded growth
        if len(self.metadata['errors']) > 10:
            self.metadata['errors'] = self.metadata['errors'][-10:]
            
    def clear_error(self) -> None:
        """Clear error state and mark tab as ready."""
        if self.is_error_state:
            self.status = TabStatus.READY
            self.last_activity_at = time.time()
            
    def navigate_to(self, url: str) -> None:
        """Mark tab as navigating to a URL."""
        self.status = TabStatus.NAVIGATING
        self.current_url = url
        self.last_activity_at = time.time()
        
    def mark_crashed(self) -> None:
        """Mark tab as crashed."""
        self.status = TabStatus.CRASHED
        self.record_error(TabError.BROWSER_CRASH, "Tab crashed or became unresponsive")
        
        # If tab had a current task, fail it
        if self.current_task:
            self.complete_task(success=False)
            
    def close(self) -> None:
        """Close the tab."""
        self.status = TabStatus.CLOSING
        
        # If tab had a current task, fail it
        if self.current_task:
            self.record_error(TabError.BROWSER_CRASH, "Tab closed while processing task")
            self.complete_task(success=False)
            
        self.status = TabStatus.CLOSED
        self.last_activity_at = time.time()
        
    def reset(self) -> None:
        """Reset tab to clean state while preserving metrics."""
        if self.current_task:
            self.fail_task(TabError.UNEXPECTED_PAGE, "Tab reset while processing task")
            
        self.status = TabStatus.READY
        self.current_url = None
        self.current_task = None
        self.last_activity_at = time.time()
        
        # Clear recent errors but keep metrics
        if 'errors' in self.metadata:
            del self.metadata['errors']
            
    def _update_average_task_time(self) -> None:
        """Update average task processing time."""
        total_tasks = self.total_tasks_processed
        if total_tasks > 0:
            self.average_task_time = self.total_processing_time / total_tasks
            
    def _update_success_rate(self) -> None:
        """Update task success rate."""
        total_tasks = self.total_tasks_processed
        if total_tasks > 0:
            completed_count = len(self.completed_tasks)
            self.task_success_rate = completed_count / total_tasks
        else:
            self.task_success_rate = 1.0
            
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this tab."""
        return {
            'total_tasks_processed': self.total_tasks_processed,
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'total_processing_time': self.total_processing_time,
            'average_task_time': self.average_task_time,
            'task_success_rate': self.task_success_rate,
            'error_count': self.error_count,
            'idle_seconds': self.idle_seconds,
            'age_seconds': self.age_seconds
        }
        
    def should_restart(self, max_errors: int = 5, max_idle_minutes: int = 30) -> bool:
        """
        Determine if tab should be restarted based on error count and idle time.
        """
        # Too many errors
        if self.error_count >= max_errors:
            return True
            
        # Too much idle time (convert minutes to seconds)
        if self.idle_seconds > (max_idle_minutes * 60):
            return True
            
        # In error or crashed state
        if self.is_error_state:
            return True
            
        return False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert tab to dictionary representation."""
        return {
            'tab_id': self.tab_id,
            'session_id': self.session_id,
            'status': self.status.value,
            'created_at': self.created_at,
            'last_activity_at': self.last_activity_at,
            'current_url': self.current_url,
            'current_task': self.current_task.task_id if self.current_task else None,
            'completed_tasks': self.completed_tasks.copy(),
            'failed_tasks': self.failed_tasks.copy(),
            'error_count': self.error_count,
            'last_error': self.last_error.value if self.last_error else None,
            'last_error_message': self.last_error_message,
            'last_error_at': self.last_error_at,
            'total_processing_time': self.total_processing_time,
            'average_task_time': self.average_task_time,
            'task_success_rate': self.task_success_rate,
            'is_available': self.is_available,
            'is_processing': self.is_processing,
            'idle_seconds': self.idle_seconds,
            'age_seconds': self.age_seconds,
            'performance_metrics': self.get_performance_metrics(),
            'metadata': self.metadata.copy()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tab':
        """Create tab from dictionary representation."""
        tab = cls(
            tab_id=data['tab_id'],
            session_id=data['session_id'],
            status=TabStatus(data['status']),
            created_at=data.get('created_at', time.time()),
            last_activity_at=data.get('last_activity_at', time.time()),
            current_url=data.get('current_url'),
            completed_tasks=data.get('completed_tasks', []),
            failed_tasks=data.get('failed_tasks', []),
            error_count=data.get('error_count', 0),
            last_error=TabError(data['last_error']) if data.get('last_error') else None,
            last_error_message=data.get('last_error_message'),
            last_error_at=data.get('last_error_at'),
            total_processing_time=data.get('total_processing_time', 0.0),
            average_task_time=data.get('average_task_time', 0.0),
            task_success_rate=data.get('task_success_rate', 1.0),
            metadata=data.get('metadata', {})
        )
        
        # Restore current task if present
        # Note: In real implementation, this would need proper task restoration
        # For now, we skip current_task restoration as it's complex
        
        return tab
        
    def __str__(self) -> str:
        """String representation of tab."""
        return f"Tab(id={self.tab_id}, status={self.status.value}, tasks={self.total_tasks_processed})"
        
    def __repr__(self) -> str:
        """Detailed representation of tab."""
        return (f"Tab(tab_id='{self.tab_id}', session_id='{self.session_id}', "
                f"status={self.status.value}, current_task={self.current_task.task_id if self.current_task else None}, "
                f"completed={len(self.completed_tasks)}, failed={len(self.failed_tasks)})")