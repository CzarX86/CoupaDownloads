# Status display widget

"""
Status display widget for showing operation progress and messages.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
from typing import TYPE_CHECKING

from .data_model import StatusMessage, UIFeedbackConfig
from .components.status_panel import StatusPanel

if TYPE_CHECKING:
    from .gui import CoupaDownloadsGUI

logger = logging.getLogger(__name__)


class StatusDisplay(ttk.Frame):
    """
    Status display widget that integrates StatusPanel and ErrorDisplay.

    Shows current operation status, progress, messages, and errors.
    """

    def __init__(self, parent: tk.Widget, gui: 'CoupaDownloadsGUI'):
        """
        Initialize the status display.

        Args:
            parent: Parent widget
            gui: Main GUI instance
        """
        super().__init__(parent)
        self.gui = gui

        # Configuration
        self.config = UIFeedbackConfig()

        # Create UI components
        self._create_widgets()

    def _create_widgets(self):
        """Create the status display widgets"""
        # Create status panel
        self.status_panel = StatusPanel(self, self.config)
        self.status_panel.frame.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights for proper resizing
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def update_status(self, message):
        """
        Update status display with new message.

        Args:
            message: Status message to display (can be old or new format)
        """
        # Convert old StatusMessage format to new format if needed
        if hasattr(message, 'level') and hasattr(message, 'message'):
            # Old format - convert to new StatusMessage
            from .data_model import StatusMessage as NewStatusMessage, StatusType
            # Map old level to new message_type
            level_mapping = {
                "info": StatusType.INFO,
                "success": StatusType.SUCCESS,
                "warning": StatusType.WARNING,
                "error": StatusType.ERROR,
                "progress": StatusType.PROGRESS
            }
            message_type = level_mapping.get(message.level.value, StatusType.INFO)

            new_message = NewStatusMessage(
                message_type=message_type,
                title=message.level.value.title(),
                message=message.message,
                timestamp=message.timestamp
            )
            self.status_panel.add_status_message(new_message)
        else:
            # Already new format
            self.status_panel.add_status_message(message)

    def update_display(self):
        """Update the entire display based on current GUI state"""
        # Update status from GUI state
        status_text = f"Current Status: {self.gui.ui_state.status_text}"

        # Create a status message for the current state
        from .data_model import StatusMessage, StatusType
        state_message = StatusMessage(
            message_type=StatusType.INFO,
            title=self.gui.ui_state.status_text,
            message=f"Progress: {self.gui.ui_state.progress_percentage}%"
        )
        self.status_panel.add_status_message(state_message)

    def reset(self):
        """Reset the status display to initial state"""
        if hasattr(self, 'status_panel'):
            self.status_panel.reset()

    def destroy(self):
        """Clean up the component"""
        if hasattr(self, 'status_panel'):
            self.status_panel.destroy()
        super().destroy()