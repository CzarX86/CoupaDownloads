# Data Model: Refactor Core Interfaces for UI Integration

**Feature**: 001-refactor-core-interfaces
**Date**: 2025-11-12
**Status**: Complete

## Data Model Overview

Three interface classes with simplified data contracts using only built-in Python types for UI serialization compatibility.

## ConfigurationManager Data Model

### Configuration Dictionary Structure
```python
{
    "input_path": str,        # Path to input CSV files
    "output_path": str,       # Path for processed outputs
    "download_dir": str,      # Directory for browser downloads
    "max_workers": int,       # Maximum concurrent workers
    "timeout": int,           # Operation timeout in seconds
    "browser_profile": str,   # Browser profile directory
    "log_level": str,         # Logging level (DEBUG, INFO, etc.)
    "auto_save": bool         # Auto-save configuration changes
}
```

### Validation Rules
- **Required Fields**: input_path, output_path, download_dir
- **Path Validation**: All path fields must exist and be writable
- **Numeric Ranges**: max_workers (1-10), timeout (30-3600)
- **Enum Values**: log_level must be valid logging level name

## ProcessingController Data Model

### Session ID
- **Type**: str (UUID4 format)
- **Uniqueness**: Guaranteed unique across sessions and restarts
- **Format**: Standard UUID4 string representation

### Processing Status Dictionary
```python
{
    "session_id": str,        # UUID4 session identifier
    "state": str,            # "idle" | "starting" | "running" | "stopping" | "completed" | "error"
    "progress": float,       # 0.0 to 1.0 progress indicator
    "current_operation": str,# Description of current operation
    "items_processed": int,  # Number of items completed
    "total_items": int,      # Total items to process
    "start_time": str,       # ISO format timestamp
    "estimated_time_remaining": int,  # Seconds remaining (optional)
    "error_message": str     # Error description if state == "error"
}
```

### Start Parameters
```python
{
    "config": dict,          # Full configuration dictionary
    "session_name": str      # Optional human-readable session name
}
```

## StatusManager Data Model

### Subscription ID
- **Type**: str (UUID4 format)
- **Purpose**: Unique identifier for callback subscriptions
- **Lifecycle**: Generated on subscribe, used for unsubscribe

### Status Update Dictionary
```python
{
    "timestamp": str,        # ISO format timestamp
    "session_id": str,       # Associated processing session (if any)
    "event_type": str,       # "status_change" | "progress_update" | "error" | "completion"
    "data": dict            # Event-specific data (see Processing Status structure)
}
```

### Callback Function Signature
```python
def status_callback(update: dict) -> None:
    """
    Callback function for status updates.

    Args:
        update: Status update dictionary with timestamp, session_id, event_type, data
    """
```

## Error Handling Data Model

### Validation Error Dictionary
```python
{
    "field": str,           # Field name that failed validation
    "error_type": str,      # "missing" | "invalid_type" | "out_of_range" | "invalid_value"
    "message": str,         # Human-readable error description
    "current_value": any    # The invalid value that was provided
}
```

### Processing Error Dictionary
```python
{
    "error_type": str,      # "validation" | "processing" | "system" | "timeout"
    "message": str,         # Detailed error description
    "recoverable": bool,    # Whether operation can be retried
    "session_id": str,      # Associated session if applicable
    "timestamp": str        # When error occurred
}
```

## Data Flow Diagrams

### Configuration Flow
```
UI Layer → ConfigurationManager.get_config() → dict
UI Layer → ConfigurationManager.save_config(dict) → bool
UI Layer → ConfigurationManager.validate_config(dict) → List[dict]
```

### Processing Flow
```
UI Layer → ProcessingController.start_processing(dict) → str (session_id)
UI Layer → ProcessingController.get_status(str) → dict
UI Layer → ProcessingController.stop_processing(str) → bool
```

### Status Notification Flow
```
StatusManager ← ProcessingController (internal updates)
StatusManager → UI Callbacks (dict updates)
UI Layer → StatusManager.subscribe(callback) → str (subscription_id)
UI Layer → StatusManager.unsubscribe(str) → bool
```

## Serialization Compatibility

### JSON Serialization Requirements
- All data structures use only JSON-serializable types
- datetime objects converted to ISO format strings
- No custom classes or complex objects
- UUID objects converted to string representation

### Thread Safety Considerations
- Status updates may occur from background threads
- Callbacks must be thread-safe or properly synchronized
- Configuration operations are synchronous and thread-safe

## Backward Compatibility

### Existing MainApp Integration
- Interfaces wrap existing MainApp functionality
- No changes to internal data structures
- All existing CLI operations continue to work
- New interfaces provide additional access patterns

## Validation Rules Summary

| Data Structure | Required Fields | Type Validation | Range Validation |
|----------------|-----------------|-----------------|------------------|
| Configuration | input_path, output_path, download_dir | str paths | paths exist & writable |
| Processing Status | session_id, state | str, valid enum | progress 0.0-1.0 |
| Status Update | timestamp, event_type | ISO str, valid enum | N/A |
| Validation Error | field, error_type, message | str types | N/A |

This data model provides clean, serializable interfaces while maintaining compatibility with existing systems.