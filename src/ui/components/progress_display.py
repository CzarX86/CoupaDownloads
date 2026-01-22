"""
Progress Display Component

Provides visual progress indicators for download operations.
Displays progress bars, completion percentages, and current file information.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
import threading
import time

from src.ui.data_model import ProgressData, UIFeedbackConfig
from src.ui.feedback_manager import FeedbackManager


class ProgressDisplay(ttk.Frame):
    """
    Tkinter component for displaying download progress.

    Features:
    - Progress bar with percentage completion
    - Current file being processed
    - Files completed / total files
    - Smooth progress updates
    - Thread-safe updates
    """

    def __init__(self, parent: tk.Widget, config: UIFeedbackConfig):
        """
        Initialize the progress display component.

        Args:
            parent: Parent Tkinter widget
            config: UI feedback configuration
        """
        super().__init__(parent, padding="5")
        self.config = config
        self.current_progress: Optional[ProgressData] = None

        # Thread safety
        self._lock = threading.Lock()
        self._update_pending = False

        # Create UI components
        self._create_widgets()

    def _on_progress_update(self, progress_data: ProgressData):
        """
        Callback for progress updates from feedback manager.

        Args:
            progress_data: New progress information
        """
        self.update_progress(progress_data)

    def register_with_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Register this display with a feedback manager for automatic updates.

        Args:
            feedback_manager: FeedbackManager instance to register with
        """
        feedback_manager.register_callback("progress_update", self._on_progress_update)

    def unregister_from_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Unregister this display from a feedback manager.

        Args:
            feedback_manager: FeedbackManager instance to unregister from
        """
        feedback_manager.unregister_callback("progress_update", self._on_progress_update)

    def _create_widgets(self):
        """Create and layout the progress display widgets."""
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self,
            variable=self.progress_var,
            maximum=100.0,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        # Status labels frame
        labels_frame = ttk.Frame(self)
        labels_frame.pack(fill=tk.X)

        # Current file label
        self.current_file_label = ttk.Label(
            labels_frame,
            text="Current file: None",
            anchor=tk.W
        )
        self.current_file_label.pack(fill=tk.X, pady=(0, 2))

        # Progress text label
        self.progress_text_label = ttk.Label(
            labels_frame,
            text="0 / 0 files completed (0%)",
            anchor=tk.W
        )
        self.progress_text_label.pack(fill=tk.X)

    def update_progress(self, progress_data: ProgressData):
        """
        Update the progress display with new progress data.

        Args:
            progress_data: New progress information
        """
        with self._lock:
            self.current_progress = progress_data
            if not self._update_pending:
                self._update_pending = True
                # Schedule UI update on main thread
                self.after(0, self._update_display)

    def _update_display(self):
        """Update the UI components with current progress data."""
        with self._lock:
            self._update_pending = False

            if self.current_progress is None:
                # No progress data yet
                self.progress_var.set(0)
                self.current_file_label.config(text="Current file: None")
                self.progress_text_label.config(text="0 / 0 files completed (0%)")
                return

            progress = self.current_progress

            # Update progress bar
            self.progress_var.set(progress.progress_percentage)

            # Update current file
            current_file = progress.current_file or "Unknown"
            self.current_file_label.config(text=f"Current file: {current_file}")

            # Update progress text
            completed = progress.completed_files
            total = progress.total_files
            percentage = progress.progress_percentage

            if total > 0:
                progress_text = f"{completed} / {total} files completed ({percentage:.1f}%)"
            else:
                progress_text = "Initializing..."

            self.progress_text_label.config(text=progress_text)

    def reset(self):
        """Reset the progress display to initial state."""
        with self._lock:
            self.current_progress = None
            self._update_display()

    def destroy(self):
        """Clean up the component."""
        super().destroy()


class ProgressDisplayManager:
    """
    Manager for progress display components.

    Handles creation, updates, and lifecycle of progress displays.
    Integrates with the feedback manager for automatic updates.
    """

    def __init__(self, config: UIFeedbackConfig):
        """
        Initialize the progress display manager.

        Args:
            config: UI feedback configuration
        """
        self.config = config
        self.displays = []
        self._lock = threading.Lock()

    def create_display(self, parent: tk.Widget) -> ProgressDisplay:
        """
        Create a new progress display component.

        Args:
            parent: Parent Tkinter widget

        Returns:
            ProgressDisplay: New progress display instance
        """
        display = ProgressDisplay(parent, self.config)
        with self._lock:
            self.displays.append(display)
        return display

    def update_all_displays(self, progress_data: ProgressData):
        """
        Update all registered progress displays.

        Args:
            progress_data: New progress information
        """
        with self._lock:
            for display in self.displays[:]:  # Copy list to avoid modification during iteration
                try:
                    display.update_progress(progress_data)
                except Exception as e:
                    # Log error but continue with other displays
                    print(f"Error updating progress display: {e}")

    def reset_all_displays(self):
        """Reset all progress displays to initial state."""
        with self._lock:
            for display in self.displays[:]:
                try:
                    display.reset()
                except Exception as e:
                    print(f"Error resetting progress display: {e}")

    def remove_display(self, display: ProgressDisplay):
        """
        Remove a progress display from management.

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
                    print(f"Error registering progress display: {e}")

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
                    print(f"Error unregistering progress display: {e}")