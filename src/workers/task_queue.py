"""
Task Queue Implementation for Parallel PO Processing

This module provides the TaskQueue class and ProcessingTask model for managing
task distribution and retry logic in parallel processing mode.
"""

import uuid
import time
import threading
from datetime import datetime
from enum import Enum
from queue import Queue, PriorityQueue, Empty
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field

from .exceptions import (
    TaskQueueError,
    TaskValidationError,
    QueueCapacityError,
    TaskTimeoutError
)
from ..core.output import maybe_print as print


class TaskStatus(Enum):
    """Status enumeration for processing tasks."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_PENDING = "retry_pending"


@dataclass
class TaskResult:
    """Result data for completed tasks."""
    success: bool
    error_message: Optional[str] = None
    processing_time: float = 0.0
    download_count: int = 0
    file_paths: List[str] = field(default_factory=list)
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingTask:
    """
    Represents a single PO processing task with metadata and progress tracking.
    
    This is the core model for T020 - ProcessingTask with all required attributes
    for task management, retry logic, and status tracking.
    """
    task_id: str
    po_data: Dict[str, Any]
    task_function: Callable
    status: TaskStatus = TaskStatus.PENDING
    assigned_worker: Optional[str] = None
    attempt_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_summary: Optional[TaskResult] = None
    priority: int = 5  # 1=highest, 10=lowest
    
    def __post_init__(self):
        """Initialize task with unique ID if not provided."""
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    def assign_to_worker(self, worker_id: str):
        """Assign task to a worker."""
        self.assigned_worker = worker_id
        self.status = TaskStatus.ASSIGNED
    
    def start_processing(self):
        """Mark task as started processing."""
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.now()
        self.attempt_count += 1
    
    def complete_successfully(self, result: TaskResult):
        """Mark task as completed successfully."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result_summary = result
    
    def mark_failed(self, error_message: str):
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message
    
    def reset_for_retry(self):
        """Reset task for retry attempt."""
        self.status = TaskStatus.RETRY_PENDING
        self.assigned_worker = None
        self.started_at = None
        self.error_message = None
    
    def get_processing_time(self) -> float:
        """Get task processing time in seconds."""
        if not self.started_at:
            return 0.0
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def get_wait_time(self) -> float:
        """Get time task waited in queue before processing."""
        if not self.started_at:
            current_time = datetime.now()
            return (current_time - self.created_at).total_seconds()
        
        return (self.started_at - self.created_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization."""
        return {
            'task_id': self.task_id,
            'po_data': self.po_data,
            'status': self.status.value,
            'assigned_worker': self.assigned_worker,
            'attempt_count': self.attempt_count,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'priority': self.priority,
            'processing_time': self.get_processing_time(),
            'wait_time': self.get_wait_time(),
            'result_summary': self.result_summary.__dict__ if self.result_summary else None
        }


class TaskQueue:
    """
    Thread-safe distribution of PO processing tasks across available workers.
    
    This class implements the TaskQueue API contract for managing task distribution,
    retry logic, and performance monitoring in parallel processing mode.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        task_timeout: float = 300.0,
        enable_priority: bool = True,
        max_size: Optional[int] = None
    ):
        """Initialize task queue with configuration."""
        # Validate parameters
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if retry_delay < 0:
            raise ValueError("retry_delay cannot be negative")
        if task_timeout <= 0:
            raise ValueError("task_timeout must be positive")
        
        # Configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.task_timeout = task_timeout
        self.enable_priority = enable_priority
        self.max_size = max_size or 10000
        
        # Queue management
        if enable_priority:
            self._queue = PriorityQueue(maxsize=self.max_size)
        else:
            self._queue = Queue(maxsize=self.max_size)
        
        # Task tracking
        self.tasks: Dict[str, ProcessingTask] = {}
        self.active_tasks: Dict[str, ProcessingTask] = {}
        self.completed_tasks: List[ProcessingTask] = []
        self.failed_tasks: List[ProcessingTask] = []
        
        # State management
        self.is_paused = False
        self.is_stopped = False
        self.created_at = datetime.now()
        
        # Thread safety
        self._lock = threading.RLock()
        self._stats_lock = threading.Lock()
        
        # Performance tracking
        self.statistics = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'retry_tasks': 0,
            'average_processing_time': 0.0,
            'average_wait_time': 0.0,
            'throughput_per_second': 0.0,
            'peak_queue_size': 0
        }
        
        # Event handlers
        self._event_handlers: Dict[str, Optional[Callable]] = {
            'on_task_complete': None,
            'on_task_failed': None,
            'on_queue_empty': None,
            'on_queue_full': None
        }
    
    def add_task(
        self,
        task_function: Callable,
        po_data: Dict[str, Any],
        priority: int = 5
    ) -> str:
        """Add processing task to queue."""
        with self._lock:
            if self.is_stopped:
                raise TaskQueueError("add_task", "Cannot add task to stopped queue")
            
            # Validate task data
            self._validate_task_data(po_data)
            
            # Check queue capacity
            if self._queue.qsize() >= self.max_size:
                if self._event_handlers['on_queue_full']:
                    self._event_handlers['on_queue_full']()
                raise QueueCapacityError(self._queue.qsize(), self.max_size)
            
            # Create task
            task = ProcessingTask(
                task_id=f"task_{uuid.uuid4().hex[:8]}",
                po_data=po_data,
                task_function=task_function,
                priority=priority
            )
            
            # Add to queue
            if self.enable_priority:
                self._queue.put((priority, task.created_at.timestamp(), task))
            else:
                self._queue.put(task)
            
            # Track task
            self.tasks[task.task_id] = task
            
            # Update statistics
            with self._stats_lock:
                self.statistics['total_tasks'] += 1
                current_size = self._queue.qsize()
                if current_size > self.statistics['peak_queue_size']:
                    self.statistics['peak_queue_size'] = current_size
            
            return task.task_id
    
    def get_next_task(self, worker_id: str) -> Optional[ProcessingTask]:
        """Get next available task for worker.

        Ensures at-most-one active task per PO number by deferring tasks whose
        po_number is already present in active_tasks. Deferred tasks are requeued
        immediately at the same priority.
        """
        with self._lock:
            if self.is_paused or self.is_stopped:
                return None
            
            try:
                # Get task from queue
                if self.enable_priority:
                    priority, timestamp, task = self._queue.get_nowait()
                else:
                    task = self._queue.get_nowait()

                # Guard: avoid assigning duplicate PO concurrently
                po_number = task.po_data.get('po_number') if isinstance(task.po_data, dict) else None
                if po_number:
                    for active in self.active_tasks.values():
                        try:
                            if active.po_data.get('po_number') == po_number:
                                # Requeue and skip assignment for now
                                if self.enable_priority:
                                    # Use the task's own priority and a fresh timestamp
                                    self._queue.put((task.priority, time.time(), task))
                                else:
                                    self._queue.put(task)
                                return None
                        except Exception:
                            # Best-effort guard; continue if missing fields
                            continue

                # Assign to worker
                task.assign_to_worker(worker_id)
                task.start_processing()
                
                # Track active task
                self.active_tasks[task.task_id] = task
                try:
                    # Lightweight debug for assignment tracing
                    pn = task.po_data.get('po_number') if isinstance(task.po_data, dict) else None
                    # Avoid import cycles: print-style log for now
                    print(f"[TaskQueue] assigned task {task.task_id} (PO={pn}) to {worker_id}")
                except Exception:
                    pass
                
                return task
                
            except Empty:
                # Queue is empty
                if self._event_handlers['on_queue_empty']:
                    self._event_handlers['on_queue_empty']()
                return None
    
    def complete_task(
        self,
        task_id: str,
        worker_id: str,
        result: TaskResult
    ) -> None:
        """Mark task as completed with result."""
        with self._lock:
            task = self._get_task_by_id(task_id)
            
            # Validate worker assignment
            if task.assigned_worker != worker_id:
                raise TaskQueueError("complete_task", f"Worker {worker_id} not assigned to task {task_id}", task_id=task_id)
            
            # Complete task
            task.complete_successfully(result)
            
            # Update tracking
            self.active_tasks.pop(task_id, None)
            self.completed_tasks.append(task)
            
            # Update statistics
            with self._stats_lock:
                self.statistics['completed_tasks'] += 1
                self._update_performance_stats(task)
            
            # Trigger event handler
            if self._event_handlers['on_task_complete']:
                self._event_handlers['on_task_complete'](task)
    
    def retry_task(
        self,
        task_id: str,
        error_details: Dict[str, Any]
    ) -> bool:
        """Retry failed task if retries remaining."""
        with self._lock:
            task = self._get_task_by_id(task_id)
            
            # Check retry limit
            if task.attempt_count >= self.max_retries:
                task.mark_failed(error_details.get('error_message', 'Max retries exceeded'))
                self.active_tasks.pop(task_id, None)
                self.failed_tasks.append(task)
                
                # Update statistics
                with self._stats_lock:
                    self.statistics['failed_tasks'] += 1
                
                # Trigger event handler
                if self._event_handlers['on_task_failed']:
                    self._event_handlers['on_task_failed'](task, error_details.get('error_message', ''))
                
                return False
            
            # Reset for retry
            task.reset_for_retry()
            self.active_tasks.pop(task_id, None)
            
            # Calculate retry delay with exponential backoff
            delay = self.retry_delay * (2 ** (task.attempt_count - 1))
            
            # Schedule retry (for simplicity, immediate requeue)
            if self.enable_priority:
                self._queue.put((task.priority, time.time() + delay, task))
            else:
                self._queue.put(task)
            
            # Update statistics
            with self._stats_lock:
                self.statistics['retry_tasks'] += 1
            
            return True
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive queue status and metrics."""
        with self._lock:
            return {
                'total_tasks': self.statistics['total_tasks'],
                'pending_tasks': self._queue.qsize(),
                'processing_tasks': len(self.active_tasks),
                'completed_tasks': len(self.completed_tasks),
                'failed_tasks': len(self.failed_tasks),
                'retry_tasks': self.statistics['retry_tasks'],
                'queue_length': self._queue.qsize(),
                'estimated_completion': self._calculate_estimated_completion(),
                'throughput': self.statistics['throughput_per_second'],
                'is_paused': self.is_paused,
                'is_stopped': self.is_stopped,
                'peak_queue_size': self.statistics['peak_queue_size']
            }
    
    def pause(self) -> None:
        """Pause queue operations."""
        with self._lock:
            self.is_paused = True
    
    def resume(self) -> None:
        """Resume queue operations."""
        with self._lock:
            self.is_paused = False
    
    def stop(self) -> None:
        """Stop queue operations."""
        with self._lock:
            self.is_stopped = True
    
    def clear(self, preserve_processing: bool = True) -> int:
        """Clear pending tasks from queue."""
        with self._lock:
            cleared_count = 0
            
            # Clear the main queue
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    cleared_count += 1
                except Empty:
                    break
            
            # Optionally clear processing tasks
            if not preserve_processing:
                cleared_count += len(self.active_tasks)
                self.active_tasks.clear()
            
            return cleared_count
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[ProcessingTask]:
        """Get all tasks with specified status."""
        with self._lock:
            if status == TaskStatus.PROCESSING:
                return list(self.active_tasks.values())
            elif status == TaskStatus.COMPLETED:
                return self.completed_tasks.copy()
            elif status == TaskStatus.FAILED:
                return self.failed_tasks.copy()
            else:
                # For pending/retry tasks, need to check all tasks
                return [task for task in self.tasks.values() if task.status == status]
    
    def get_tasks_by_worker(self, worker_id: str) -> List[ProcessingTask]:
        """Get all tasks assigned to specific worker."""
        with self._lock:
            return [task for task in self.tasks.values() if task.assigned_worker == worker_id]
    
    def find_task(
        self,
        po_number: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Optional[ProcessingTask]:
        """Find task by PO number or task ID."""
        if task_id:
            return self.tasks.get(task_id)
        
        if po_number:
            for task in self.tasks.values():
                if task.po_data.get('po_number') == po_number:
                    return task
        
        return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        with self._stats_lock:
            return self.statistics.copy()
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors encountered."""
        with self._lock:
            error_counts = {}
            unique_errors = set()
            
            for task in self.failed_tasks:
                if task.error_message:
                    unique_errors.add(task.error_message)
                    error_counts[task.error_message] = error_counts.get(task.error_message, 0) + 1
            
            most_common = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            retry_success_rate = 0.0
            if self.statistics['retry_tasks'] > 0:
                successful_retries = self.statistics['retry_tasks'] - len(self.failed_tasks)
                retry_success_rate = successful_retries / self.statistics['retry_tasks']
            
            return {
                'total_errors': len(self.failed_tasks),
                'unique_error_types': len(unique_errors),
                'most_common_errors': [{'error': error, 'count': count} for error, count in most_common],
                'retry_success_rate': retry_success_rate
            }
    
    def set_event_handlers(
        self,
        on_task_complete: Optional[Callable[[ProcessingTask], None]] = None,
        on_task_failed: Optional[Callable[[ProcessingTask, str], None]] = None,
        on_queue_empty: Optional[Callable[[], None]] = None,
        on_queue_full: Optional[Callable[[], None]] = None
    ) -> None:
        """Set event handlers for queue operations."""
        if on_task_complete:
            self._event_handlers['on_task_complete'] = on_task_complete
        if on_task_failed:
            self._event_handlers['on_task_failed'] = on_task_failed
        if on_queue_empty:
            self._event_handlers['on_queue_empty'] = on_queue_empty
        if on_queue_full:
            self._event_handlers['on_queue_full'] = on_queue_full
    
    def get_pending_count(self) -> int:
        """Get number of pending tasks."""
        return self._queue.qsize()
    
    def get_active_count(self) -> int:
        """Get number of active tasks."""
        return len(self.active_tasks)
    
    def get_completed_count(self) -> int:
        """Get number of completed tasks."""
        return len(self.completed_tasks)
    
    def get_failed_count(self) -> int:
        """Get number of failed tasks."""
        return len(self.failed_tasks)
    
    # Private helper methods
    
    def _validate_task_data(self, po_data: Dict[str, Any]):
        """Validate PO data for task creation."""
        required_fields = ['po_number']  # Only po_number is truly required
        
        for field in required_fields:
            if field not in po_data:
                raise TaskValidationError(field, f"Missing required field: {field}")
            
            if not po_data[field]:
                raise TaskValidationError(field, f"Empty value for required field: {field}")
        
        # Optional fields with warnings
        optional_fields = ['supplier', 'url']
        for field in optional_fields:
            if field not in po_data or not po_data[field]:
                # Log warning but don't fail validation
                try:
                    # Removed verbose warning messages to reduce terminal output clutter
                    # print(f"[TaskQueue] Warning: {field} is empty for PO {po_data.get('po_number', 'unknown')}")
                    pass
                except Exception:
                    pass
    
    def _get_task_by_id(self, task_id: str) -> ProcessingTask:
        """Get task by ID with error handling."""
        task = self.tasks.get(task_id)
        if not task:
            raise TaskQueueError("_get_task_by_id", f"Task not found: {task_id}", task_id=task_id)
        return task
    
    def _update_performance_stats(self, task: ProcessingTask):
        """Update performance statistics with completed task."""
        processing_time = task.get_processing_time()
        wait_time = task.get_wait_time()
        
        # Update average processing time
        completed_count = self.statistics['completed_tasks']
        if completed_count == 1:
            self.statistics['average_processing_time'] = processing_time
            self.statistics['average_wait_time'] = wait_time
        else:
            # Incremental average calculation
            old_avg_processing = self.statistics['average_processing_time']
            old_avg_wait = self.statistics['average_wait_time']
            
            self.statistics['average_processing_time'] = (
                (old_avg_processing * (completed_count - 1) + processing_time) / completed_count
            )
            self.statistics['average_wait_time'] = (
                (old_avg_wait * (completed_count - 1) + wait_time) / completed_count
            )
        
        # Update throughput
        total_time = (datetime.now() - self.created_at).total_seconds()
        if total_time > 0:
            self.statistics['throughput_per_second'] = completed_count / total_time
    
    def _calculate_estimated_completion(self) -> Optional[float]:
        """Calculate estimated time to complete all pending tasks."""
        pending_count = self._queue.qsize()
        if pending_count == 0:
            return 0.0
        
        avg_processing_time = self.statistics['average_processing_time']
        if avg_processing_time <= 0:
            return None
        
        # Estimate based on average processing time
        # This is a simple estimation; could be improved with worker count consideration
        return pending_count * avg_processing_time
