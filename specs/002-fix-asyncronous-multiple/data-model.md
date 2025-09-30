# Data Model: Asynchronous/Multiple Workers Implementation

**Feature**: Fix Asynchronous/Multiple Workers in EXPERIMENTAL Subproject  
**Date**: 2025-09-29

## Core Entities

### WorkerPool
**Purpose**: Manages the lifecycle and coordination of multiple worker processes for parallel PO processing

**Attributes**:
- `pool_size: int` - Number of concurrent worker processes (default: 4, max: 8)
- `headless_config: HeadlessConfiguration` - Browser mode configuration for all workers
- `active_workers: List[WorkerInstance]` - Currently running worker processes
- `task_queue: TaskQueue` - Queue of PO processing tasks awaiting assignment
- `status: PoolStatus` - Current state (IDLE, STARTING, RUNNING, STOPPING, ERROR)
- `created_at: datetime` - Pool creation timestamp
- `profile_manager: ProfileManager` - Manages temporary browser profiles
- `performance_metrics: Dict[str, Any]` - Processing statistics and timings

**State Transitions**:
- IDLE → STARTING (when parallel processing initiated)
- STARTING → RUNNING (when all workers initialized successfully)
- RUNNING → STOPPING (when stop_processing called or completion)
- RUNNING → ERROR (when critical failure occurs)
- STOPPING → IDLE (when all workers completed and cleaned up)
- ERROR → IDLE (after error recovery and cleanup)

**Business Rules**:
- Pool size must be between 1 and 8 workers
- All workers must use same HeadlessConfiguration
- Cannot start new processing while in STOPPING or ERROR state
- Profile manager must cleanup all profiles when pool stops
- Performance metrics tracked for optimization and monitoring

### WorkerInstance
**Purpose**: Represents an individual worker process with isolated browser profile and execution context

**Attributes**:
- `worker_id: str` - Unique identifier (e.g., "worker_001")
- `process_id: int` - System process ID of the worker
- `profile_path: str` - Path to temporary browser profile directory
- `status: WorkerStatus` - Current state (INITIALIZING, READY, PROCESSING, COMPLETED, FAILED)
- `current_task: Optional[ProcessingTask]` - Task currently being processed
- `processed_count: int` - Number of POs successfully processed
- `failed_count: int` - Number of POs that failed processing
- `start_time: datetime` - Worker start timestamp
- `last_activity: datetime` - Last activity timestamp for health monitoring
- `error_message: Optional[str]` - Last error message if failed

**State Transitions**:
- INITIALIZING → READY (when browser and profile setup complete)
- READY → PROCESSING (when assigned a processing task)
- PROCESSING → READY (when task processing completes successfully)
- PROCESSING → FAILED (when task processing encounters unrecoverable error)
- Any state → COMPLETED (when worker shutdown requested)

**Business Rules**:
- Worker ID must be unique within a pool
- Profile path must be cleaned up when worker completes
- Failed workers should log detailed error information for debugging
- Health monitoring should detect inactive workers (timeout detection)
- Last activity updated on every significant operation

### ProfileManager
**Purpose**: Handles creation, management, and cleanup of temporary browser profiles for workers

**Attributes**:
- `base_profile_path: Optional[str]` - Template profile to copy (if any)
- `temp_profiles: Dict[str, str]` - Mapping of worker_id to profile path
- `cleanup_on_exit: bool` - Whether to auto-cleanup profiles (default: True)
- `max_profiles: int` - Maximum number of concurrent profiles (default: 8)
- `profile_size_limit: int` - Maximum profile size in MB (default: 500)
- `cleanup_timeout: int` - Timeout for cleanup operations in seconds

**Methods**:
- `create_profile(worker_id: str) -> str` - Create temporary profile for worker
- `copy_base_profile(worker_id: str) -> bool` - Copy base profile if configured
- `cleanup_profile(worker_id: str) -> bool` - Remove worker's temporary profile
- `cleanup_all_profiles() -> int` - Remove all temporary profiles, return count
- `get_profile_size(worker_id: str) -> int` - Get profile disk usage in bytes
- `validate_profile(worker_id: str) -> bool` - Check profile integrity and accessibility

**Business Rules**:
- Each worker must have unique temporary profile
- Profiles created in system temp directory with secure permissions
- Cleanup must be robust (handle locked files, permissions, crashes)
- Base profile copying should preserve essential settings only
- Profile size monitoring to prevent disk space exhaustion

