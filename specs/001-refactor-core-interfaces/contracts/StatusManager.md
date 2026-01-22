# Interface Contract: StatusManager

**Feature**: 001-refactor-core-interfaces
**Date**: 2025-11-12
**Status**: Complete

## Overview

The StatusManager provides a subscription-based notification system for real-time status updates, enabling UI components to receive processing updates without polling.

## Interface Definition

```python
class StatusManager:
    def subscribe_to_updates(self, callback: Callable[[Dict[str, Any]], None]) -> str:
        """Subscribe to status updates. Returns subscription ID."""

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from updates. Returns success status."""
```

## Preconditions

- StatusManager instance properly initialized
- Callback functions must be callable and thread-safe
- Subscription IDs must be valid (returned from subscribe_to_updates)

## Postconditions

- subscribe_to_updates() returns valid unique subscription ID
- unsubscribe() removes subscription and stops notifications
- Callbacks receive all subsequent status updates

## Invariants

- Subscription IDs are unique across manager lifetime
- Active subscriptions receive all status updates
- Failed callbacks are handled gracefully without interrupting processing

## Error Conditions

| Method | Error Condition | Behavior |
|--------|----------------|----------|
| subscribe_to_updates | Invalid callback | Raises TypeError |
| unsubscribe | Invalid subscription ID | Returns False |
| unsubscribe | Subscription already inactive | Returns False |

## Performance Contracts

- subscribe_to_updates(): <10ms
- unsubscribe(): <10ms
- notify_status_update(): <50ms (for all active subscriptions)

## Thread Safety

- All methods are thread-safe
- Callbacks may be invoked from background threads
- Subscription management is thread-safe
- Concurrent subscribe/unsubscribe operations are safe

## Data Contracts

### Status Update Schema
```python
{
    "timestamp": str,          # ISO 8601 timestamp
    "session_id": str,         # Optional: associated session UUID4
    "event_type": str,         # "status_change" | "progress_update" | "error" | "completion"
    "data": Dict[str, Any]     # Event-specific data payload
}
```

### Callback Function Signature
```python
def status_callback(update: Dict[str, Any]) -> None:
    """
    Status update callback function.

    Args:
        update: Status update dictionary with standardized structure

    Note:
        Callbacks should be fast and thread-safe.
        Exceptions in callbacks are caught and logged.
    """
```

## Failure Handling

### Callback Failure Policy
- Exceptions in callbacks are caught and logged
- Failed callbacks are tracked per subscription
- After 3 consecutive failures, subscription is automatically unsubscribed
- Processing continues unaffected by callback failures

### Failure Tracking
```python
_callback_failures: Dict[str, int]  # subscription_id -> failure_count
```

## Notification Patterns

### Event Types
- **status_change**: Major state transitions (idle→running, running→completed)
- **progress_update**: Periodic progress updates during processing
- **error**: Error conditions that don't stop processing
- **completion**: Final completion status

### Update Frequency
- status_change: Immediate on state transitions
- progress_update: Every 1-5 seconds during active processing
- error: Immediate on error detection
- completion: Immediate on processing end

## Integration Requirements

- Must be integrated with ProcessingController for status source
- Must handle cross-thread notifications properly
- Must provide clean subscription lifecycle management
- Must not interfere with core processing performance

## Backward Compatibility

- Purely additive interface
- No changes to existing status tracking
- Existing code continues to work unchanged
- New subscription system provides additional capability

## Testing Contracts

### Unit Test Requirements
- Test subscription lifecycle (subscribe/unsubscribe)
- Test callback failure handling (3-strike rule)
- Test thread safety with concurrent operations
- Test notification delivery to multiple subscribers
- Test performance contracts

### Integration Test Requirements
- Test with ProcessingController status updates
- Test cross-thread callback execution
- Test error handling without affecting processing
- Test memory leaks with long-running subscriptions