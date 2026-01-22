# TaskQueue API Contract

**Module**: `EXPERIMENTAL.workers.task_queue`  
**Class**: `TaskQueue`

## Constructor

```python
def __init__(
    self,
    max_retries: int = 3,
    retry_delay: float = 5.0,
    task_timeout: float = 300.0,
    enable_priority: bool = True
) -> None:
    """Initialize task queue for parallel PO processing.
    
    Args:
        max_retries: Maximum retry attempts per task
        retry_delay: Base delay between retries (seconds)
        task_timeout: Maximum execution time per task (seconds)
        enable_priority: Whether to support task prioritization
        
    Raises:
        ValueError: If timeout or retry values are invalid
    """
```

## Core Queue Operations

### add_task
```python
def add_task(
    self,
    task: ProcessingTask,
    priority: int = 5
) -> str:
    """Add processing task to queue.
    
    Args:
        task: ProcessingTask instance with PO data and configuration
        priority: Task priority (1=highest, 10=lowest, default=5)
        
    Returns:
        str: Unique task identifier
        
    Raises:
        ValueError: If task data is invalid or incomplete
        QueueFullError: If queue at maximum capacity
        
    Behavior:
        - Validates task data completeness
        - Assigns unique task identifier
        - Inserts in priority order (if priority enabled)
        - Updates queue metrics and status
    """
```

### get_next_task
```python
def get_next_task(self, worker_id: str) -> Optional[ProcessingTask]:
    """Get next available task for worker.
    
    Args:
        worker_id: Identifier of requesting worker
        
    Returns:
        Optional[ProcessingTask]: Next task or None if queue empty
        
    Behavior:
        - Returns highest priority task (if priority enabled)
        - Marks task as assigned to worker
        - Updates task status to PROCESSING
        - Records assignment timestamp
        - Thread-safe operation with proper locking
    """
```

### complete_task
```python
def complete_task(
    self,
    task_id: str,
    worker_id: str,
    result: TaskResult
) -> None:
    """Mark task as completed with result.
    
    Args:
        task_id: Unique task identifier
        worker_id: Identifier of completing worker
        result: Task completion result and details
        
    Raises:
        TaskNotFoundError: If task_id doesn't exist
        WorkerMismatchError: If worker_id doesn't match assigned worker
        
    Side Effects:
        - Updates task status to COMPLETED or FAILED
        - Records completion timestamp and duration
        - Updates queue statistics
        - Triggers completion callbacks if configured
    """
```

### retry_task
```python
def retry_task(
    self,
    task_id: str,
    error_details: Dict[str, Any]
) -> bool:
    """Retry failed task if retries remaining.
    
    Args:
        task_id: Unique task identifier
        error_details: Details about the failure
        
    Returns:
        bool: True if task queued for retry, False if max retries exceeded
        
    Behavior:
        - Checks retry count against max_retries
        - Calculates retry delay with exponential backoff
        - Updates task retry count and error history
        - Re-queues task with appropriate delay
        - Logs retry decision and timing
    """
```

## Queue Management

### get_queue_status
```python
def get_queue_status(self) -> Dict[str, Any]:
    """Get comprehensive queue status and metrics.
    
    Returns:
        Dict[str, Any]: Queue status with keys:
            - total_tasks: int total tasks ever added
            - pending_tasks: int tasks waiting to be processed
            - processing_tasks: int tasks currently being processed
            - completed_tasks: int successfully completed tasks
            - failed_tasks: int tasks that failed all retries
            - retry_tasks: int tasks waiting for retry
            - queue_length: int current tasks in queue
            - estimated_completion: Optional[float] estimated seconds to complete all
            - throughput: float tasks completed per second (recent average)
    """
```

### pause_queue
```python
def pause_queue(self) -> None:
    """Pause queue operations (stop dispatching new tasks).
    
    Behavior:
        - Prevents get_next_task from returning new tasks
        - Allows currently processing tasks to complete
        - Maintains queue state for resumption
        - Updates queue status to PAUSED
    """
```

### resume_queue
```python
def resume_queue(self) -> None:
    """Resume queue operations after pause.
    
    Behavior:
        - Re-enables task dispatching
        - Updates queue status to ACTIVE
        - Logs resumption with queue statistics
    """
```

### clear_queue
```python
def clear_queue(self, preserve_processing: bool = True) -> int:
    """Clear pending tasks from queue.
    
    Args:
        preserve_processing: Whether to keep currently processing tasks
        
    Returns:
        int: Number of tasks removed from queue
        
    Behavior:
        - Removes pending and retry tasks
        - Optionally preserves tasks being processed
        - Updates queue metrics appropriately
        - Logs clear operation with details
    """
```

## Task Filtering and Search

### get_tasks_by_status
```python
def get_tasks_by_status(
    self,
    status: TaskStatus
) -> List[ProcessingTask]:
    """Get all tasks with specified status.
    
    Args:
        status: TaskStatus enum value to filter by
        
    Returns:
        List[ProcessingTask]: Tasks matching the status
        
    Supports:
        - PENDING: Waiting to be processed
        - PROCESSING: Currently being worked on
        - COMPLETED: Successfully finished
        - FAILED: Failed all retry attempts
        - RETRY_PENDING: Waiting for retry attempt
    """
```

