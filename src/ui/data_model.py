"""
Data Model: Enhanced UI Feedback

This module defines the data structures and models required for the enhanced UI feedback system
in the CoupaDownloads application.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any


class StatusType(Enum):
    """Types of status messages."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"


class ErrorType(Enum):
    """Types of errors that can occur."""
    NETWORK_ERROR = "network"
    AUTHENTICATION_ERROR = "auth"
    FILE_SYSTEM_ERROR = "filesystem"
    CONFIGURATION_ERROR = "config"
    VALIDATION_ERROR = "validation"
    UNKNOWN_ERROR = "unknown"


class FeedbackMessageType(Enum):
    """Types of feedback messages for thread communication."""
    PROGRESS_UPDATE = "progress_update"
    STATUS_CHANGE = "status_change"
    ERROR_OCCURRED = "error_occurred"
    STATISTICS_UPDATE = "statistics_update"
    OPERATION_START = "operation_start"
    OPERATION_COMPLETE = "operation_complete"


class MessagePriority(Enum):
    """Priority levels for feedback messages."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class UITheme(Enum):
    """Available UI themes."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"


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


@dataclass
class FeedbackManagerState:
    """Central state for feedback management."""
    progress_data: ProgressData = field(default_factory=ProgressData)
    current_status: Optional[StatusMessage] = None
    statistics: DownloadStatistics = field(default_factory=DownloadStatistics)
    error_history: List[ErrorInfo] = field(default_factory=list)
    is_active: bool = False
    last_update: Optional[datetime] = None


@dataclass
class UIComponentState:
    """Base state for UI components."""
    is_visible: bool = True
    is_enabled: bool = True
    last_updated: Optional[datetime] = None
    error_state: bool = False


@dataclass
class FeedbackMessage:
    """Thread-safe message for UI updates."""
    message_type: FeedbackMessageType
    data: Any  # Flexible data payload
    timestamp: datetime = field(default_factory=datetime.now)
    priority: MessagePriority = MessagePriority.NORMAL


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