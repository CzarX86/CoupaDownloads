# GUI-Core Interface Contract

**Feature**: 002-tkinter-ui
**Date**: 2025-11-12

## Overview

This contract defines the interfaces between the Tkinter GUI components and the core CoupaDownloads system. The GUI acts as a client to the core system, providing configuration and control while receiving status updates.

## Core System Interface

### Configuration Management

**Endpoint**: `core.load_configuration() -> ConfigurationSettings`
- **Purpose**: Load persisted configuration on GUI startup
- **Returns**: ConfigurationSettings object or None if no config exists
- **Error Handling**: Returns None on file access errors

**Endpoint**: `core.save_configuration(config: ConfigurationSettings) -> bool`
- **Purpose**: Persist configuration changes
- **Parameters**: config - validated ConfigurationSettings object
- **Returns**: True on success, False on failure
- **Error Handling**: Validates configuration before saving, logs errors

**Endpoint**: `core.validate_configuration(config: ConfigurationSettings) -> List[str]`
- **Purpose**: Validate configuration against business rules
- **Parameters**: config - ConfigurationSettings to validate
- **Returns**: List of validation error messages (empty if valid)
- **Error Handling**: Comprehensive validation of paths, ranges, permissions

### Operation Control

**Endpoint**: `core.start_downloads(config: ConfigurationSettings, status_callback: Callable) -> OperationHandle`
- **Purpose**: Initiate download operations with GUI status callback
- **Parameters**:
  - config: validated ConfigurationSettings
  - status_callback: function to call with StatusMessage objects
- **Returns**: OperationHandle for tracking/cancellation
- **Error Handling**: Validates config before starting, provides error status

**Endpoint**: `core.stop_downloads(handle: OperationHandle) -> bool`
- **Purpose**: Gracefully stop ongoing download operations
- **Parameters**: handle - OperationHandle from start_downloads
- **Returns**: True if stop signal sent successfully
- **Error Handling**: Handles already-stopped operations gracefully

**Endpoint**: `core.get_operation_status(handle: OperationHandle) -> OperationStatus`
- **Purpose**: Get current status of download operation
- **Parameters**: handle - OperationHandle from start_downloads
- **Returns**: OperationStatus enum (NOT_STARTED, RUNNING, COMPLETED, ERROR, STOPPED)
- **Error Handling**: Returns ERROR status for invalid handles

## Data Types

### ConfigurationSettings
```python
@dataclass
class ConfigurationSettings:
    worker_count: int
    download_directory: Path
    csv_file_path: Path
    max_retries: int
    last_modified: datetime = field(default_factory=datetime.now)
```

### StatusMessage
```python
@dataclass
class StatusMessage:
    timestamp: datetime
    level: StatusLevel  # INFO, WARNING, ERROR, SUCCESS
    message: str
    operation_id: Optional[str] = None
    progress: Optional[int] = None
```

### OperationHandle
```python
class OperationHandle:
    """Opaque handle for tracking operations"""
    pass
```

## Communication Patterns

### Status Updates
- Status callbacks called from background threads
- GUI must handle callbacks in main thread using `root.after()`
- Callbacks are fire-and-forget (no return values expected)

### Error Handling
- Core system provides detailed error messages for GUI display
- GUI translates technical errors to user-friendly messages
- Configuration validation errors include specific field information

### Threading Model
- GUI runs in main thread
- Core operations run in background threads/processes
- Status communication through thread-safe callbacks