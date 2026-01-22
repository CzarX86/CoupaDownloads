# Core Interfaces Documentation

## Overview

The CoupaDownloads core interfaces provide a clean, thread-safe API for UI integration while maintaining backward compatibility with existing CLI usage patterns. All interfaces use only built-in Python types (dict, str, bool, int, float) for seamless UI serialization.

## Interfaces

### ConfigurationManager

Manages application configuration with file persistence and validation.

#### Key Features
- File-based configuration persistence
- Configuration validation with detailed error messages
- Thread-safe operations
- Default configuration management

#### Usage Example

```python
from src.core.config_interface import ConfigurationManager

# Initialize (uses default config file location)
config_manager = ConfigurationManager()

# Get current configuration
config = config_manager.get_config()
print(f"Max workers: {config['max_workers']}")

# Modify configuration
config['max_workers'] = 4
config['headless_mode'] = True
success = config_manager.save_config(config)

# Validate configuration
validation = config_manager.validate_config(config)
if not validation['valid']:
    print(f"Errors: {validation['errors']}")

# Reset to defaults
config_manager.reset_to_defaults()
```

#### Configuration Schema

```python
{
    "headless_mode": bool,           # Run browser in headless mode
    "enable_parallel": bool,         # Enable parallel processing
    "max_workers": int,              # Maximum number of worker processes (>= 1)
    "download_folder": str,          # Download directory path
    "input_file_path": str,          # Input file path
    "csv_enabled": bool,             # Enable CSV output (optional)
    "csv_path": str|None             # CSV output path (optional)
}
```

### ProcessingController

Manages processing sessions with status tracking and session isolation.

#### Key Features
- Single active session constraint
- Real-time status tracking
- Thread-safe session management
- Background processing support

#### Usage Example

```python
from src.core.processing_controller import ProcessingController

# Initialize
processing_controller = ProcessingController()

# Start processing
config = {
    "headless_mode": True,
    "enable_parallel": False,
    "max_workers": 1,
    "download_folder": "/tmp/downloads",
    "input_file_path": "/tmp/input.csv"
}

session_id = processing_controller.start_processing(config)

# Check status
status = processing_controller.get_status(session_id)
print(f"State: {status['state']}, Progress: {status['progress']}")

# Stop processing
processing_controller.stop_processing(session_id)
```

#### Status Schema

```python
{
    "session_id": str,                    # Unique session identifier
    "state": str,                        # "starting" | "running" | "completed" | "failed" | "unknown"
    "progress": float,                   # Progress percentage (0.0 to 1.0)
    "current_operation": str,            # Current operation description
    "items_processed": int,              # Number of items processed
    "total_items": int,                  # Total number of items
    "start_time": str,                   # ISO format start time
    "estimated_time_remaining": float|None, # Estimated seconds remaining
    "error_message": str                 # Error message (if any)
}
```

### StatusManager

Provides real-time status updates through a subscription system.

#### Key Features
- Publisher-subscriber pattern
- Thread-safe notification system
- Automatic cleanup of failed subscribers
- Callback failure handling (3-strike policy)

#### Usage Example

```python
from src.core.status_manager import StatusManager
from src.core import StatusUpdate, StatusEventType
import time

# Initialize
status_manager = StatusManager()

# Subscribe to updates
def status_callback(update):
    print(f"Event: {update.event_type}, Progress: {update.data.get('progress', 0)}")

subscription_id = status_manager.subscribe_to_updates(status_callback)

# Send status update
update = StatusUpdate(
    event_type=StatusEventType.PROCESSING_STARTED,
    session_id="session-123",
    timestamp=time.time(),
    data={"progress": 0.0}
)

status_manager.notify_status_update(update)

# Unsubscribe
status_manager.unsubscribe(subscription_id)
```

#### StatusUpdate Schema

```python
StatusUpdate = {
    "event_type": StatusEventType,       # Event type enum
    "session_id": str,                   # Associated session ID
    "timestamp": float,                  # Unix timestamp
    "data": dict                         # Event-specific data
}
```

#### StatusEventType Values

- `PROCESSING_STARTED` - Processing session started
- `PROGRESS_UPDATE` - Progress update with current status
- `PROCESSING_COMPLETED` - Processing completed successfully
- `PROCESSING_FAILED` - Processing failed with error

## Integration Example

Here's how to use all three interfaces together for a complete UI integration:

```python
from src.core.config_interface import ConfigurationManager
from src.core.processing_controller import ProcessingController
from src.core.status_manager import StatusManager
from src.core import StatusUpdate, StatusEventType
import time

# Initialize interfaces
config_manager = ConfigurationManager()
processing_controller = ProcessingController()
status_manager = StatusManager()

# UI callback for real-time updates
def ui_callback(update):
    # Update UI with status information
    if update.event_type == StatusEventType.PROGRESS_UPDATE:
        progress = update.data.get('progress', 0)
        ui.update_progress(progress)

# Subscribe to status updates
subscription_id = status_manager.subscribe_to_updates(ui_callback)

# Load and validate configuration
config = config_manager.get_config()
validation = config_manager.validate_config(config)
if not validation['valid']:
    raise ValueError(f"Invalid config: {validation['errors']}")

# Start processing
try:
    session_id = processing_controller.start_processing(config)

    # Monitor progress
    while True:
        status = processing_controller.get_status(session_id)
        if status['state'] in ['completed', 'failed']:
            break
        time.sleep(1)  # Update UI every second

except RuntimeError:
    # Processing already active
    print("Processing is already running")

finally:
    # Cleanup
    status_manager.unsubscribe(subscription_id)
```

## Performance Characteristics

All interfaces are designed for UI responsiveness:

- **ConfigurationManager**: < 100ms for all operations
- **StatusManager**: < 50ms for subscribe/notify/unsubscribe
- **ProcessingController**: < 500ms for start/stop, < 100ms for status queries

## Thread Safety

All interfaces are thread-safe and can be safely accessed from UI threads:

- ConfigurationManager: Uses file locking for persistence
- ProcessingController: Uses threading locks for session management
- StatusManager: Uses RLock for subscription management

## Error Handling

Interfaces provide clear error messages and graceful degradation:

- Invalid configurations are rejected with detailed validation errors
- Processing conflicts are prevented with clear error messages
- Failed subscribers are automatically cleaned up to prevent memory leaks
- File I/O errors fall back to in-memory operation

## Backward Compatibility

The interfaces maintain full compatibility with existing CLI usage patterns while providing the structure needed for UI integration. Existing code can gradually migrate to use these interfaces without breaking changes.

## Testing

Comprehensive test suites validate:

- Contract compliance (individual interface behavior)
- Integration (interfaces working together)
- Performance requirements
- Thread safety under concurrent access
- Backward compatibility with CLI patterns

Run tests with:
```bash
# All interface tests
poetry run pytest tests/test_*/test_*_interface*.py -v

# Integration tests
poetry run pytest tests/test_integration/ -v

# Performance tests
poetry run pytest tests/test_integration/test_performance.py -v

# Thread safety tests
poetry run pytest tests/test_integration/test_thread_safety.py -v
```</content>
<parameter name="filePath">/Users/juliocezar/Dev/CoupaDownloads_Refactoring/docs/core_interfaces.md