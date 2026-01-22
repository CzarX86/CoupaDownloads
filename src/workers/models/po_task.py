"""
POTask model with priority and retry logic.

This module provides the POTask data model with support for:
- Purchase order task management
- Priority-based processing
- Retry logic and failure handling
- Metadata tracking
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class TaskStatus(Enum):
    """Task processing status enumeration."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class POTask:
    """
    POTask model with priority and retry logic.
    
    Represents a purchase order processing task with comprehensive
    tracking, prioritization, and retry capabilities.
    """
    
    # Core identification
    po_number: str = ""
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    
    # Processing control
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    
    # Timing
    created_time: datetime = field(default_factory=datetime.now)
    assigned_time: Optional[datetime] = None
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    
    # Retry logic
    retry_count: int = 0
    max_retries: int = 3
    timeout_override: Optional[float] = None  # Task-specific timeout
    
    # Worker assignment
    assigned_worker_id: Optional[str] = None
    
    # Error tracking
    error_message: Optional[str] = None
    error_history: list = field(default_factory=list)
    
    # Processing results
    result_data: Dict[str, Any] = field(default_factory=dict)
    downloaded_files: list = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate task configuration after initialization."""
        if not self.po_number:
            raise ValueError("PO number cannot be empty")
        
        if not self.task_id:
            raise ValueError("Task ID cannot be empty")
        
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        
        if isinstance(self.priority, int):
            self.priority = TaskPriority(self.priority)
    
    def assign_to_worker(self, worker_id: str):
        """Assign task to specified worker."""
        if self.status != TaskStatus.PENDING:
            raise ValueError(f"Cannot assign task in status: {self.status}")
        
        self.assigned_worker_id = worker_id
        self.assigned_time = datetime.now()
        self.status = TaskStatus.ASSIGNED
    
    def start_processing(self):
        """Mark task as started processing."""
        if self.status != TaskStatus.ASSIGNED:
            raise ValueError(f"Cannot start processing task in status: {self.status}")
        
        self.started_time = datetime.now()
        self.status = TaskStatus.PROCESSING
    
    def complete_successfully(self, result_data: Optional[Dict[str, Any]] = None, 
                            downloaded_files: Optional[list] = None):
        """Mark task as completed successfully."""
        if self.status != TaskStatus.PROCESSING:
            raise ValueError(f"Cannot complete task in status: {self.status}")
        
        self.completed_time = datetime.now()
        self.status = TaskStatus.COMPLETED
        
        if result_data:
            self.result_data.update(result_data)
        
        if downloaded_files:
            self.downloaded_files.extend(downloaded_files)
    
    def fail_with_error(self, error_message: str, allow_retry: bool = True):
        """Mark task as failed with error message."""
        self.error_message = error_message
        self.error_history.append({
            'timestamp': datetime.now().isoformat(),
            'message': error_message,
            'retry_count': self.retry_count
        })
        
        if allow_retry and self.can_retry():
            self.status = TaskStatus.RETRYING
            self.retry_count += 1
            # Reset assignment for retry
            self.assigned_worker_id = None
            self.assigned_time = None
            self.started_time = None
        else:
            self.status = TaskStatus.FAILED
            self.completed_time = datetime.now()
    
    def cancel(self, reason: str = "Cancelled by user"):
        """Cancel task processing."""
        self.status = TaskStatus.CANCELLED
        self.completed_time = datetime.now()
        self.error_message = reason
    
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return (self.retry_count < self.max_retries and 
                self.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED])
    
    def reset_for_retry(self):
        """Reset task state for retry attempt."""
        if not self.can_retry():
            raise ValueError("Task cannot be retried")
        
        self.status = TaskStatus.PENDING
        self.assigned_worker_id = None
        self.assigned_time = None
        self.started_time = None
        self.error_message = None
    
    def get_processing_time(self) -> Optional[float]:
        """Get total processing time in seconds."""
        if not self.started_time:
            return None
        
        end_time = self.completed_time or datetime.now()
        return (end_time - self.started_time).total_seconds()
    
    def get_wait_time(self) -> Optional[float]:
        """Get time waiting for assignment in seconds."""
        if not self.assigned_time:
            return None
        
        return (self.assigned_time - self.created_time).total_seconds()
    
    def get_priority_score(self) -> int:
        """Get numeric priority score for sorting."""
        # Higher number = higher priority
        # Also consider age of task for fair processing
        age_bonus = min(5, int((datetime.now() - self.created_time).total_seconds() / 3600))  # Hours
        return self.priority.value * 10 + age_bonus
    
    def is_completed(self) -> bool:
        """Check if task is in a completed state."""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    
    def is_active(self) -> bool:
        """Check if task is actively being processed."""
        return self.status in [TaskStatus.ASSIGNED, TaskStatus.PROCESSING]
    
    def to_dict(self) -> dict:
        """Convert task to dictionary representation."""
        return {
            'po_number': self.po_number,
            'task_id': self.task_id,
            'priority': self.priority.value,
            'status': self.status.value,
            'created_time': self.created_time.isoformat(),
            'assigned_time': self.assigned_time.isoformat() if self.assigned_time else None,
            'started_time': self.started_time.isoformat() if self.started_time else None,
            'completed_time': self.completed_time.isoformat() if self.completed_time else None,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'timeout_override': self.timeout_override,
            'assigned_worker_id': self.assigned_worker_id,
            'error_message': self.error_message,
            'error_history': self.error_history.copy(),
            'result_data': self.result_data.copy(),
            'downloaded_files': self.downloaded_files.copy(),
            'metadata': self.metadata.copy(),
            'processing_time_seconds': self.get_processing_time(),
            'wait_time_seconds': self.get_wait_time(),
            'priority_score': self.get_priority_score()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'POTask':
        """Create task from dictionary representation."""
        # Convert enums
        if 'priority' in data and isinstance(data['priority'], int):
            data['priority'] = TaskPriority(data['priority'])
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TaskStatus(data['status'])
        
        # Convert datetime strings
        datetime_fields = ['created_time', 'assigned_time', 'started_time', 'completed_time']
        for field in datetime_fields:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        
        # Remove computed fields
        computed_fields = ['processing_time_seconds', 'wait_time_seconds', 'priority_score']
        for field in computed_fields:
            data.pop(field, None)
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of task."""
        return f"POTask({self.po_number}, {self.status.value}, priority={self.priority.value})"
    
    def __repr__(self) -> str:
        """Detailed representation of task."""
        return (f"POTask(po_number='{self.po_number}', status={self.status}, "
                f"priority={self.priority}, retry_count={self.retry_count})")
    
    def __lt__(self, other):
        """Less than comparison for priority queue sorting."""
        if not isinstance(other, POTask):
            return NotImplemented
        # Higher priority score should come first (reverse order)
        return self.get_priority_score() > other.get_priority_score()
