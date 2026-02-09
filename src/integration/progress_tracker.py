"""
Progress tracking and status reporting for worker pool operations.

This module provides the ProgressTracker class for real-time monitoring
of processing progress with support for:
- Real-time progress updates
- ETA calculations  
- Status event broadcasting
- Progress persistence
- Monitoring hooks
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import deque
import structlog

from ..workers.models import POTask, TaskStatus

logger = structlog.get_logger(__name__)


class ProgressEventType(Enum):
    """Types of progress events."""
    TASK_SUBMITTED = "task_submitted"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_RETRY = "task_retry"
    WORKER_STARTED = "worker_started"
    WORKER_STOPPED = "worker_stopped"
    BATCH_COMPLETED = "batch_completed"
    PROCESSING_COMPLETE = "processing_complete"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class ProgressEvent:
    """Individual progress event."""
    event_type: ProgressEventType
    timestamp: datetime
    task_id: Optional[str]
    worker_id: Optional[str]
    message: str
    metadata: Dict[str, Any]


@dataclass
class ProgressSnapshot:
    """Point-in-time progress snapshot."""
    timestamp: datetime
    total_tasks: int
    submitted_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    success_rate_percent: float
    active_workers: int
    estimated_time_remaining_seconds: Optional[float]
    current_processing_rate_per_second: float
    average_processing_time_seconds: float


class ProgressTracker:
    """
    Real-time progress tracking for worker pool operations.
    
    Provides comprehensive progress monitoring with event broadcasting,
    ETA calculations, and status reporting capabilities.
    """
    
    def __init__(self, max_event_history: int = 1000):
        """
        Initialize progress tracker.
        
        Args:
            max_event_history: Maximum number of events to keep in memory
        """
        self.max_event_history = max_event_history
        
        # Task tracking
        self.tasks: Dict[str, POTask] = {}  # task_id -> POTask
        self.task_timestamps: Dict[str, Dict[str, datetime]] = {}  # task_id -> event timestamps
        
        # Worker tracking
        self.active_workers: Dict[str, datetime] = {}  # worker_id -> start_time
        
        # Event tracking
        self.events: deque[ProgressEvent] = deque(maxlen=max_event_history)
        self.event_listeners: List[Callable[[ProgressEvent], None]] = []
        
        # Progress calculation data
        self.start_time = datetime.now()
        self.last_snapshot_time = self.start_time
        self.completed_in_last_window: List[datetime] = []
        self.processing_rate_window_seconds = 300.0  # Calculate rate over 5 minutes
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Persistence
        self.save_file: Optional[Path] = None
        self.auto_save_interval_seconds = 30.0
        self.last_save_time = self.start_time
        
        logger.debug("ProgressTracker initialized", max_event_history=max_event_history)
    
    def add_event_listener(self, listener: Callable[[ProgressEvent], None]) -> None:
        """
        Add event listener for progress events.
        
        Args:
            listener: Function to call when events occur
        """
        with self._lock:
            self.event_listeners.append(listener)
        
        logger.debug("Event listener added", total_listeners=len(self.event_listeners))
    
    def remove_event_listener(self, listener: Callable[[ProgressEvent], None]) -> None:
        """
        Remove event listener.
        
        Args:
            listener: Function to remove from listeners
        """
        with self._lock:
            if listener in self.event_listeners:
                self.event_listeners.remove(listener)
        
        logger.debug("Event listener removed", total_listeners=len(self.event_listeners))
    
    def enable_auto_save(self, file_path: Union[str, Path], 
                        interval_seconds: float = 30.0) -> None:
        """
        Enable automatic progress saving to file.
        
        Args:
            file_path: File to save progress to
            interval_seconds: Save interval in seconds
        """
        self.save_file = Path(file_path)
        self.auto_save_interval_seconds = interval_seconds
        
        logger.info("Auto-save enabled", file=str(self.save_file), 
                   interval=interval_seconds)
    
    def disable_auto_save(self) -> None:
        """Disable automatic progress saving."""
        self.save_file = None
        logger.info("Auto-save disabled")
    
    def track_task_submission(self, task: POTask) -> None:
        """
        Track task submission.
        
        Args:
            task: POTask that was submitted
        """
        with self._lock:
            self.tasks[task.task_id] = task
            self.task_timestamps[task.task_id] = {'submitted': datetime.now()}
            
            self._emit_event(
                ProgressEventType.TASK_SUBMITTED,
                task_id=task.task_id,
                message=f"Task submitted: {task.po_number}",
                metadata={'po_number': task.po_number, 'priority': task.priority}
            )
            
            self._check_auto_save()
    
    def track_task_started(self, task: POTask, worker_id: str) -> None:
        """
        Track task start.
        
        Args:
            task: POTask that started
            worker_id: Worker ID processing the task
        """
        with self._lock:
            if task.task_id in self.task_timestamps:
                self.task_timestamps[task.task_id]['started'] = datetime.now()
            
            self._emit_event(
                ProgressEventType.TASK_STARTED,
                task_id=task.task_id,
                worker_id=worker_id,
                message=f"Task started: {task.po_number}",
                metadata={'po_number': task.po_number, 'worker_id': worker_id}
            )
    
    def track_task_completed(self, task: POTask, worker_id: Optional[str] = None) -> None:
        """
        Track task completion.
        
        Args:
            task: POTask that completed
            worker_id: Worker ID that processed the task
        """
        with self._lock:
            self.tasks[task.task_id] = task
            
            completion_time = datetime.now()
            if task.task_id in self.task_timestamps:
                self.task_timestamps[task.task_id]['completed'] = completion_time
            
            # Track completion for rate calculation
            self.completed_in_last_window.append(completion_time)
            self._clean_rate_window()
            
            event_type = (ProgressEventType.TASK_COMPLETED 
                         if task.status == TaskStatus.COMPLETED 
                         else ProgressEventType.TASK_FAILED)
            
            self._emit_event(
                event_type,
                task_id=task.task_id,
                worker_id=worker_id,
                message=f"Task {task.status.value.lower()}: {task.po_number}",
                metadata={
                    'po_number': task.po_number,
                    'status': task.status.value,
                    'worker_id': worker_id,
                    'processing_time_seconds': task.get_processing_time(),
                    'retry_count': task.retry_count
                }
            )
            
            self._check_auto_save()
    
    def track_task_cancelled(self, task: POTask) -> None:
        """
        Track task cancellation.
        
        Args:
            task: POTask that was cancelled
        """
        with self._lock:
            self.tasks[task.task_id] = task
            
            if task.task_id in self.task_timestamps:
                self.task_timestamps[task.task_id]['cancelled'] = datetime.now()
            
            self._emit_event(
                ProgressEventType.TASK_CANCELLED,
                task_id=task.task_id,
                message=f"Task cancelled: {task.po_number}",
                metadata={'po_number': task.po_number}
            )
    
    def track_task_retry(self, task: POTask, worker_id: Optional[str] = None) -> None:
        """
        Track task retry.
        
        Args:
            task: POTask being retried
            worker_id: Worker ID handling the retry
        """
        with self._lock:
            self.tasks[task.task_id] = task
            
            self._emit_event(
                ProgressEventType.TASK_RETRY,
                task_id=task.task_id,
                worker_id=worker_id,
                message=f"Task retry #{task.retry_count}: {task.po_number}",
                metadata={
                    'po_number': task.po_number,
                    'retry_count': task.retry_count,
                    'worker_id': worker_id
                }
            )
    
    def track_worker_started(self, worker_id: str) -> None:
        """
        Track worker start.
        
        Args:
            worker_id: Worker ID that started
        """
        with self._lock:
            self.active_workers[worker_id] = datetime.now()
            
            self._emit_event(
                ProgressEventType.WORKER_STARTED,
                worker_id=worker_id,
                message=f"Worker started: {worker_id}",
                metadata={'worker_id': worker_id}
            )
    
    def track_worker_stopped(self, worker_id: str) -> None:
        """
        Track worker stop.
        
        Args:
            worker_id: Worker ID that stopped
        """
        with self._lock:
            if worker_id in self.active_workers:
                start_time = self.active_workers.pop(worker_id)
                uptime = (datetime.now() - start_time).total_seconds()
            else:
                uptime = None
            
            self._emit_event(
                ProgressEventType.WORKER_STOPPED,
                worker_id=worker_id,
                message=f"Worker stopped: {worker_id}",
                metadata={
                    'worker_id': worker_id,
                    'uptime_seconds': uptime
                }
            )
    
    def track_batch_completed(self, batch_size: int, batch_id: Optional[str] = None) -> None:
        """
        Track batch completion.
        
        Args:
            batch_size: Number of tasks in completed batch
            batch_id: Optional batch identifier
        """
        with self._lock:
            self._emit_event(
                ProgressEventType.BATCH_COMPLETED,
                message=f"Batch completed: {batch_size} tasks",
                metadata={'batch_size': batch_size, 'batch_id': batch_id}
            )
    
    def track_error(self, error_message: str, task_id: Optional[str] = None,
                   worker_id: Optional[str] = None) -> None:
        """
        Track error occurrence.
        
        Args:
            error_message: Error description
            task_id: Optional task ID related to error
            worker_id: Optional worker ID related to error
        """
        with self._lock:
            self._emit_event(
                ProgressEventType.ERROR_OCCURRED,
                task_id=task_id,
                worker_id=worker_id,
                message=f"Error occurred: {error_message}",
                metadata={
                    'error_message': error_message,
                    'task_id': task_id,
                    'worker_id': worker_id
                }
            )
    
    def mark_processing_complete(self) -> None:
        """Mark overall processing as complete."""
        with self._lock:
            self._emit_event(
                ProgressEventType.PROCESSING_COMPLETE,
                message="Processing completed",
                metadata={'total_duration_seconds': self.get_total_duration().total_seconds()}
            )
            
            # Final save if auto-save is enabled
            if self.save_file:
                self.save_progress(self.save_file)
    
    def get_snapshot(self) -> ProgressSnapshot:
        """
        Get current progress snapshot.
        
        Returns:
            ProgressSnapshot with current status
        """
        with self._lock:
            # Count tasks by status
            total_tasks = len(self.tasks)
            submitted_tasks = total_tasks
            
            status_counts = {status: 0 for status in TaskStatus}
            for task in self.tasks.values():
                status_counts[task.status] += 1
            
            pending_tasks = status_counts[TaskStatus.PENDING]
            in_progress_tasks = status_counts[TaskStatus.PROCESSING] + status_counts[TaskStatus.ASSIGNED]
            completed_tasks = status_counts[TaskStatus.COMPLETED]
            failed_tasks = status_counts[TaskStatus.FAILED]
            cancelled_tasks = status_counts[TaskStatus.CANCELLED]
            
            # Calculate success rate
            finished_tasks = completed_tasks + failed_tasks
            success_rate = (completed_tasks / finished_tasks * 100) if finished_tasks > 0 else 0.0
            
            # Calculate processing rate and ETA
            current_rate = self._calculate_processing_rate()
            avg_processing_time = self._calculate_average_processing_time()
            eta = self._calculate_eta(pending_tasks + in_progress_tasks, current_rate)
            
            return ProgressSnapshot(
                timestamp=datetime.now(),
                total_tasks=total_tasks,
                submitted_tasks=submitted_tasks,
                pending_tasks=pending_tasks,
                in_progress_tasks=in_progress_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                cancelled_tasks=cancelled_tasks,
                success_rate_percent=round(success_rate, 2),
                active_workers=len(self.active_workers),
                estimated_time_remaining_seconds=eta,
                current_processing_rate_per_second=current_rate,
                average_processing_time_seconds=avg_processing_time
            )
    
    def get_recent_events(self, limit: int = 50) -> List[ProgressEvent]:
        """
        Get recent progress events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent ProgressEvent instances
        """
        with self._lock:
            events_list = list(self.events)
            return events_list[-limit:] if limit < len(events_list) else events_list
    
    def get_events_by_type(self, event_type: ProgressEventType,
                          limit: Optional[int] = None) -> List[ProgressEvent]:
        """
        Get events filtered by type.
        
        Args:
            event_type: Type of events to retrieve
            limit: Maximum number of events to return
            
        Returns:
            List of filtered ProgressEvent instances
        """
        with self._lock:
            filtered_events = [event for event in self.events 
                             if event.event_type == event_type]
            
            if limit and len(filtered_events) > limit:
                return filtered_events[-limit:]
            
            return filtered_events
    
    def get_task_history(self, task_id: str) -> Dict[str, Any]:
        """
        Get processing history for specific task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dictionary with task history
        """
        with self._lock:
            task = self.tasks.get(task_id)
            timestamps = self.task_timestamps.get(task_id, {})
            
            # Get events for this task
            task_events = [event for event in self.events if event.task_id == task_id]
            
            return {
                'task': asdict(task) if task else None,
                'timestamps': {k: v.isoformat() for k, v in timestamps.items()},
                'events': [asdict(event) for event in task_events],
                'processing_duration_seconds': (
                    (timestamps.get('completed', datetime.now()) - 
                     timestamps['started']).total_seconds()
                    if 'started' in timestamps else None
                )
            }
    
    def get_worker_activity(self, worker_id: str) -> Dict[str, Any]:
        """
        Get activity summary for specific worker.
        
        Args:
            worker_id: Worker identifier
            
        Returns:
            Dictionary with worker activity
        """
        with self._lock:
            # Get events for this worker
            worker_events = [event for event in self.events if event.worker_id == worker_id]
            
            # Count tasks processed by this worker
            tasks_processed = len([task for task in self.tasks.values() 
                                 if task.assigned_worker_id == worker_id])
            
            # Calculate uptime
            start_time = self.active_workers.get(worker_id)
            uptime_seconds = (
                (datetime.now() - start_time).total_seconds()
                if start_time else None
            )
            
            return {
                'worker_id': worker_id,
                'is_active': worker_id in self.active_workers,
                'start_time': start_time.isoformat() if start_time else None,
                'uptime_seconds': uptime_seconds,
                'tasks_processed': tasks_processed,
                'event_count': len(worker_events),
                'recent_events': [asdict(event) for event in worker_events[-10:]]
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        with self._lock:
            snapshot = self.get_snapshot()
            
            # Calculate throughput over different periods
            now = datetime.now()
            throughput_1min = self._calculate_throughput_since(now - timedelta(minutes=1))
            throughput_5min = self._calculate_throughput_since(now - timedelta(minutes=5))
            throughput_15min = self._calculate_throughput_since(now - timedelta(minutes=15))
            
            # Worker efficiency
            worker_efficiency = self._calculate_worker_efficiency()
            
            return {
                'current_snapshot': asdict(snapshot),
                'throughput': {
                    'last_1_minute': throughput_1min,
                    'last_1_minute': throughput_1min,
                    'last_5_minutes': throughput_5min,
                    'last_15_minutes': throughput_15min,
                    'dynamic_rate_per_minute': self._calculate_dynamic_throughput() * 60
                },
                'worker_efficiency': worker_efficiency,
                'total_processing_time_seconds': self.get_total_duration().total_seconds(),
                'events_recorded': len(self.events),
                'memory_usage': {
                    'tracked_tasks': len(self.tasks),
                    'active_workers': len(self.active_workers),
                    'event_history_size': len(self.events)
                }
            }
    
    def save_progress(self, file_path: Union[str, Path]) -> None:
        """
        Save current progress to file.
        
        Args:
            file_path: File to save progress to
        """
        file_path = Path(file_path)
        
        with self._lock:
            snapshot = self.get_snapshot()
            recent_events = self.get_recent_events(100)
            
            save_data = {
                'save_timestamp': datetime.now().isoformat(),
                'tracker_start_time': self.start_time.isoformat(),
                'snapshot': asdict(snapshot),
                'recent_events': [asdict(event) for event in recent_events],
                'active_workers': {
                    worker_id: start_time.isoformat()
                    for worker_id, start_time in self.active_workers.items()
                },
                'total_tasks_tracked': len(self.tasks)
            }
            
            # Serialize datetime objects
            save_data = self._serialize_for_json(save_data)
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)
                
                self.last_save_time = datetime.now()
                logger.debug("Progress saved", file=str(file_path))
                
            except Exception as e:
                logger.error("Failed to save progress", 
                           file=str(file_path), error=str(e))
                raise
    
    def get_total_duration(self) -> timedelta:
        """Get total tracking duration."""
        return datetime.now() - self.start_time
    
    def _emit_event(self, event_type: ProgressEventType, 
                   task_id: Optional[str] = None,
                   worker_id: Optional[str] = None,
                   message: str = "",
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """Emit progress event to listeners."""
        event = ProgressEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            task_id=task_id,
            worker_id=worker_id,
            message=message,
            metadata=metadata or {}
        )
        
        self.events.append(event)
        
        # Notify listeners (don't hold lock during callbacks)
        listeners = self.event_listeners.copy()
        
        # Release lock before calling listeners to avoid deadlocks
        # Listeners should not call back into tracker methods
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.warning("Event listener failed", error=str(e))
    
    def _clean_rate_window(self) -> None:
        """Clean old completions from rate calculation window."""
        cutoff_time = datetime.now() - timedelta(seconds=self.processing_rate_window_seconds)
        self.completed_in_last_window = [
            completion_time for completion_time in self.completed_in_last_window
            if completion_time > cutoff_time
        ]
    
    def _calculate_processing_rate(self) -> float:
        """Calculate current processing rate (tasks per second)."""
        self._clean_rate_window()
        
        if not self.completed_in_last_window:
            return 0.0
        
        return len(self.completed_in_last_window) / self.processing_rate_window_seconds
    
    def _calculate_average_processing_time(self) -> float:
        """Calculate average processing time for completed tasks."""
        processing_times = []
        
        for task in self.tasks.values():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                processing_time = task.get_processing_time()
                if processing_time:
                    processing_times.append(processing_time)
        
        return sum(processing_times) / len(processing_times) if processing_times else 0.0
    
    def _calculate_eta(self, remaining_tasks: int, current_rate: float) -> Optional[float]:
        """Calculate estimated time remaining."""
        if remaining_tasks <= 0 or current_rate <= 0:
            return None
        
        return remaining_tasks / current_rate
    
    def _calculate_throughput_since(self, since_time: datetime) -> float:
        """Calculate throughput since specific time."""
        completed_since = [
            completion_time for completion_time in self.completed_in_last_window
            if completion_time >= since_time
        ]
        
        duration_seconds = (datetime.now() - since_time).total_seconds()
        return len(completed_since) / duration_seconds if duration_seconds > 0 else 0.0

    def _calculate_dynamic_throughput(self) -> float:
        """
        Calculate throughput using a dynamic window based on runtime.
        - First 5 minutes: use 10-second window (fast feedback)
        - After 5 minutes: use 5-minute window (stable trend)
        """
        now = datetime.now()
        runtime_seconds = (now - self.start_time).total_seconds()
        
        if runtime_seconds < 300:  # Less than 5 minutes
            window_start = now - timedelta(seconds=10)
        else:
            window_start = now - timedelta(minutes=5)
            
        return self._calculate_throughput_since(window_start)
    
    def _calculate_worker_efficiency(self) -> Dict[str, Any]:
        """Calculate worker efficiency metrics."""
        worker_stats = {}
        
        for worker_id in self.active_workers:
            worker_tasks = [task for task in self.tasks.values() 
                          if task.assigned_worker_id == worker_id]
            
            if worker_tasks:
                completed = sum(1 for task in worker_tasks 
                              if task.status == TaskStatus.COMPLETED)
                total = len(worker_tasks)
                
                worker_stats[worker_id] = {
                    'tasks_processed': total,
                    'tasks_completed': completed,
                    'success_rate': (completed / total * 100) if total > 0 else 0,
                    'efficiency_score': self._calculate_efficiency_score(worker_tasks)
                }
        
        return worker_stats
    
    def _calculate_efficiency_score(self, tasks: List[POTask]) -> float:
        """Calculate efficiency score for a list of tasks."""
        if not tasks:
            return 0.0
        
        # Simple efficiency score based on success rate and average processing time
        completed_tasks = [task for task in tasks if task.status == TaskStatus.COMPLETED]
        success_rate = len(completed_tasks) / len(tasks)
        
        if completed_tasks:
            processing_times = [task.get_processing_time() or 0 for task in completed_tasks]
            avg_time = sum(processing_times) / len(processing_times)
            # Lower processing time is better (normalized)
            time_efficiency = max(0, 1 - (avg_time / 300))  # 5 minutes as baseline
        else:
            time_efficiency = 0
        
        return (success_rate * 0.7 + time_efficiency * 0.3) * 100
    
    def _check_auto_save(self) -> None:
        """Check if auto-save should be triggered."""
        if (self.save_file and 
            (datetime.now() - self.last_save_time).total_seconds() >= self.auto_save_interval_seconds):
            try:
                self.save_progress(self.save_file)
            except Exception as e:
                logger.warning("Auto-save failed", error=str(e))
    
    def _serialize_for_json(self, data: Any) -> Any:
        """Serialize data for JSON export."""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, ProgressEventType):
            return data.value
        elif isinstance(data, dict):
            return {key: self._serialize_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_json(item) for item in data]
        else:
            return data
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get tracker statistics.
        
        Returns:
            Dictionary containing tracker statistics
        """
        with self._lock:
            return {
                'total_tasks_tracked': len(self.tasks),
                'active_workers': len(self.active_workers),
                'events_recorded': len(self.events),
                'tracking_duration_seconds': self.get_total_duration().total_seconds(),
                'auto_save_enabled': self.save_file is not None,
                'event_listeners': len(self.event_listeners),
                'last_save_time': self.last_save_time.isoformat(),
                'processing_rate_per_second': self._calculate_processing_rate()
            }