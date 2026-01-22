# Data Model: Enhanced UI Feedback

**Branch**: `008-enhanced-ui-feedback` | **Date**: 2025-01-29 | **Spec**: [specs/008-enhanced-ui-feedback/spec.md](specs/008-enhanced-ui-feedback/spec.md)
**Phase**: 1 (Design) - Data structures and relationships

## Overview

This document defines the data structures and models required for the enhanced UI feedback system in the CoupaDownloads application.

## Core Data Structures

### ProgressData

Represents download progress information for real-time display.

```python
@dataclass
class ProgressData:
    """Download progress tracking data."""
    total_files: int = 0
    completed_files: int = 0
    current_file: Optional[str] = None
    current_file_size: Optional[int] = None
    bytes_downloaded: int = 0
    total_bytes: int = 0
    start_time: Optional[datetime] = None
    estimated_time_remaining: Optional[timedelta] = None
    download_speed: Optional[float] = None  # bytes per second

    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.completed_files / self.total_files) * 100.0

    @property
    def current_file_progress(self) -> float:
        """Calculate current file download progress."""
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_downloaded / self.total_bytes) * 100.0
```

### StatusMessage

Represents status updates and messages for user feedback.

```python
@dataclass
class StatusMessage:
    """Status message for UI display."""
    message_type: StatusType
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Optional[str] = None
    actionable: bool = False
    action_label: Optional[str] = None

enum StatusType:
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"
```

### ErrorInfo

Detailed error information for user-friendly display.

```python
@dataclass
class ErrorInfo:
    """Error information with user-friendly details."""
    error_type: ErrorType
    user_message: str
    technical_details: Optional[str] = None
    recovery_suggestions: List[str] = field(default_factory=list)
    contact_support: bool = False
    retry_possible: bool = True
    timestamp: datetime = field(default_factory=datetime.now)

enum ErrorType:
    NETWORK_ERROR = "network"
    AUTHENTICATION_ERROR = "auth"
    FILE_SYSTEM_ERROR = "filesystem"
    CONFIGURATION_ERROR = "config"
    VALIDATION_ERROR = "validation"
    UNKNOWN_ERROR = "unknown"
```

### DownloadStatistics

Comprehensive statistics for download operations.

```python
@dataclass
class DownloadStatistics:
    """Download operation statistics."""
    total_files: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    total_bytes_downloaded: int = 0
    average_file_size: float = 0.0
    total_duration: Optional[timedelta] = None
    average_speed: Optional[float] = None  # bytes per second
    peak_speed: Optional[float] = None     # bytes per second
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.successful_downloads / self.total_files) * 100.0

    @property
    def formatted_duration(self) -> str:
        """Format duration for display."""
        if not self.total_duration:
            return "N/A"
        return str(self.total_duration).split('.')[0]  # Remove microseconds
```

## Component State Models

### FeedbackManagerState

Central state management for the feedback system.

```python
@dataclass
class FeedbackManagerState:
    """Central state for feedback management."""
    progress_data: ProgressData = field(default_factory=ProgressData)
    current_status: Optional[StatusMessage] = None
    statistics: DownloadStatistics = field(default_factory=DownloadStatistics)
    error_history: List[ErrorInfo] = field(default_factory=list)
    is_active: bool = False
    last_update: Optional[datetime] = None
```

### UIComponentState

Base state for individual UI components.

```python
@dataclass
class UIComponentState:
    """Base state for UI components."""
    is_visible: bool = True
    is_enabled: bool = True
    last_updated: Optional[datetime] = None
    error_state: bool = False
```

## Message Queue System

### FeedbackMessage

Messages passed between threads for UI updates.

```python
@dataclass
class FeedbackMessage:
    """Thread-safe message for UI updates."""
    message_type: FeedbackMessageType
    data: Any  # Flexible data payload
    timestamp: datetime = field(default_factory=datetime.now)
    priority: MessagePriority = MessagePriority.NORMAL

enum FeedbackMessageType:
    PROGRESS_UPDATE = "progress_update"
    STATUS_CHANGE = "status_change"
    ERROR_OCCURRED = "error_occurred"
    STATISTICS_UPDATE = "statistics_update"
    OPERATION_START = "operation_start"
    OPERATION_COMPLETE = "operation_complete"

enum MessagePriority:
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
```

## Configuration Models

### UIFeedbackConfig

Configuration for UI feedback behavior.

```python
@dataclass
class UIFeedbackConfig:
    """Configuration for UI feedback features."""
    enable_progress_bars: bool = True
    enable_detailed_status: bool = True
    enable_statistics: bool = True
    enable_error_recovery: bool = True
    update_frequency_ms: int = 100  # Minimum update interval
    max_error_history: int = 10
    show_technical_details: bool = False
    enable_animations: bool = True
    theme: UITheme = UITheme.DEFAULT

enum UITheme:
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
```

## Data Flow Diagrams

### Progress Update Flow

```
Download Thread → ProgressData → FeedbackMessage → UI Queue → ProgressDisplay Component
```

### Status Message Flow

```
Core System → StatusMessage → FeedbackManager → UI Component Update
```

### Error Handling Flow

```
Error Occurs → ErrorInfo → ErrorDisplay Component → User Action → Recovery Logic
```

## Validation Rules

### ProgressData Validation

- `total_files` must be >= 0
- `completed_files` must be <= `total_files`
- `progress_percentage` must be between 0.0 and 100.0
- `start_time` must be before current time if set

### StatusMessage Validation

- `title` and `message` must not be empty
- `timestamp` must not be in the future
- `action_label` required if `actionable` is True

### ErrorInfo Validation

- `user_message` must be user-friendly (no technical jargon)
- `recovery_suggestions` should contain actionable steps
- `technical_details` should only be shown if configured

## Thread Safety Considerations

### Shared Data Access

- All data structures must be accessed through thread-safe mechanisms
- Use locks for complex updates spanning multiple fields
- Prefer immutable updates where possible

### Message Queue Implementation

- Use `queue.Queue` for thread-safe message passing
- Implement proper cleanup on application shutdown
- Handle queue overflow gracefully

## Persistence Requirements

### Configuration Persistence

- `UIFeedbackConfig` should be saved to user configuration file
- Load on application startup
- Validate configuration on load

### Statistics Persistence (Optional)

- `DownloadStatistics` could be saved for historical tracking
- Consider user privacy implications
- Implement cleanup for old statistics

## Implementation Notes

### Python Type Hints

All data structures use proper type hints for IDE support and runtime validation.

### Dataclass Usage

Using `@dataclass` for automatic `__init__`, `__repr__`, and comparison methods.

### Enum Definitions

Using enums for type safety and code clarity.

### Property Methods

Calculated properties for derived values (progress percentages, formatted durations).

This data model provides a solid foundation for implementing the enhanced UI feedback features while maintaining thread safety and extensibility.