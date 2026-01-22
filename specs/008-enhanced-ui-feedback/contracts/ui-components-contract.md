# Contract: UI Component Interface

**Location**: `src/gui/components/base_component.py`
**Purpose**: Define the base interface for all UI feedback components

## Interface Definition

```python
from abc import ABC, abstractmethod
from typing import Any, Optional
import tkinter as tk
from ..data_model import UIComponentState

class UIComponentInterface(ABC):
    """Base interface for UI feedback components."""

    @abstractmethod
    def __init__(self, parent: tk.Widget, feedback_manager: 'FeedbackManagerInterface'):
        """Initialize component with parent widget and feedback manager."""
        self.parent = parent
        self.feedback_manager = feedback_manager
        self.state = UIComponentState()
        self.frame: Optional[tk.Frame] = None

    @abstractmethod
    def create_widgets(self) -> tk.Frame:
        """Create and return the main component frame."""
        pass

    @abstractmethod
    def update_display(self, data: Any) -> None:
        """Update component display with new data."""
        pass

    @abstractmethod
    def show_error(self, error_message: str) -> None:
        """Display an error state in the component."""
        pass

    @abstractmethod
    def clear_error(self) -> None:
        """Clear error state and return to normal display."""
        pass

    @abstractmethod
    def enable(self) -> None:
        """Enable the component for user interaction."""
        pass

    @abstractmethod
    def disable(self) -> None:
        """Disable the component."""
        pass

    @abstractmethod
    def show(self) -> None:
        """Make the component visible."""
        pass

    @abstractmethod
    def hide(self) -> None:
        """Hide the component."""
        pass

    @abstractmethod
    def destroy(self) -> None:
        """Clean up component resources."""
        pass

    @abstractmethod
    def get_state(self) -> UIComponentState:
        """Get current component state."""
        return self.state

    @abstractmethod
    def set_state(self, state: UIComponentState) -> None:
        """Set component state."""
        pass
```

## Specific Component Contracts

### ProgressDisplay Contract

**Location**: `src/gui/components/progress_display.py`

```python
class ProgressDisplayInterface(UIComponentInterface):
    """Interface for progress display component."""

    @abstractmethod
    def set_progress(self, percentage: float, current_file: Optional[str] = None) -> None:
        """Set progress bar percentage and current file info."""
        pass

    @abstractmethod
    def set_indeterminate(self, indeterminate: bool = True) -> None:
        """Set progress bar to indeterminate mode."""
        pass

    @abstractmethod
    def reset_progress(self) -> None:
        """Reset progress to zero."""
        pass
```

### StatusPanel Contract

**Location**: `src/gui/components/status_panel.py`

```python
class StatusPanelInterface(UIComponentInterface):
    """Interface for status panel component."""

    @abstractmethod
    def set_status(self, message: str, message_type: str = "info") -> None:
        """Set status message with type."""
        pass

    @abstractmethod
    def append_message(self, message: str, message_type: str = "info") -> None:
        """Append message to status history."""
        pass

    @abstractmethod
    def clear_messages(self) -> None:
        """Clear all status messages."""
        pass

    @abstractmethod
    def set_max_messages(self, max_messages: int) -> None:
        """Set maximum number of messages to display."""
        pass
```

### ErrorDisplay Contract

**Location**: `src/gui/components/error_display.py`

```python
class ErrorDisplayInterface(UIComponentInterface):
    """Interface for error display component."""

    @abstractmethod
    def show_error(self, title: str, message: str,
                   recovery_steps: list[str] = None,
                   can_retry: bool = True) -> None:
        """Display error with recovery options."""
        pass

    @abstractmethod
    def hide_error(self) -> None:
        """Hide error display."""
        pass

    @abstractmethod
    def set_retry_callback(self, callback: Callable) -> None:
        """Set callback for retry action."""
        pass
```

### StatisticsPanel Contract

**Location**: `src/gui/components/statistics_panel.py`

```python
class StatisticsPanelInterface(UIComponentInterface):
    """Interface for statistics panel component."""

    @abstractmethod
    def update_statistics(self, stats: DownloadStatistics) -> None:
        """Update displayed statistics."""
        pass

    @abstractmethod
    def reset_statistics(self) -> None:
        """Reset all statistics to zero."""
        pass

    @abstractmethod
    def highlight_metric(self, metric_name: str) -> None:
        """Highlight a specific metric."""
        pass
```

## Contract Requirements

### Tkinter Integration
- All components must properly integrate with Tkinter event loop
- Use thread-safe update mechanisms (`after()` callbacks)
- Handle widget lifecycle properly

### Layout Requirements
- Components should be responsive to parent container resizing
- Use appropriate Tkinter geometry managers
- Support minimum and maximum size constraints

### Accessibility
- Components should support screen readers
- Keyboard navigation where appropriate
- High contrast color schemes

### Performance
- UI updates should be fast (< 50ms)
- No memory leaks during component lifecycle
- Efficient redraw handling

### Error Handling
- Graceful degradation on display errors
- Logging of component failures
- Recovery from invalid data

## Implementation Notes

### Base Component Class
- Provide default implementations for common methods
- Handle Tkinter widget creation and destruction
- Implement state management

### Thread Safety
- All UI updates must use `root.after()` for thread safety
- Queue-based communication with feedback manager
- Proper cleanup on component destruction

### Styling
- Consistent color scheme across components
- Configurable themes support
- Responsive to system font scaling