### get_tasks_by_worker
```python
def get_tasks_by_worker(
    self,
    worker_id: str
) -> List[ProcessingTask]:
    """Get all tasks assigned to specific worker.
    
    Args:
        worker_id: Worker identifier to filter by
        
    Returns:
        List[ProcessingTask]: Tasks assigned to the worker
        
    Includes:
        - Currently processing tasks
        - Recently completed tasks
        - Failed tasks from this worker
    """
```

### find_task
```python
def find_task(
    self,
    po_number: str = None,
    task_id: str = None
) -> Optional[ProcessingTask]:
    """Find task by PO number or task ID.
    
    Args:
        po_number: PO number to search for
        task_id: Unique task identifier to search for
        
    Returns:
        Optional[ProcessingTask]: Found task or None
        
    Note:
        Either po_number or task_id must be provided
    """
```

## Monitoring and Analytics

### get_performance_metrics
```python
def get_performance_metrics(self) -> Dict[str, Any]:
    """Get detailed performance metrics.
    
    Returns:
        Dict[str, Any]: Performance data with keys:
            - average_task_duration: float seconds per task
            - throughput_last_minute: float tasks per second
            - throughput_last_hour: float tasks per second
            - retry_rate: float percentage of tasks requiring retry
            - failure_rate: float percentage of tasks ultimately failing
            - queue_wait_time: float average seconds tasks wait in queue
            - worker_utilization: Dict[str, float] per-worker utilization rates
    """
```

### get_error_summary
```python
def get_error_summary(self) -> Dict[str, Any]:
    """Get summary of errors encountered.
    
    Returns:
        Dict[str, Any]: Error analysis with keys:
            - total_errors: int total error occurrences
            - unique_error_types: int distinct error types seen
            - most_common_errors: List[Dict] top error types with counts
            - error_trends: Dict hourly error rates
            - retry_success_rate: float percentage of retries that succeed
    """
```

### export_queue_report
```python
def export_queue_report(
    self,
    format: str = "json",
    include_completed: bool = True
) -> Union[Dict, str]:
    """Export comprehensive queue report.
    
    Args:
        format: Export format ("json", "csv", "yaml")
        include_completed: Whether to include completed tasks
        
    Returns:
        Union[Dict, str]: Report data in requested format
        
    Report includes:
        - All task details and history
        - Performance metrics and statistics
        - Error analysis and retry patterns
        - Worker assignment and timing data
    """
```

## Thread Safety and Resource Management

### Resource Management
```python
def _cleanup_resources(self) -> None:
    """Clean up queue resources and memory.
    
    Behavior:
        - Removes completed task references beyond retention period
        - Clears error logs older than configured threshold
        - Compacts queue data structures
        - Releases unnecessary memory allocations
    """
```

### Thread Safety
```python
def _ensure_thread_safety(self) -> None:
    """Ensure thread-safe operations across all methods.
    
    Implementation:
        - Uses threading.RLock for queue operations
        - Atomic operations for status updates
        - Thread-local storage for worker contexts
        - Proper exception handling in multi-threaded environment
    """
```

## Configuration and Tuning

### update_configuration
```python
def update_configuration(
    self,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    task_timeout: Optional[float] = None,
    queue_size_limit: Optional[int] = None
) -> None:
    """Update queue configuration dynamically.
    
    Args:
        max_retries: New maximum retry attempts
        retry_delay: New base retry delay
        task_timeout: New task timeout duration
        queue_size_limit: New maximum queue size
        
    Note:
        Changes apply to new tasks; existing tasks keep original settings
    """
```

### optimize_for_workload
```python
def optimize_for_workload(
    self,
    expected_task_count: int,
    average_task_duration: float,
    worker_count: int
) -> Dict[str, Any]:
    """Optimize queue settings for expected workload.
    
    Args:
        expected_task_count: Number of tasks expected
        average_task_duration: Expected seconds per task
        worker_count: Number of workers that will process tasks
        
    Returns:
        Dict[str, Any]: Recommended configuration settings
        
    Optimizes:
        - Queue size limits
        - Retry timeouts
        - Priority thresholds
        - Memory allocation
    """
```

## Event Handling and Callbacks

### set_event_handlers
```python
def set_event_handlers(
    self,
    on_task_complete: Optional[Callable[[ProcessingTask], None]] = None,
    on_task_failed: Optional[Callable[[ProcessingTask, str], None]] = None,
    on_queue_empty: Optional[Callable[[], None]] = None,
    on_queue_full: Optional[Callable[[], None]] = None
) -> None:
    """Set event handlers for queue operations.
    
    Args:
        on_task_complete: Called when task completes successfully
        on_task_failed: Called when task fails all retries
        on_queue_empty: Called when queue becomes empty
        on_queue_full: Called when queue reaches capacity
    """
```

---

*Contract defines TaskQueue for managing parallel processing tasks with retry logic, monitoring, and thread safety*