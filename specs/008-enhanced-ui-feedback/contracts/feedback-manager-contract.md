# Contract: Feedback Manager Interface

**Location**: `src/gui/feedback_manager.py`
**Purpose**: Define the interface for central feedback coordination

## Interface Definition

```python
from abc import ABC, abstractmethod
from typing import Callable, Any, Optional
from datetime import datetime
from .data_model import (
    ProgressData,
    StatusMessage,
    ErrorInfo,
    DownloadStatistics,
    FeedbackMessage,
    UIFeedbackConfig
)

class FeedbackManagerInterface(ABC):
    """Interface for feedback management and coordination."""

    @abstractmethod
    def initialize(self, config: UIFeedbackConfig) -> None:
        """Initialize the feedback manager with configuration."""
        pass

    @abstractmethod
    def start_operation(self, operation_name: str) -> None:
        """Signal the start of a download operation."""
        pass

    @abstractmethod
    def update_progress(self, progress_data: ProgressData) -> None:
        """Update progress information."""
        pass

    @abstractmethod
    def update_status(self, status: StatusMessage) -> None:
        """Update current status message."""
        pass

    @abstractmethod
    def report_error(self, error: ErrorInfo) -> None:
        """Report an error for display."""
        pass

    @abstractmethod
    def update_statistics(self, stats: DownloadStatistics) -> None:
        """Update download statistics."""
        pass

    @abstractmethod
    def complete_operation(self, success: bool = True) -> None:
        """Signal completion of the operation."""
        pass

    @abstractmethod
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register a callback for specific events."""
        pass

    @abstractmethod
    def unregister_callback(self, event_type: str, callback: Callable) -> None:
        """Unregister a callback."""
        pass

    @abstractmethod
    def get_current_state(self) -> dict:
        """Get current feedback state snapshot."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Clean shutdown of feedback manager."""
        pass
```

## Contract Requirements

### Thread Safety
- All methods must be thread-safe for background thread calls
- Use appropriate locking mechanisms for shared state
- Queue-based message passing for UI updates

### Error Handling
- Methods should not raise exceptions that crash the calling thread
- Log errors internally and continue operation
- Provide error recovery mechanisms

### Performance
- Updates should complete within 50ms
- Memory usage should not exceed 10MB for typical operations
- Support high-frequency updates without degradation

### Callback System
- Support multiple callbacks per event type
- Callbacks should be called asynchronously to avoid blocking
- Provide cleanup for dead callbacks

## Implementation Notes

### Message Queue
- Use `queue.Queue` for thread-safe message passing
- Implement proper queue size limits
- Handle queue overflow gracefully

### State Management
- Maintain consistent internal state
- Provide atomic state updates
- Support state serialization for debugging

### Event Types
- `progress_updated`: Progress data changed
- `status_changed`: Status message updated
- `error_occurred`: New error reported
- `statistics_updated`: Statistics changed
- `operation_started`: Operation began
- `operation_completed`: Operation finished