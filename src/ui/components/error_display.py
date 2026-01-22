"""
Error Display Component

Provides specialized error display with recovery options for download operations.
Shows detailed error information, recovery suggestions, and action buttons.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Callable
import threading

from src.ui.data_model import ErrorInfo, UIFeedbackConfig
from src.ui.feedback_manager import FeedbackManager


class ErrorDisplay(ttk.LabelFrame):
    """
    Tkinter component for displaying errors with recovery options.

    Features:
    - Detailed error message display
    - Recovery suggestions with actionable steps
    - Retry and dismiss action buttons
    - Technical details toggle (if enabled)
    - Thread-safe updates
    """

    def __init__(self, parent: tk.Widget, config: UIFeedbackConfig):
        """
        Initialize the error display component.

        Args:
            parent: Parent Tkinter widget
            config: UI feedback configuration
        """
        super().__init__(parent, text="Error Details", padding="10")
        self.config = config
        self.current_error: Optional[ErrorInfo] = None

        # Callbacks
        self.on_retry: Optional[Callable[[ErrorInfo], None]] = None
        self.on_dismiss: Optional[Callable[[ErrorInfo], None]] = None

        # Thread safety
        self._lock = threading.Lock()
        self._update_pending = False

        # Create UI components
        self._create_widgets()

    def _on_error_update(self, error_info: ErrorInfo):
        """
        Callback for error updates from feedback manager.

        Args:
            error_info: New error information
        """
        self.display_error(error_info)

    def register_with_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Register this display with a feedback manager for automatic updates.

        Args:
            feedback_manager: FeedbackManager instance to register with
        """
        feedback_manager.register_callback("error_update", self._on_error_update)

    def unregister_from_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Unregister this display from a feedback manager.

        Args:
            feedback_manager: FeedbackManager instance to unregister from
        """
        feedback_manager.unregister_callback("error_update", self._on_error_update)

    def set_retry_callback(self, callback: Callable[[ErrorInfo], None]):
        """
        Set the callback for retry actions.

        Args:
            callback: Function to call when retry is requested
        """
        self.on_retry = callback

    def set_dismiss_callback(self, callback: Callable[[ErrorInfo], None]):
        """
        Set the callback for dismiss actions.

        Args:
            callback: Function to call when error is dismissed
        """
        self.on_dismiss = callback

    def _create_widgets(self):
        """Create and layout the error display widgets."""
        # Error type and timestamp
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        self.error_type_label = ttk.Label(
            header_frame,
            text="",
            font=("Arial", 10, "bold"),
            foreground="red"
        )
        self.error_type_label.pack(side=tk.LEFT)

        self.timestamp_label = ttk.Label(
            header_frame,
            text="",
            font=("Arial", 8),
            foreground="gray"
        )
        self.timestamp_label.pack(side=tk.RIGHT)

        # Error message
        ttk.Label(self, text="Error:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        self.error_message_label = ttk.Label(
            self,
            text="",
            wraplength=500,
            justify=tk.LEFT,
            font=("Arial", 9)
        )
        self.error_message_label.pack(fill=tk.X, pady=(5, 15))

        # Recovery suggestions
        ttk.Label(self, text="Recovery Suggestions:", font=("Arial", 9, "bold")).pack(anchor=tk.W)

        self.recovery_frame = ttk.Frame(self)
        self.recovery_frame.pack(fill=tk.X, pady=(5, 15))

        # Action buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.retry_button = ttk.Button(
            button_frame,
            text="Retry Operation",
            command=self._on_retry_click,
            state="disabled"
        )
        self.retry_button.pack(side=tk.LEFT, padx=(0, 10))

        self.contact_button = ttk.Button(
            button_frame,
            text="Contact Support",
            command=self._on_contact_support,
            state="disabled"
        )
        self.contact_button.pack(side=tk.LEFT, padx=(0, 10))

        self.dismiss_button = ttk.Button(
            button_frame,
            text="Dismiss",
            command=self._on_dismiss_click
        )
        self.dismiss_button.pack(side=tk.RIGHT)

        # Technical details (if enabled)
        if self.config.show_technical_details:
            self._create_technical_details()

    def _create_technical_details(self):
        """Create the technical details section."""
        self.tech_frame = ttk.LabelFrame(self, text="Technical Details", padding="5")

        self.tech_text = tk.Text(
            self.tech_frame,
            height=6,
            width=60,
            state="disabled",
            wrap=tk.WORD,
            font=("Consolas", 8)
        )
        self.tech_text.pack(fill=tk.BOTH, expand=True)

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
        """Update the UI components with current error data."""
        with self._lock:
            self._update_pending = False

            if self.current_error is None:
                # Hide error display content
                self.pack_forget()
                return

            # Show error display
            if not self.winfo_ismapped():
                self.pack(fill=tk.X, pady=(10, 0))

            error = self.current_error

            # Update header
            self.error_type_label.config(text=f"Error: {error.error_type.value.replace('_', ' ').title()}")
            self.timestamp_label.config(text=error.timestamp.strftime("%H:%M:%S"))

            # Update error message
            self.error_message_label.config(text=error.user_message)

            # Update recovery suggestions
            self._update_recovery_suggestions(error.recovery_suggestions)

            # Update action buttons
            self.retry_button.config(state="normal" if error.retry_possible else "disabled")
            self.contact_button.config(state="normal" if error.contact_support else "disabled")

            # Update technical details
            if self.config.show_technical_details and hasattr(self, 'tech_frame'):
                self._update_technical_details(error.technical_details)

    def _update_recovery_suggestions(self, suggestions: List[str]):
        """Update the recovery suggestions display."""
        # Clear existing suggestions
        for widget in self.recovery_frame.winfo_children():
            widget.destroy()

        if not suggestions:
            ttk.Label(
                self.recovery_frame,
                text="No specific recovery suggestions available.",
                font=("Arial", 9),
                foreground="gray"
            ).pack(anchor=tk.W)
            return

        # Add numbered suggestions
        for i, suggestion in enumerate(suggestions, 1):
            suggestion_frame = ttk.Frame(self.recovery_frame)
            suggestion_frame.pack(fill=tk.X, pady=(0, 3))

            # Number label
            ttk.Label(
                suggestion_frame,
                text=f"{i}.",
                font=("Arial", 9, "bold"),
                width=3,
                anchor=tk.W
            ).pack(side=tk.LEFT)

            # Suggestion text
            ttk.Label(
                suggestion_frame,
                text=suggestion,
                font=("Arial", 9),
                wraplength=450,
                justify=tk.LEFT
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _update_technical_details(self, technical_details: Optional[str]):
        """Update the technical details display."""
        if not hasattr(self, 'tech_text'):
            return

        self.tech_text.config(state="normal")
        self.tech_text.delete(1.0, tk.END)

        if technical_details:
            self.tech_text.insert(tk.END, technical_details)
            if not self.tech_frame.winfo_ismapped():
                self.tech_frame.pack(fill=tk.X, pady=(10, 0))
        else:
            if self.tech_frame.winfo_ismapped():
                self.tech_frame.pack_forget()

        self.tech_text.config(state="disabled")

    def _on_retry_click(self):
        """Handle retry button click."""
        if self.current_error and self.on_retry:
            self.on_retry(self.current_error)

    def _on_contact_support(self):
        """Handle contact support button click."""
        if self.current_error and self.current_error.contact_support:
            # Show contact information
            contact_info = "For technical support, please contact:\n\n"
            contact_info += "• Check the application logs for detailed error information\n"
            contact_info += "• Include the error type and timestamp when reporting\n"
            contact_info += "• Provide steps to reproduce the issue"

            messagebox.showinfo("Contact Support", contact_info)

    def _on_dismiss_click(self):
        """Handle dismiss button click."""
        if self.current_error and self.on_dismiss:
            self.on_dismiss(self.current_error)

        # Clear the error display
        self.clear_error()

    def clear_error(self):
        """Clear the current error display."""
        with self._lock:
            self.current_error = None
            self._update_display()

    def reset(self):
        """Reset the error display to initial state."""
        with self._lock:
            self.current_error = None
            self._update_display()

    def destroy(self):
        """Clean up the component."""
        super().destroy()


class ErrorDisplayManager:
    """
    Manager for error display components.

    Handles creation, updates, and lifecycle of error displays.
    Integrates with the feedback manager for automatic updates.
    """

    def __init__(self, config: UIFeedbackConfig):
        """
        Initialize the error display manager.

        Args:
            config: UI feedback configuration
        """
        self.config = config
        self.displays = []
        self._lock = threading.Lock()

    def create_display(self, parent: tk.Widget) -> ErrorDisplay:
        """
        Create a new error display component.

        Args:
            parent: Parent Tkinter widget

        Returns:
            ErrorDisplay: New error display instance
        """
        display = ErrorDisplay(parent, self.config)
        with self._lock:
            self.displays.append(display)
        return display

    def broadcast_error(self, error: ErrorInfo):
        """
        Broadcast an error to all displays.

        Args:
            error: Error information to broadcast
        """
        with self._lock:
            for display in self.displays[:]:  # Copy list to avoid modification during iteration
                try:
                    display.display_error(error)
                except Exception as e:
                    # Log error but continue with other displays
                    print(f"Error updating error display: {e}")

    def clear_all_errors(self):
        """Clear errors from all displays."""
        with self._lock:
            for display in self.displays[:]:
                try:
                    display.clear_error()
                except Exception as e:
                    print(f"Error clearing error display: {e}")

    def reset_all_displays(self):
        """Reset all error displays to initial state."""
        with self._lock:
            for display in self.displays[:]:
                try:
                    display.reset()
                except Exception as e:
                    print(f"Error resetting error display: {e}")

    def remove_display(self, display: ErrorDisplay):
        """
        Remove an error display from management.

        Args:
            display: Display to remove
        """
        with self._lock:
            if display in self.displays:
                self.displays.remove(display)

    def register_all_with_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Register all displays with a feedback manager.

        Args:
            feedback_manager: FeedbackManager instance to register with
        """
        with self._lock:
            for display in self.displays:
                try:
                    display.register_with_feedback_manager(feedback_manager)
                except Exception as e:
                    print(f"Error registering error display: {e}")

    def unregister_all_from_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Unregister all displays from a feedback manager.

        Args:
            feedback_manager: FeedbackManager instance to unregister from
        """
        with self._lock:
            for display in self.displays:
                try:
                    display.unregister_from_feedback_manager(feedback_manager)
                except Exception as e:
                    print(f"Error unregistering error display: {e}")

    def set_retry_callback_all(self, callback: Callable[[ErrorInfo], None]):
        """
        Set retry callback for all displays.

        Args:
            callback: Retry callback function
        """
        with self._lock:
            for display in self.displays:
                display.set_retry_callback(callback)

    def set_dismiss_callback_all(self, callback: Callable[[ErrorInfo], None]):
        """
        Set dismiss callback for all displays.

        Args:
            callback: Dismiss callback function
        """
        with self._lock:
            for display in self.displays:
                display.set_dismiss_callback(callback)