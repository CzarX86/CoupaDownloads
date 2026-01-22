# Interface Contract: ProcessingController

**Feature**: 001-refactor-core-interfaces
**Date**: 2025-11-12
**Status**: Complete

## Overview

The ProcessingController provides clean start/stop/status operations for processing workflows, managing session lifecycle while wrapping existing MainApp functionality.

## Interface Definition

```python
class ProcessingController:
    def start_processing(self, config: Dict[str, Any]) -> str:
        """Start processing with configuration. Returns session ID."""

    def stop_processing(self, session_id: str) -> bool:
        """Stop processing for session. Returns success status."""

    def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get current processing status for session."""
```

## Preconditions

- ProcessingController must be initialized with valid MainApp instance
- Configuration must be validated before start_processing
- Session IDs must be valid UUID4 strings
- No concurrent session operations for same session

## Postconditions

- start_processing() returns valid session ID on success
- stop_processing() ensures graceful shutdown
- get_status() returns current accurate status

## Invariants

- Only one active session at a time (single-session constraint)
- Session IDs are unique across application lifetime
- Status information remains consistent during operations

## Error Conditions

| Method | Error Condition | Behavior |
|--------|----------------|----------|
| start_processing | Already active session | Raises RuntimeError |
| start_processing | Invalid configuration | Raises ValueError |
| start_processing | MainApp failure | Raises RuntimeError |
| stop_processing | Invalid session ID | Returns False |
| stop_processing | MainApp stop failure | Returns False, logs error |
| get_status | Invalid session ID | Returns {"state": "unknown"} |

## Performance Contracts

- start_processing(): <500ms (includes config application)
- stop_processing(): <200ms (graceful shutdown)
- get_status(): <50ms (status retrieval)

## Thread Safety

- Methods are thread-safe for UI integration
- Status queries can be called concurrently with processing
- Start/stop operations are serialized
- Status updates from background threads are safe

## Data Contracts

### Start Parameters Schema
```python
{
    "config": Dict[str, Any],    # Valid configuration dictionary
    "session_name": str         # Optional human-readable name
}
```

### Status Response Schema
```python
{
    "session_id": str,          # UUID4 session identifier
    "state": str,              # "idle" | "starting" | "running" | "stopping" | "completed" | "error"
    "progress": float,         # 0.0 to 1.0
    "current_operation": str,  # Current operation description
    "items_processed": int,    # Items completed
    "total_items": int,        # Total items to process
    "start_time": str,         # ISO timestamp
    "estimated_time_remaining": int,  # Optional: seconds remaining
    "error_message": str       # Error description if state == "error"
}
```

## Session Lifecycle

1. **Creation**: start_processing() generates unique session ID
2. **Active**: Session processes until completion or stop
3. **Termination**: stop_processing() or natural completion
4. **Cleanup**: Resources released, status becomes "completed"

## Backward Compatibility

- Existing MainApp processing logic unchanged
- CLI operations continue to work
- New interface provides additional control layer
- No breaking changes to existing workflows

## Integration Requirements

- Must integrate with StatusManager for notifications
- Must handle MainApp threading model properly
- Must provide clean error propagation
- Must support graceful shutdown signals

## Testing Contracts

### Unit Test Requirements
- Test single-session constraint enforcement
- Test all error conditions and edge cases
- Test session lifecycle management
- Test performance contracts
- Test thread safety

### Integration Test Requirements
- Test with real MainApp instance
- Test status integration with StatusManager
- Test backward compatibility with CLI
- Test error recovery and cleanup