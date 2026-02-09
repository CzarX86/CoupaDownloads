"""
Status Panel Component

Provides detailed status messages and error display for download operations.
Shows current operation status, message history, and error information with recovery options.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Optional, List, Callable
import threading
from datetime import datetime

from src.ui.data_model import StatusMessage, ErrorInfo, UIFeedbackConfig
from src.ui.feedback_manager import FeedbackManager


class StatusPanel(ttk.LabelFrame):
    """
    Tkinter component for displaying status messages and errors.

    Features:
    - Real-time status message display
    - Message history with timestamps
    - Error display with recovery suggestions
    - Color-coded message types
    - Thread-safe updates
    - Scrollable message log
    """

    def __init__(self, parent: tk.Widget, config: UIFeedbackConfig):
        """
        Initialize the status panel component.

        Args:
            parent: Parent Tkinter widget
            config: UI feedback configuration
        """
        super().__init__(parent, text="Status & Messages", padding="10")
        self.config = config

        # Message history
        self.message_history: List[StatusMessage] = []
        self.current_error: Optional[ErrorInfo] = None

        # Thread safety
        self._lock = threading.Lock()
        self._update_pending = False

        # Create UI components
        self._create_widgets()

    def _on_status_update(self, status_message: StatusMessage):
        """
        Callback for status updates from feedback manager.

        Args:
            status_message: New status message
        """
        self.add_status_message(status_message)

    def _on_error_update(self, error_info: ErrorInfo):
        """
        Callback for error updates from feedback manager.

        Args:
            error_info: New error information
        """
        self.display_error(error_info)

    def register_with_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Register this panel with a feedback manager for automatic updates.

        Args:
            feedback_manager: FeedbackManager instance to register with
        """
        feedback_manager.register_callback("status_change", self._on_status_update)
        feedback_manager.register_callback("error_occurred", self._on_error_update)

    def unregister_from_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Unregister this panel from a feedback manager.

        Args:
            feedback_manager: FeedbackManager instance to unregister from
        """
        feedback_manager.unregister_callback("status_change", self._on_status_update)
        feedback_manager.unregister_callback("error_occurred", self._on_error_update)

    def _create_widgets(self):
        """Create and layout the status panel widgets."""
        # Current status section
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        # Status indicator and text
        self.status_indicator_label = ttk.Label(
            status_frame,
            text="●",
            font=("Arial", 12, "bold"),
            foreground="green"
        )
        self.status_indicator_label.pack(side=tk.LEFT, padx=(0, 5))

        self.status_text_label = ttk.Label(
            status_frame,
            text="Ready",
            font=("Arial", 10, "bold"),
            anchor=tk.W
        )
        self.status_text_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Message log section
        log_frame = ttk.LabelFrame(self, text="Message Log", padding="3")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Message text area - increased height for more messages
        self.message_text = scrolledtext.ScrolledText(
            log_frame,
            width=60,
            state="disabled",
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.message_text.pack(fill=tk.BOTH, expand=True)

        # Control buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X)

        self.clear_button = ttk.Button(
            button_frame,
            text="Clear Log",
            command=self.clear_message_log
        )
        self.clear_button.pack(side=tk.RIGHT)

        # Error display section (initially hidden)
        self._create_error_display()

    def _create_error_display(self):
        """Create the error display section."""
        self.error_frame = ttk.LabelFrame(self, text="Error Details", padding="10")

        # Error message
        self.error_message_label = ttk.Label(
            self.error_frame,
            text="",
            wraplength=400,
            justify=tk.LEFT
        )
        self.error_message_label.pack(fill=tk.X, pady=(0, 10))

        # Recovery suggestions
        ttk.Label(self.error_frame, text="Suggested Actions:", font=("Arial", 9, "bold")).pack(anchor=tk.W)

        self.recovery_text = tk.Text(
            self.error_frame,
            width=50,
            state="disabled",
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.recovery_text.pack(fill=tk.X, pady=(5, 10))

        # Action buttons
        action_frame = ttk.Frame(self.error_frame)
        action_frame.pack(fill=tk.X)

        self.retry_button = ttk.Button(
            action_frame,
            text="Retry",
            command=self._on_retry_action
        )
        self.retry_button.pack(side=tk.LEFT, padx=(0, 10))

        self.dismiss_button = ttk.Button(
            action_frame,
            text="Dismiss",
            command=self._dismiss_error
        )
        self.dismiss_button.pack(side=tk.RIGHT)

    def add_status_message(self, message: StatusMessage):
        """
        Add a status message to the display.

        Args:
            message: Status message to add
        """
        with self._lock:
            self.message_history.append(message)

            # Keep only last 100 messages
            if len(self.message_history) > 100:
                self.message_history = self.message_history[-100:]

            if not self._update_pending:
                self._update_pending = True
                # Schedule UI update on main thread
                self.after(0, self._update_display)

    def display_error(self, error: ErrorInfo):
        """
        Display an error with recovery options.

        Args:
            error: Error information to display
        """
        with self._lock:
            self.current_error = error
            if not self._update_pending:
                self._update_pending = True
                # Schedule UI update on main thread
                self.after(0, self._update_display)

    def _update_display(self):
        """Update the UI components with current data."""
        with self._lock:
            self._update_pending = False

            # Update status indicator and text
            self._update_status_display()

            # Update message log
            self._update_message_log()

            # Update error display
            self._update_error_display()

    def _update_status_display(self):
        """Update the status indicator and text."""
        if not self.message_history:
            self.status_indicator_label.config(text="●", foreground="gray")
            self.status_text_label.config(text="No status messages yet")
            return

        latest_message = self.message_history[-1]

        # Set indicator color based on message type
        if latest_message.message_type.value == "error":
            self.status_indicator_label.config(text="●", foreground="red")
        elif latest_message.message_type.value == "warning":
            self.status_indicator_label.config(text="●", foreground="orange")
        elif latest_message.message_type.value == "success":
            self.status_indicator_label.config(text="●", foreground="green")
        else:  # INFO or PROGRESS
            self.status_indicator_label.config(text="●", foreground="blue")

        # Set status text
        status_text = f"{latest_message.message_type.value.title()}: {latest_message.title}"
        if len(status_text) > 50:
            status_text = status_text[:47] + "..."

        self.status_text_label.config(text=status_text)

    def _update_message_log(self):
        """Update the message log display."""
        self.message_text.config(state="normal")
        self.message_text.delete(1.0, tk.END)

        for message in self.message_history[-50:]:  # Show last 50 messages
            timestamp = message.timestamp.strftime("%H:%M:%S")
            level_indicator = self._get_level_indicator(message.message_type.value)

            # Format message
            log_line = f"[{timestamp}] {level_indicator} {message.title}"
            if message.message:
                log_line += f" - {message.message}"

            log_line += "\n"

            # Insert with appropriate color
            start_pos = self.message_text.index(tk.END + "-1c")
            self.message_text.insert(tk.END, log_line)
            end_pos = self.message_text.index(tk.END + "-1c")

            # Apply color tags
            color = self._get_message_color(message.message_type.value)
            self.message_text.tag_add(f"color_{message.message_type.value}", start_pos, end_pos)
            self.message_text.tag_config(f"color_{message.message_type.value}", foreground=color)

        self.message_text.see(tk.END)  # Scroll to bottom
        self.message_text.config(state="disabled")

    def _get_level_indicator(self, level: str) -> str:
        """Get the indicator symbol for a message level."""
        indicators = {
            "error": "❌",
            "warning": "⚠️",
            "success": "✅",
            "info": "ℹ️",
            "progress": "⏳"
        }
        return indicators.get(level, "•")

    def _get_message_color(self, level: str) -> str:
        """Get the color for a message level."""
        colors = {
            "error": "red",
            "warning": "orange",
            "success": "green",
            "info": "blue",
            "progress": "purple"
        }
        return colors.get(level, "black")

    def _update_error_display(self):
        """Update the error display section."""
        if self.current_error is None:
            # Hide error display
            if self.error_frame.winfo_ismapped():
                self.error_frame.pack_forget()
            return

        # Show error display
        if not self.error_frame.winfo_ismapped():
            self.error_frame.pack(fill=tk.X, pady=(10, 0))

        error = self.current_error

        # Update error message
        self.error_message_label.config(text=error.user_message)

        # Update recovery suggestions
        self.recovery_text.config(state="normal")
        self.recovery_text.delete(1.0, tk.END)

        if error.recovery_suggestions:
            for i, suggestion in enumerate(error.recovery_suggestions, 1):
                self.recovery_text.insert(tk.END, f"{i}. {suggestion}\n")
        else:
            self.recovery_text.insert(tk.END, "No specific recovery suggestions available.")

        self.recovery_text.config(state="disabled")

        # Update action buttons
        self.retry_button.config(state="normal" if error.retry_possible else "disabled")

    def clear_message_log(self):
        """Clear the message log."""
        with self._lock:
            self.message_history.clear()
            self._update_display()

    def _on_retry_action(self):
        """Handle retry action button click."""
        if self.current_error and self.current_error.retry_possible:
            # Emit retry event (would be handled by feedback manager)
            print(f"Retry requested for error: {self.current_error.error_type}")
            # TODO: Integrate with feedback manager for retry logic

    def _dismiss_error(self):
        """Dismiss the current error display."""
        with self._lock:
            self.current_error = None
            self._update_display()

    def reset(self):
        """Reset the status panel to initial state."""
        with self._lock:
            self.message_history.clear()
            self.current_error = None
            self._update_display()

    def destroy(self):
        """Clean up the component."""
        super().destroy()


class StatusPanelManager:
    """
    Manager for status panel components.

    Handles creation, updates, and lifecycle of status panels.
    Integrates with the feedback manager for automatic updates.
    """

    def __init__(self, config: UIFeedbackConfig):
        """
        Initialize the status panel manager.

        Args:
            config: UI feedback configuration
        """
        self.config = config
        self.panels = []
        self._lock = threading.Lock()

    def create_panel(self, parent: tk.Widget) -> StatusPanel:
        """
        Create a new status panel component.

        Args:
            parent: Parent Tkinter widget

        Returns:
            StatusPanel: New status panel instance
        """
        panel = StatusPanel(parent, self.config)
        with self._lock:
            self.panels.append(panel)
        return panel

    def broadcast_status_message(self, message: StatusMessage):
        """
        Broadcast a status message to all panels.

        Args:
            message: Status message to broadcast
        """
        with self._lock:
            for panel in self.panels[:]:  # Copy list to avoid modification during iteration
                try:
                    panel.add_status_message(message)
                except Exception as e:
                    # Log error but continue with other panels
                    print(f"Error updating status panel: {e}")

    def broadcast_error(self, error: ErrorInfo):
        """
        Broadcast an error to all panels.

        Args:
            error: Error information to broadcast
        """
        with self._lock:
            for panel in self.panels[:]:
                try:
                    panel.display_error(error)
                except Exception as e:
                    print(f"Error displaying error in panel: {e}")

    def reset_all_panels(self):
        """Reset all status panels to initial state."""
        with self._lock:
            for panel in self.panels[:]:
                try:
                    panel.reset()
                except Exception as e:
                    print(f"Error resetting status panel: {e}")

    def remove_panel(self, panel: StatusPanel):
        """
        Remove a status panel from management.

        Args:
            panel: Panel to remove
        """
        with self._lock:
            if panel in self.panels:
                self.panels.remove(panel)

    def register_all_with_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Register all panels with a feedback manager.

        Args:
            feedback_manager: FeedbackManager instance to register with
        """
        with self._lock:
            for panel in self.panels:
                try:
                    panel.register_with_feedback_manager(feedback_manager)
                except Exception as e:
                    print(f"Error registering status panel: {e}")

    def unregister_all_from_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Unregister all panels from a feedback manager.

        Args:
            feedback_manager: FeedbackManager instance to unregister from
        """
        with self._lock:
            for panel in self.panels:
                try:
                    panel.unregister_from_feedback_manager(feedback_manager)
                except Exception as e:
                    print(f"Error unregistering status panel: {e}")