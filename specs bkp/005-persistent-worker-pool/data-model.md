# Data Model: Persistent Worker Pool with Tab-Based Processing

## Core Entities

### PersistentWorkerPool
**Purpose**: Orchestrates lifecycle management of worker processes and coordinates task distribution

**Attributes**:
- `worker_count: int` - Number of workers to maintain (1-8)
- `headless_mode: bool` - Browser visibility setting
- `base_profile_path: str` - Path to source browser profile for cloning
- `workers: List[WorkerProcess]` - Active worker process references
- `task_queue: Queue[POTask]` - Thread-safe task distribution queue
- `shutdown_event: Event` - Coordination signal for graceful shutdown
- `memory_threshold: float` - Memory usage threshold (75% of system RAM)

**State Transitions**:
- `INITIALIZING` → `READY` → `PROCESSING` → `SHUTTING_DOWN` → `TERMINATED`

**Relationships**:
- 1:N with Worker (manages multiple workers)
- 1:1 with TaskQueue (owns task distribution)
- 1:1 with MemoryMonitor (monitors resource usage)

### Worker  
**Purpose**: Long-running process that maintains browser session and processes POs via tabs

**Attributes**:
- `worker_id: str` - Unique identifier for worker process
- `profile_path: str` - Path to worker's isolated browser profile
- `browser_session: BrowserSession` - Persistent WebDriver session
- `current_task: Optional[POTask]` - Currently processing PO task
- `status: WorkerStatus` - Current operational state
- `memory_usage: int` - Current memory consumption in bytes
- `processed_count: int` - Number of POs completed by this worker

**State Transitions**:
- `STARTING` → `READY` → `PROCESSING` → `IDLE` → `TERMINATING` → `TERMINATED`
- `CRASHED` → `RESTARTING` → `READY` (recovery path)

**Relationships**:
- N:1 with PersistentWorkerPool (managed by pool)
- 1:1 with BrowserSession (owns browser instance)
- 1:N with Tab (creates multiple tabs per session)

### BrowserSession
**Purpose**: Maintains persistent WebDriver instance with session state preservation

**Attributes**:
- `driver: WebDriver` - Selenium WebDriver instance
- `main_window_handle: str` - Reference to initial browser tab
- `active_tabs: Dict[str, str]` - Mapping of task IDs to window handles
- `session_cookies: Dict[str, Any]` - Preserved authentication state
- `startup_time: datetime` - Session initialization timestamp
- `last_activity: datetime` - Last successful operation timestamp

**State Transitions**:
- `INITIALIZING` → `AUTHENTICATED` → `ACTIVE` → `CLOSING` → `CLOSED`
- `ERROR` → `RECOVERING` → `ACTIVE` (error recovery)

**Relationships**:
- 1:1 with Worker (owned by worker)
- 1:N with Tab (manages multiple tabs)
- 1:1 with Profile (uses cloned profile)

### Tab
**Purpose**: Short-lived browser tab for individual PO processing within persistent session

**Attributes**:
- `window_handle: str` - Browser window identifier
- `task_id: str` - Associated PO task identifier
- `creation_time: datetime` - Tab opening timestamp
- `po_number: str` - Purchase order being processed
- `status: TabStatus` - Current processing state

**State Transitions**:
- `OPENING` → `LOADING` → `PROCESSING` → `COMPLETED` → `CLOSING` → `CLOSED`
- `ERROR` → `FAILED` (error path)

**Relationships**:
- N:1 with BrowserSession (created within session)
- 1:1 with POTask (processes one task)

### Profile
**Purpose**: Isolated browser profile clone for worker process isolation

**Attributes**:
- `profile_id: str` - Unique profile identifier
- `base_profile_path: str` - Source profile location
- `worker_profile_path: str` - Worker-specific profile location
- `clone_time: datetime` - Profile creation timestamp
- `corruption_detected: bool` - Profile integrity status

**State Transitions**:
- `CLONING` → `READY` → `IN_USE` → `CLEANUP` → `REMOVED`
- `CORRUPTED` → `FAILED` (corruption path)

**Relationships**:
- 1:1 with Worker (assigned to worker)
- N:1 with BaseProfile (cloned from base)

## Validation Rules

### Worker Pool Constraints
- Worker count must be between 1 and 8 (inclusive)
- Memory threshold must be between 50% and 90% of system RAM
- Base profile must exist and be readable before worker initialization
- Maximum 1 minute timeout for graceful shutdown operations

### Worker Process Rules
- Each worker must have unique profile path and worker ID
- Workers cannot share browser profiles or session state
- Workers must complete current PO before accepting shutdown signal
- Worker restart attempts limited to 3 per session

### Session State Management
- Browser sessions must preserve cookies and authentication across PO processing
- Sessions persist until batch completion or explicit termination
- Tab creation/cleanup must maintain session state integrity
- Main window handle must never be closed during worker lifecycle

### Resource Management
- Total memory usage monitoring across all worker processes
- Individual worker memory tracking for restart decisions
- Profile cleanup required on worker termination
- Temporary files must be cleaned up on shutdown

## Error Handling Patterns

### Cascading Recovery
1. **Worker Crash**: Attempt worker restart with same profile
2. **Restart Failure**: Redistribute failed PO to available worker
3. **No Available Workers**: Mark PO as failed and continue processing

### Profile Corruption
- **Detection**: During worker initialization or session startup
- **Response**: Abort entire operation and require manual intervention
- **Rationale**: Prevents data integrity issues and system instability

### Memory Exhaustion
- **Trigger**: Total usage exceeds 75% of available system RAM
- **Response**: Restart highest-memory worker process
- **Fallback**: Graceful shutdown if restart fails

### Session Timeout
- **Detection**: Authentication or network errors during PO processing
- **Response**: Attempt to refresh session within same browser instance
- **Fallback**: Worker restart if session recovery fails