### TaskQueue
**Purpose**: Thread-safe distribution of PO processing tasks across available workers

**Attributes**:
- `pending_tasks: Queue[ProcessingTask]` - Tasks waiting for worker assignment
- `active_tasks: Dict[str, ProcessingTask]` - Tasks currently being processed (worker_id -> task)
- `completed_tasks: List[ProcessingTask]` - Successfully completed tasks
- `failed_tasks: List[ProcessingTask]` - Tasks that failed processing (for retry)
- `retry_limit: int` - Maximum retry attempts per task (default: 2)
- `task_timeout: int` - Maximum processing time per task in seconds
- `distribution_strategy: str` - Task assignment strategy ("round_robin", "load_balanced")

**Methods**:
- `add_task(po_data: dict) -> str` - Add PO for processing, return task_id
- `get_next_task() -> Optional[ProcessingTask]` - Get next task for worker assignment
- `mark_task_active(task_id: str, worker_id: str) -> bool` - Mark task as actively processing
- `mark_task_complete(task_id: str, worker_id: str, result: dict) -> bool` - Mark task completed
- `mark_task_failed(task_id: str, worker_id: str, error: str) -> bool` - Mark task as failed
- `retry_failed_tasks() -> int` - Requeue failed tasks for retry, return count
- `get_queue_status() -> Dict[str, int]` - Get counts for pending, active, completed, failed

**Business Rules**:
- Tasks must be assigned to exactly one worker at a time
- Failed tasks can be retried up to retry_limit times
- Queue operations must be thread-safe for concurrent access
- Task history preserved for audit and debugging purposes
- Timeout detection for stuck tasks

### ProcessingTask
**Purpose**: Represents a single PO processing task with metadata and progress tracking

**Attributes**:
- `task_id: str` - Unique task identifier (UUID)
- `po_data: dict` - PO information (number, supplier, URL, amount, etc.)
- `status: TaskStatus` - Current state (PENDING, ASSIGNED, PROCESSING, COMPLETED, FAILED)
- `assigned_worker: Optional[str]` - Worker ID currently processing this task
- `attempt_count: int` - Number of processing attempts made
- `created_at: datetime` - Task creation timestamp
- `started_at: Optional[datetime]` - Processing start timestamp
- `completed_at: Optional[datetime]` - Processing completion timestamp
- `error_message: Optional[str]` - Last error message if failed
- `result_summary: Optional[dict]` - Processing results (downloads, status, paths, etc.)
- `priority: int` - Task priority for queue ordering (default: 0)

**State Transitions**:
- PENDING → ASSIGNED (when worker picks up task)
- ASSIGNED → PROCESSING (when worker starts processing)
- PROCESSING → COMPLETED (when processing succeeds)
- PROCESSING → FAILED (when processing fails)
- FAILED → PENDING (when task retried, if within retry limit)

**Business Rules**:
- Task ID must be unique across all tasks in session
- Attempt count must not exceed configured retry limit
- Error messages should be detailed for debugging purposes
- Result summary should include download counts, file paths, processing time
- Priority ordering for task queue management

### ProcessingSession
**Purpose**: Overall coordination and monitoring of parallel processing execution

**Attributes**:
- `session_id: str` - Unique session identifier
- `worker_pool: WorkerPool` - Associated worker pool instance
- `total_tasks: int` - Total number of tasks in session
- `start_time: datetime` - Session start timestamp
- `end_time: Optional[datetime]` - Session completion timestamp
- `status: SessionStatus` - Current state (INITIALIZING, RUNNING, COMPLETED, FAILED)
- `progress_callback: Optional[Callable]` - Progress update callback function
- `performance_stats: Dict[str, Any]` - Session-level performance metrics

**Methods**:
- `start_processing(po_list: List[dict]) -> bool` - Begin parallel processing
- `stop_processing() -> bool` - Stop all processing and cleanup
- `get_progress() -> Dict[str, Any]` - Get current progress information
- `get_results() -> Tuple[int, int]` - Get final success/failure counts
- `export_session_report() -> dict` - Generate detailed session report

**Business Rules**:
- Session manages complete lifecycle of parallel processing
- Progress tracking provides real-time updates to user interface
- Performance statistics enable optimization and troubleshooting
- Session report provides audit trail and performance analysis

