# Download Control Contract

**Contract ID**: CONTROL-UI-001
**Date**: 2025-11-12
**Type**: Control Contract
**Components**: `ui/main_window.py` ↔ Core Download System

## Overview

Defines how the UI initiates, monitors, and controls download operations while maintaining separation between UI and core logic.

## Control Flow

### Operation Lifecycle

1. **Configuration** → UI collects and validates settings
2. **Initiation** → UI triggers download process with config
3. **Monitoring** → UI receives status updates via queue
4. **Control** → UI can request operation stop
5. **Completion** → Core signals completion, UI updates state

## Interface Definition

### Download Launcher (UI Side)

**Function**: `start_downloads(config, status_queue)`
**Location**: `src/ui/main_window.py`

```python
def start_downloads(config: dict, status_queue: mp.Queue) -> mp.Process:
    """Launch download operations in separate process.

    Args:
        config: ConfigurationSettings dict
        status_queue: Queue for status communication

    Returns:
        Process object for the download operation

    Preconditions:
        - Configuration is validated
        - No existing download process running
        - Status queue is available

    Postconditions:
        - Download process is started
        - Status updates begin flowing
        - UI state reflects running operation
    """
```

### Download Process (Core Side)

**Function**: `run_download_process(config, status_queue)`
**Location**: Core download system

```python
def run_download_process(config: dict, status_queue: mp.Queue) -> None:
    """Execute download operations with provided configuration.

    Args:
        config: Validated ConfigurationSettings dict
        status_queue: Queue for status updates to UI

    Process Flow:
        1. Initialize worker pool
        2. Load and validate CSV data
        3. Start download operations
        4. Monitor progress and send updates
        5. Handle completion or errors
        6. Cleanup resources
    """
```

### Operation Control

**Function**: `stop_downloads(process)`
**Location**: `src/ui/main_window.py`

```python
def stop_downloads(process: mp.Process) -> None:
    """Request graceful stop of download operations.

    Args:
        process: Download process to stop

    Behavior:
        - Send termination signal to process
        - Wait for graceful shutdown (timeout: 30s)
        - Force terminate if needed
        - Update UI state
    """
```

## State Management

### UI State Transitions

```
READY ── start_downloads() ──→ RUNNING
RUNNING ── stop_downloads() ──→ STOPPING
STOPPING ── completion ──────→ READY
RUNNING ── error ────────────→ ERROR
ERROR ── reset ──────────────→ READY
```

### Process States

- **Initializing**: Setting up workers and resources
- **Running**: Actively processing downloads
- **Stopping**: Gracefully shutting down
- **Completed**: Finished successfully
- **Failed**: Terminated with errors

## Error Handling

### Configuration Errors
**Invalid config**: Return validation errors to UI without starting process
**Missing files**: Report specific missing files/directories
**Permission errors**: Report access issues clearly

### Process Launch Errors
**Process creation failed**: Return error to UI, don't start operations
**Resource allocation failed**: Cleanup partial resources, report error
**Queue communication failed**: Fallback to local operation if possible

### Runtime Errors
**Worker failures**: Continue with remaining workers, report issues
**Network timeouts**: Retry according to config, report progress
**Disk space issues**: Pause operations, alert user
**System interrupts**: Graceful shutdown with partial results

## Resource Management

### Process Lifecycle
- **Creation**: Separate process to avoid UI blocking
- **Resource limits**: Monitor memory and CPU usage
- **Cleanup**: Ensure all resources released on completion
- **Timeout**: Maximum runtime limits to prevent hanging

### Worker Pool Management
- **Initialization**: Create workers based on config
- **Scaling**: Handle worker failures gracefully
- **Shutdown**: Wait for all workers to complete
- **Monitoring**: Track worker health and progress

## Integration Requirements

### Configuration Validation
- UI must validate config before passing to core
- Core assumes valid config (defensive programming still advised)
- Validation errors returned to UI for user correction

### Status Reporting
- Regular progress updates (every 5-10 seconds during active operations)
- Immediate updates for state changes (start, stop, errors)
- Final summary on completion

### Result Handling
- Success/failure counts
- Error details for failed operations
- Performance metrics (if available)
- Generated output file locations

## Testing Requirements

- **Process isolation**: UI process unaffected by core failures
- **State synchronization**: UI state matches actual process state
- **Error propagation**: Core errors properly communicated to UI
- **Resource cleanup**: No resource leaks on process termination
- **Concurrent safety**: Multiple UI interactions handled safely