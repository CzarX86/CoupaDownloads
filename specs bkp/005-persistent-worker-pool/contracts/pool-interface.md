# Worker Pool Interface Contract

## PersistentWorkerPool API

### Core Methods

#### `__init__(self, config: PoolConfig) -> None`
**Purpose**: Initialize worker pool with configuration
**Preconditions**: 
- `config.worker_count` between 1-8
- `config.base_profile_path` exists and readable
- System has minimum required RAM (4GB)
**Postconditions**: Pool in INITIALIZING state, workers not yet started

#### `start(self) -> None`
**Purpose**: Start all worker processes and begin task processing
**Preconditions**: Pool in INITIALIZING state
**Postconditions**: 
- All workers in READY state OR pool in ERROR state
- Task queue accepting submissions
- Memory monitor active
**Exceptions**: 
- `ProfileCorruptionError` if base profile invalid
- `InsufficientResourcesError` if cannot allocate workers

#### `submit_task(self, task: POTask) -> TaskHandle`
**Purpose**: Submit PO task for processing
**Preconditions**: Pool in READY or PROCESSING state
**Postconditions**: 
- Task added to queue with unique handle
- Task assigned to available worker OR queued for next available
**Returns**: `TaskHandle` for status tracking
**Exceptions**: `PoolShutdownError` if pool shutting down

#### `get_status(self) -> PoolStatus`
**Purpose**: Get current pool operational status
**Returns**: `PoolStatus` containing:
- Worker states and counts
- Queue depth and processing rate
- Memory usage statistics
- Error counts and last error time

#### `shutdown(self, timeout: float = 60.0) -> bool`
**Purpose**: Gracefully shutdown all workers and cleanup resources
**Preconditions**: None (can be called in any state)
**Postconditions**: 
- All workers terminated
- Browser sessions closed
- Temporary profiles cleaned up
- All resources released
**Returns**: `True` if shutdown completed within timeout
**Timeout Behavior**: Force termination if timeout exceeded

### Event Callbacks

#### `on_worker_crashed(self, worker_id: str, error: Exception) -> None`
**Purpose**: Handle worker process crash
**Behavior**: 
- Log crash details
- Attempt worker restart (max 3 attempts)
- Redistribute failed task to available worker

#### `on_memory_threshold_exceeded(self, usage_percent: float) -> None`
**Purpose**: Handle memory pressure situation
**Behavior**:
- Identify highest-memory worker
- Restart worker after task completion
- Log memory usage statistics

#### `on_task_completed(self, task_handle: TaskHandle, result: TaskResult) -> None`
**Purpose**: Handle successful task completion
**Behavior**:
- Update task status
- Log completion metrics
- Clean up task-specific resources

## Worker Interface Contract

### Core Methods

#### `process_po(self, po_task: POTask) -> POResult`
**Purpose**: Process single PO task within persistent browser session
**Preconditions**: 
- Worker in READY state
- Browser session authenticated
- Task contains valid PO identifier
**Postconditions**: 
- PO processed and files downloaded OR failure recorded
- Browser session remains active
- Worker returns to READY state
**Returns**: `POResult` with download status and file locations
**Exceptions**: 
- `AuthenticationError` if session expired
- `PONotFoundError` if PO doesn't exist
- `NetworkError` for connectivity issues

#### `get_health_status(self) -> WorkerHealth`
**Purpose**: Get worker health metrics
**Returns**: `WorkerHealth` containing:
- Memory usage
- Session uptime
- Processed task count
- Last error (if any)

#### `terminate(self, force: bool = False) -> None`
**Purpose**: Shutdown worker process
**Behavior**:
- Complete current task if `force=False`
- Close browser session
- Clean up profile directory
- Terminate process

## Browser Session Contract

### Session Management

#### `authenticate(self) -> bool`
**Purpose**: Establish authenticated session with Coupa
**Preconditions**: Browser initialized with valid profile
**Postconditions**: 
- Cookies and session state preserved
- Ready for PO processing
**Returns**: `True` if authentication successful
**Timeout**: 30 seconds maximum

#### `create_tab(self, task_id: str) -> TabHandle`
**Purpose**: Create new tab for PO processing
**Preconditions**: Session authenticated
**Postconditions**: 
- New tab opened
- Tab mapped to task ID
- Main session preserved
**Returns**: `TabHandle` for tab operations

#### `close_tab(self, tab_handle: TabHandle) -> None`
**Purpose**: Close tab and cleanup resources
**Preconditions**: Tab exists and mapped
**Postconditions**: 
- Tab closed
- Resources cleaned up
- Main session preserved

### Session Recovery

#### `recover_session(self) -> bool`
**Purpose**: Attempt to recover from session errors
**Behavior**:
- Check authentication status
- Refresh if needed
- Validate session functionality
**Returns**: `True` if recovery successful
**Timeout**: 15 seconds maximum

## Error Handling Contracts

### Exception Hierarchy
```
PoolError (base)
├── ConfigurationError
├── ProfileCorruptionError
├── InsufficientResourcesError
├── PoolShutdownError
└── WorkerError
    ├── AuthenticationError
    ├── PONotFoundError
    ├── NetworkError
    └── SessionCorruptionError
```

### Error Recovery Guarantees
- Pool continues operating if single worker fails
- Task redistribution preserves processing order
- Session errors trigger worker restart, not pool shutdown
- Memory pressure triggers selective worker restart
- Profile corruption triggers immediate pool shutdown

### Timeout Specifications
- Worker startup: 30 seconds maximum
- Task processing: 5 minutes maximum per PO
- Session authentication: 30 seconds maximum
- Graceful shutdown: 60 seconds default (configurable)
- Force shutdown: 10 seconds maximum

## Configuration Schema

### PoolConfig
```python
@dataclass
class PoolConfig:
    worker_count: int = 4                    # 1-8 workers
    headless_mode: bool = True              # Browser visibility
    base_profile_path: str                  # Source profile path
    memory_threshold: float = 0.75          # 50%-90% of system RAM
    max_restart_attempts: int = 3           # Per worker restart limit
    task_timeout: float = 300.0             # 5 minutes per PO
    shutdown_timeout: float = 60.0          # Graceful shutdown limit
```

### TaskConfig
```python
@dataclass  
class POTask:
    po_number: str                          # Purchase order identifier
    priority: int = 0                       # Processing priority (higher first)
    timeout_override: Optional[float] = None # Task-specific timeout
    retry_count: int = 0                    # Current retry attempt
    metadata: Dict[str, Any] = field(default_factory=dict)
```