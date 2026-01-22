# Control panel widget

"""
Control panel for starting and stopping download operations.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import TYPE_CHECKING

from .state import OperationStatus

if TYPE_CHECKING:
    from .gui import CoupaDownloadsGUI

logger = logging.getLogger(__name__)


class ControlPanel(ttk.LabelFrame):
    """
    Control panel widget for download operations.

    Provides buttons to start, stop, and monitor download operations.
    """

    def __init__(self, parent: tk.Widget, gui: 'CoupaDownloadsGUI'):
        """
        Initialize the control panel.

        Args:
            parent: Parent widget
            gui: Main GUI instance
        """
        super().__init__(parent, text="Control", padding="8")
        self.gui = gui

        # Create UI components
        self._create_widgets()

    def _create_widgets(self):
        """Create the control panel widgets"""
        # Status and progress in one compact row
        status_frame = ttk.Frame(self)
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        status_frame.columnconfigure(1, weight=1)

        # Status indicator and text
        self.status_label = ttk.Label(
            status_frame,
            text="Ready",
            font=("Arial", 9, "bold"),
            foreground="green"
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=(0, 8))

        # Progress bar - compact
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=200
        )
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        # Control buttons - compact
        self.start_button = ttk.Button(
            status_frame,
            text="▶ Start",
            command=self._start_downloads,
            state="disabled",
            width=8
        )
        self.start_button.grid(row=0, column=2, padx=(0, 3))

        self.stop_button = ttk.Button(
            status_frame,
            text="⏹ Stop",
            command=self._stop_downloads,
            state="disabled",
            width=8
        )
        self.stop_button.grid(row=0, column=3)

        # Configure grid weights
        self.columnconfigure(0, weight=1)

    def update_button_states(self):
        """Update button states based on current operation status"""
        status = self.gui.ui_state.current_operation_status
        config_loaded = self.gui.ui_state.config_loaded

        if status == OperationStatus.RUNNING:
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.status_label.config(text="Running", foreground="blue")
        elif status == OperationStatus.STOPPED:
            self.start_button.config(state="normal" if config_loaded else "disabled")
            self.stop_button.config(state="disabled")
            self.status_label.config(text="Stopped", foreground="orange")
        elif status == OperationStatus.ERROR:
            self.start_button.config(state="normal" if config_loaded else "disabled")
            self.stop_button.config(state="disabled")
            self.status_label.config(text="Error", foreground="red")
        else:  # READY
            self.start_button.config(state="normal" if config_loaded else "disabled")
            self.stop_button.config(state="disabled")
            self.status_label.config(text="Ready", foreground="green")

        # Update progress bar
        self.progress_var.set(self.gui.ui_state.progress_percentage)

    def _start_downloads(self):
        """Start download operations"""
        # First check if configuration is loaded
        if not self.gui.ui_state.config_loaded:
            messagebox.showerror("Error", "No configuration loaded. Please configure settings first.")
            return

        # Validate configuration before starting
        if not self.gui.current_config:
            messagebox.showerror("Error", "Configuration not available.")
            return

        errors = self.gui.validate_configuration()
        if errors:
            error_text = "\n".join(errors)
            messagebox.showerror("Configuration Error", f"Cannot start downloads due to configuration errors:\n{error_text}")
            return

        # Confirm start with user
        result = messagebox.askyesno(
            "Start Downloads",
            f"Start downloading with {self.gui.current_config.worker_count} workers?\n"
            f"Input: {self.gui.current_config.csv_file_path}\n"
            f"Output: {self.gui.current_config.download_directory}"
        )

        if not result:
            return

        try:
            self.gui.start_downloads()
        except Exception as e:
            logger.error(f"Error starting downloads: {e}")
            messagebox.showerror("Error", f"Failed to start downloads: {e}")

    def _stop_downloads(self):
        """Stop download operations"""
        # Confirm stop with user
        result = messagebox.askyesno(
            "Stop Downloads",
            "Stop all download operations? This may leave partial downloads."
        )

        if not result:
            return

        try:
            self.gui.stop_downloads()
        except Exception as e:
            logger.error(f"Error stopping downloads: {e}")
            messagebox.showerror("Error", f"Failed to stop downloads: {e}")