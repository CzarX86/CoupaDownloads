# WorkerPool API Contract

**Module**: `EXPERIMENTAL.corelib.worker_pool`  
**Class**: `WorkerPool`

## Constructor

```python
def __init__(
    self,
    pool_size: int = 4,
    headless_config: HeadlessConfiguration,
    profile_manager: Optional[ProfileManager] = None,
    max_task_timeout: int = 300
) -> None:
    """Initialize worker pool with specified configuration.
    
    Args:
        pool_size: Number of concurrent workers (1-8)
        headless_config: Browser mode configuration for all workers
        profile_manager: Optional custom profile manager instance
        max_task_timeout: Maximum time per task in seconds
        
    Raises:
        ValueError: If pool_size not in range 1-8
        TypeError: If headless_config is not HeadlessConfiguration instance
    """
```

## Core Methods

### start_processing
```python
def start_processing(self, po_list: List[dict]) -> bool:
    """Start parallel processing of PO list using worker pool.
    
    Args:
        po_list: List of PO data dictionaries with required keys:
                 - po_number: str
                 - supplier: str  
                 - url: str
                 - amount: float
                 
    Returns:
        bool: True if processing started successfully
        
    Raises:
        RuntimeError: If pool already running or in error state
        ValueError: If po_list is empty or contains invalid PO data
        ProfileCreationError: If worker profile setup fails
        
    Side Effects:
        - Creates worker processes with isolated browser profiles
        - Initializes task queue with PO data
        - Starts progress monitoring
        - Updates pool status to RUNNING
    """
```

### stop_processing
```python
def stop_processing(self, timeout: int = 30) -> bool:
    """Stop all workers gracefully and cleanup resources.
    
    Args:
        timeout: Maximum seconds to wait for workers to complete current tasks
        
    Returns:
        bool: True if all workers stopped cleanly within timeout
        
    Side Effects:
        - Signals workers to stop after current task completion
        - Waits for graceful shutdown or forces termination after timeout
        - Cleans up all temporary profiles
        - Joins worker processes
        - Updates pool status to IDLE
    """
```

### get_status
```python
def get_status(self) -> Dict[str, Any]:
    """Get current pool and worker status information.
    
    Returns:
        Dict[str, Any]: Status information with keys:
            - pool_status: PoolStatus enum value
            - active_workers: int count of running workers
            - tasks_pending: int count of unprocessed tasks
            - tasks_active: int count of currently processing tasks
            - tasks_completed: int count of finished tasks
            - tasks_failed: int count of failed tasks
            - worker_details: List[Dict] with per-worker status
            - performance_metrics: Dict with timing and throughput data
    """
```

### get_results
```python
def get_results(self) -> Tuple[int, int, Dict[str, Any]]:
    """Get processing results summary and performance metrics.
    
    Returns:
        Tuple[int, int, Dict[str, Any]]: 
            - successful_count: Number of POs processed successfully
            - failed_count: Number of POs that failed processing
            - performance_data: Detailed metrics including timing, throughput
        
    Note:
        Should only be called after processing completion or during execution
        for progress monitoring
    """
```

## Advanced Methods

### pause_processing
```python
def pause_processing(self) -> bool:
    """Pause processing after current tasks complete.
    
    Returns:
        bool: True if pause was initiated successfully
        
    Note:
        Workers complete current tasks but don't pick up new ones
        Can be resumed with resume_processing()
    """
```

### resume_processing
```python
def resume_processing(self) -> bool:
    """Resume paused processing.
    
    Returns:
        bool: True if resume was successful
        
    Raises:
        RuntimeError: If pool not in paused state
    """
```

### scale_workers
```python
def scale_workers(self, new_size: int) -> bool:
    """Dynamically adjust worker count during processing.
    
    Args:
        new_size: New worker pool size (1-8)
        
    Returns:
        bool: True if scaling completed successfully
        
    Note:
        Scaling down waits for workers to complete current tasks
        Scaling up creates additional workers with isolated profiles
    """
```

## State Management

### Pool States
- **IDLE**: Pool created, no processing active
- **STARTING**: Workers being initialized, profiles being created
- **RUNNING**: Workers actively processing tasks
- **PAUSED**: Processing paused, workers idle but ready
- **STOPPING**: Graceful shutdown in progress
- **ERROR**: Critical error occurred, manual intervention needed

### State Transitions
```python
# Valid transitions:
IDLE -> STARTING        # via start_processing()
STARTING -> RUNNING     # when all workers initialized
RUNNING -> PAUSED       # via pause_processing()
PAUSED -> RUNNING       # via resume_processing()
RUNNING -> STOPPING     # via stop_processing()
STOPPING -> IDLE        # when all workers stopped and cleaned up
Any -> ERROR           # on critical failure
ERROR -> IDLE          # after manual recovery
```

## Error Handling

### Expected Exceptions
- `ValueError`: Invalid configuration parameters or PO data
- `RuntimeError`: Invalid state transitions or pool operations
- `ProfileCreationError`: Temporary profile setup failure
- `WorkerStartupError`: Worker process initialization failure
- `TaskTimeoutError`: Task processing exceeded configured timeout

### Recovery Behavior
- Individual worker failures should not stop other workers
- Failed tasks automatically retried up to configured limit
- Profile cleanup must occur even on abnormal termination
- Pool should gracefully degrade if workers crash
- Error details logged for debugging and monitoring

## Thread Safety

All public methods must be thread-safe for concurrent access:
- Status queries during processing
- Stop/pause requests from signal handlers
- Result collection from monitoring threads
- Dynamic scaling operations

## Performance Requirements

- Worker startup time: < 15 seconds per worker
- Task distribution latency: < 100ms
- Status query response: < 50ms
- Graceful shutdown: < 30 seconds (configurable timeout)
- Memory usage: < 200MB per worker including browser
- Parallel speedup: 3-4x improvement for 4+ workers on 5+ PO batches

## Resource Management

### Memory Management
- Monitor worker memory usage and enforce limits
- Cleanup profiles and temporary files promptly
- Prevent memory leaks in long-running sessions

### Profile Management
- Each worker gets isolated temporary profile
- Profiles cleaned up on worker completion or failure
- Base profile copying preserves essential settings only
- Disk space monitoring and limits

### Process Management
- Worker processes isolated from main process
- Proper signal handling for graceful shutdown
- Orphaned process cleanup on abnormal termination

---

*Contract defines expected behavior for WorkerPool implementation*