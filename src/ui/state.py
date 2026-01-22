# UI State data structures

"""
Data classes for tracking GUI component states.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OperationStatus(Enum):
    """Status of download operations"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class UIState:
    """
    Current state of GUI components and active operations.

    Fields:
        config_loaded: Whether valid configuration is loaded
        operation_running: Whether download operation is active
        start_button_enabled: Start button availability (computed)
        stop_button_enabled: Stop button availability (computed)
        status_text: Current status message
        progress_percentage: Operation progress (0-100)
        current_operation_status: Current operation status enum
    """
    config_loaded: bool = False
    operation_running: bool = False
    status_text: str = "Ready"
    progress_percentage: int = 0
    current_operation_status: OperationStatus = OperationStatus.NOT_STARTED

    @property
    def start_button_enabled(self) -> bool:
        """Start button is enabled when config is loaded and no operation is running"""
        return self.config_loaded and not self.operation_running

    @property
    def stop_button_enabled(self) -> bool:
        """Stop button is enabled when an operation is running"""
        return self.operation_running

    def update_operation_status(self, status: OperationStatus, message: Optional[str] = None):
        """
        Update operation status and related state.

        Args:
            status: New operation status
            message: Optional status message to display
        """
        self.current_operation_status = status

        # Update running state based on status
        self.operation_running = (status == OperationStatus.RUNNING)

        # Update status text if provided
        if message:
            self.status_text = message
        else:
            # Default messages based on status
            status_messages = {
                OperationStatus.NOT_STARTED: "Ready",
                OperationStatus.RUNNING: "Download in progress...",
                OperationStatus.COMPLETED: "Download completed successfully",
                OperationStatus.ERROR: "Download failed - check logs",
                OperationStatus.STOPPED: "Download stopped by user"
            }
            self.status_text = status_messages.get(status, "Unknown status")

        # Reset progress on completion or error
        if status in (OperationStatus.COMPLETED, OperationStatus.ERROR, OperationStatus.STOPPED):
            self.progress_percentage = 100 if status == OperationStatus.COMPLETED else 0

    def reset(self):
        """Reset UI state to initial values"""
        self.config_loaded = False
        self.operation_running = False
        self.status_text = "Ready"
        self.progress_percentage = 0
        self.current_operation_status = OperationStatus.NOT_STARTED