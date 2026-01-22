"""
Enhanced Tab model with lifecycle tracking.

This module provides the Tab data model with support for:
- Browser tab lifecycle management
- PO processing coordination
- State tracking and transitions
- Resource cleanup
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


class TabStatus(Enum):
    """Tab processing status enumeration."""
    OPENING = "opening"
    LOADING = "loading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"
    FAILED = "failed"


@dataclass
class Tab:
    """
    Enhanced Tab model with lifecycle tracking.
    
    Represents a short-lived browser tab for individual PO processing
    within a persistent browser session.
    """
    
    # Core identification
    window_handle: str = ""
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    
    # PO processing
    po_number: str = ""
    
    # Lifecycle management
    status: TabStatus = TabStatus.OPENING
    creation_time: datetime = field(default_factory=datetime.now)
    completion_time: Optional[datetime] = None
    
    # Error tracking
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        """Validate tab configuration after initialization."""
        if not self.task_id:
            raise ValueError("Task ID cannot be empty")
        
        # Note: po_number can be empty at creation time and will be set later
        # Only validate when status moves beyond OPENING
    
    def assign_po(self, po_number: str):
        """Assign PO number to tab and validate."""
        if not po_number:
            raise ValueError("PO number cannot be empty")
        self.po_number = po_number
        if self.status == TabStatus.OPENING:
            self.status = TabStatus.LOADING
    
    def mark_completed(self, success: bool = True):
        """Mark tab processing as completed."""
        self.completion_time = datetime.now()
        self.status = TabStatus.COMPLETED if success else TabStatus.FAILED
    
    def mark_error(self, error_message: str):
        """Mark tab as having an error."""
        self.status = TabStatus.ERROR
        self.error_message = error_message
    
    def get_processing_time(self) -> float:
        """Get total processing time in seconds."""
        end_time = self.completion_time or datetime.now()
        return (end_time - self.creation_time).total_seconds()
    
    def to_dict(self) -> dict:
        """Convert tab to dictionary representation."""
        return {
            'window_handle': self.window_handle,
            'task_id': self.task_id,
            'po_number': self.po_number,
            'status': self.status.value,
            'creation_time': self.creation_time.isoformat(),
            'completion_time': self.completion_time.isoformat() if self.completion_time else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'processing_time_seconds': self.get_processing_time()
        }
