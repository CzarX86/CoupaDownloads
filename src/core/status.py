# Status message data structures

"""
Data classes for real-time status updates and progress reporting.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class StatusLevel(Enum):
    """Severity levels for status messages"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class StatusMessage:
    """
    Real-time status updates about download progress and system state.

    Fields:
        timestamp: When message was created (auto-generated)
        level: Message severity level
        message: Human-readable status text (max 500 chars)
        operation_id: Identifier for related operation (optional)
        progress: Associated progress percentage (0-100, optional)
    """
    timestamp: datetime
    level: StatusLevel
    message: str
    operation_id: Optional[str] = None
    progress: Optional[int] = None

    def __post_init__(self):
        """Validate message after initialization"""
        if not self.message or not self.message.strip():
            raise ValueError("Message cannot be empty")

        if len(self.message) > 500:
            raise ValueError("Message cannot exceed 500 characters")

        if self.progress is not None and (self.progress < 0 or self.progress > 100):
            raise ValueError("Progress must be between 0 and 100")

    @classmethod
    def info(cls, message: str, operation_id: Optional[str] = None, progress: Optional[int] = None) -> 'StatusMessage':
        """Create an info-level status message"""
        return cls(
            timestamp=datetime.now(),
            level=StatusLevel.INFO,
            message=message,
            operation_id=operation_id,
            progress=progress
        )

    @classmethod
    def warning(cls, message: str, operation_id: Optional[str] = None, progress: Optional[int] = None) -> 'StatusMessage':
        """Create a warning-level status message"""
        return cls(
            timestamp=datetime.now(),
            level=StatusLevel.WARNING,
            message=message,
            operation_id=operation_id,
            progress=progress
        )

    @classmethod
    def error(cls, message: str, operation_id: Optional[str] = None, progress: Optional[int] = None) -> 'StatusMessage':
        """Create an error-level status message"""
        return cls(
            timestamp=datetime.now(),
            level=StatusLevel.ERROR,
            message=message,
            operation_id=operation_id,
            progress=progress
        )

    @classmethod
    def success(cls, message: str, operation_id: Optional[str] = None, progress: Optional[int] = None) -> 'StatusMessage':
        """Create a success-level status message"""
        return cls(
            timestamp=datetime.now(),
            level=StatusLevel.SUCCESS,
            message=message,
            operation_id=operation_id,
            progress=progress
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the message
        """
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'message': self.message,
            'operation_id': self.operation_id,
            'progress': self.progress
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'StatusMessage':
        """
        Create from dictionary representation.

        Args:
            data: Dictionary with message data

        Returns:
            StatusMessage instance
        """
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            level=StatusLevel(data['level']),
            message=data['message'],
            operation_id=data.get('operation_id'),
            progress=data.get('progress')
        )