## Supporting Enums

### PoolStatus
- `IDLE` - Pool created but not processing
- `STARTING` - Pool initializing workers
- `RUNNING` - Pool actively processing tasks
- `STOPPING` - Pool shutting down gracefully
- `ERROR` - Pool encountered critical error

### WorkerStatus  
- `INITIALIZING` - Worker starting up, setting up profile and browser
- `READY` - Worker ready to accept tasks
- `PROCESSING` - Worker currently processing a PO
- `COMPLETED` - Worker finished and cleaned up
- `FAILED` - Worker encountered unrecoverable error

### TaskStatus
- `PENDING` - Task waiting for worker assignment
- `ASSIGNED` - Task assigned to worker but not started
- `PROCESSING` - Task currently being processed
- `COMPLETED` - Task completed successfully
- `FAILED` - Task failed processing (within retry limits)

### SessionStatus
- `INITIALIZING` - Session starting up
- `RUNNING` - Session actively processing
- `COMPLETED` - Session finished successfully
- `FAILED` - Session encountered critical failure

## Integration Points

### Existing Models
- **HeadlessConfiguration**: Passed to WorkerPool for browser mode configuration
- **BrowserManager**: Enhanced to accept profile path parameter for worker isolation
- **MainApp**: Extended with ProcessingSession for parallel processing coordination

### New Dependencies
- **multiprocessing**: For worker process management and inter-process communication
- **queue**: For thread-safe task distribution and coordination
- **tempfile**: For temporary profile directory creation
- **shutil**: For profile copying and cleanup operations
- **threading**: For progress monitoring and timeout detection

## Validation Rules

### Data Integrity
- Worker pool size between 1-8 workers (configurable maximum)
- Profile paths must be valid, writable, and in temp directory
- Task retry count within configured limits
- Worker health monitoring with configurable timeout detection
- Session state consistency across all components

### Resource Management
- Temporary profiles cleaned up on worker completion or failure
- Memory usage monitoring for worker processes
- Disk space validation for profile creation and downloads
- Browser process cleanup on worker failure or timeout
- Profile size limits to prevent disk exhaustion

### Error Handling
- Worker failures isolated from other workers (no cascading failures)
- Failed tasks automatically retried within configured limits
- Profile cleanup occurs even on abnormal termination
- Comprehensive logging for debugging and performance monitoring
- Graceful degradation to sequential mode on critical failures

### ResourceMonitor
**Purpose**: Monitors system resources and triggers automatic worker scaling to maintain optimal performance

**Attributes**:
- `cpu_threshold: float` - Maximum CPU utilization before scaling down (default: 0.8 = 80%)
- `memory_threshold: float` - Maximum memory utilization before scaling down (default: 0.9 = 90%)
- `check_interval: int` - Seconds between resource checks (default: 5)
- `current_cpu: float` - Current CPU utilization (0.0-1.0)
- `current_memory: float` - Current memory utilization (0.0-1.0)
- `worker_pool: WorkerPool` - Reference to managed worker pool
- `monitoring_active: bool` - Whether monitoring is currently running
- `scaling_history: List[Dict]` - History of scaling decisions with timestamps

**State Transitions**:
- INACTIVE → MONITORING (when worker pool starts)
- MONITORING → SCALING_DOWN (when thresholds exceeded)
- SCALING_DOWN → MONITORING (when scaling complete)
- MONITORING → INACTIVE (when worker pool stops)

**Business Rules**:
- CPU threshold must be between 0.5 and 0.95
- Memory threshold must be between 0.7 and 0.98
- Check interval must be between 1 and 30 seconds
- Scaling decisions recorded with timestamps and reasons
- Cannot scale below 1 worker regardless of resource pressure

**Integration Points**:
- **WorkerPool**: Triggers worker count adjustments
- **ProcessingSession**: Provides resource utilization in progress reports
- **Configuration**: Respects system-wide monitoring settings

### Performance Requirements
- Worker initialization time under 30 seconds per worker
- Task distribution latency under 100ms
- Queue operations optimized for concurrent access
- Progress updates provided in real-time without blocking processing
- Resource cleanup completed within 10 seconds of session end
- Resource monitoring overhead under 1% CPU usage
- Scaling decisions completed within 2 seconds of threshold breach

---

*Data model complete with 7 entities - ready for contract generation*