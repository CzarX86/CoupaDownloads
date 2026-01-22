# Configuration panel widget

"""
Configuration panel for the CoupaDownloads GUI.

This module provides a widget for configuring download settings
including input/output directories, credentials, and other options.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from typing import Optional, TYPE_CHECKING
from pathlib import Path

from ..core.config import ConfigurationSettings
from .dialogs import browse_directory, browse_file

if TYPE_CHECKING:
    from .gui import CoupaDownloadsGUI

logger = logging.getLogger(__name__)


class ConfigPanel(ttk.LabelFrame):
    """
    Configuration panel widget.

    Provides UI controls for configuring download settings.
    """

    def __init__(self, parent: tk.Widget, gui: 'CoupaDownloadsGUI'):
        """
        Initialize the configuration panel.

        Args:
            parent: Parent widget
            gui: Main GUI instance
        """
        super().__init__(parent, text="Config", padding="8")
        self.gui = gui

        # Configuration variables
        self.csv_file_var = tk.StringVar()
        self.download_dir_var = tk.StringVar()
        self.worker_count_var = tk.IntVar(value=4)
        self.max_retries_var = tk.IntVar(value=2)
        self.headless_var = tk.BooleanVar(value=True)

        # Create UI components
        self._create_widgets()

        # Bind validation
        self._setup_validation()

        # Bind change events to mark config as modified
        self._bind_change_events()

    def _create_widgets(self):
        """Create the configuration panel widgets"""
        # Main container frame
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="ew")
        main_frame.columnconfigure(0, weight=1)

        # Top row: CSV file and Download directory side by side
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        # CSV file section
        csv_frame = ttk.LabelFrame(top_frame, text="CSV", padding="3")
        csv_frame.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        csv_frame.columnconfigure(0, weight=1)

        self.csv_entry = ttk.Entry(csv_frame, textvariable=self.csv_file_var, font=("Arial", 8))
        self.csv_entry.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ttk.Button(csv_frame, text="...", command=self._browse_csv_file, width=3).grid(row=0, column=1)

        # Download directory section
        download_frame = ttk.LabelFrame(top_frame, text="Output", padding="3")
        download_frame.grid(row=0, column=1, sticky="ew", padx=(3, 0))
        download_frame.columnconfigure(0, weight=1)

        self.download_entry = ttk.Entry(download_frame, textvariable=self.download_dir_var, font=("Arial", 8))
        self.download_entry.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ttk.Button(download_frame, text="...", command=self._browse_download_dir, width=3).grid(row=0, column=1)

        # Bottom row: Settings and buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=1, column=0, sticky="ew")
        bottom_frame.columnconfigure(0, weight=1)

        # Settings section
        settings_frame = ttk.Frame(bottom_frame)
        settings_frame.grid(row=0, column=0, sticky="ew", pady=(0, 3))

        # Workers
        ttk.Label(settings_frame, text="Workers:", font=("Arial", 8)).grid(row=0, column=0, sticky="w", padx=(0, 2))
        self.worker_count_spin = ttk.Spinbox(
            settings_frame,
            from_=1,
            to=10,
            textvariable=self.worker_count_var,
            width=3,
            font=("Arial", 8)
        )
        self.worker_count_spin.grid(row=0, column=1, padx=(0, 8))

        # Retries
        ttk.Label(settings_frame, text="Retries:", font=("Arial", 8)).grid(row=0, column=2, sticky="w", padx=(0, 2))
        self.max_retries_spin = ttk.Spinbox(
            settings_frame,
            from_=0,
            to=5,
            textvariable=self.max_retries_var,
            width=3,
            font=("Arial", 8)
        )
        self.max_retries_spin.grid(row=0, column=3, padx=(0, 8))

        # Headless checkbox
        self.headless_check = ttk.Checkbutton(
            settings_frame,
            text="Headless",
            variable=self.headless_var,
            command=self._mark_modified
        )
        self.headless_check.grid(row=0, column=4, sticky="w")

        # Buttons
        button_frame = ttk.Frame(bottom_frame)
        button_frame.grid(row=1, column=0, sticky="ew")

        ttk.Button(button_frame, text="Load", command=self._load_config, width=6).pack(side="left", padx=(0, 3))
        ttk.Button(button_frame, text="Save", command=self._save_config, width=6).pack(side="left", padx=(0, 3))
        ttk.Button(button_frame, text="Validate", command=self._validate_config, width=8).pack(side="left")

        # Configure grid weights
        self.columnconfigure(0, weight=1)

    def _setup_validation(self):
        """Setup input validation"""
        # Validate numeric inputs
        self.worker_count_spin.config(validate="key", validatecommand=(self.register(self._validate_int), "%P"))
        self.max_retries_spin.config(validate="key", validatecommand=(self.register(self._validate_int), "%P"))

    def _validate_int(self, value: str) -> bool:
        """Validate integer input"""
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _bind_change_events(self):
        """Bind events to mark configuration as modified when values change"""
        # Bind to entry widgets
        self.csv_entry.bind('<KeyRelease>', self._mark_modified)
        self.download_entry.bind('<KeyRelease>', self._mark_modified)

        # Bind to spinbox widgets
        self.worker_count_spin.bind('<KeyRelease>', self._mark_modified)
        self.max_retries_spin.bind('<KeyRelease>', self._mark_modified)

        # Bind to checkbox
        self.headless_var.trace_add('write', lambda *args: self._mark_modified())

    def _mark_modified(self, event=None):
        """Mark configuration as modified"""
        if hasattr(self.gui, 'config_modified'):
            self.gui.config_modified = True

    def _browse_csv_file(self):
        """Browse for CSV file"""
        filename = browse_file(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.csv_file_var.set(filename)
            self._mark_modified()

    def _browse_download_dir(self):
        """Browse for download directory"""
        dirname = browse_directory(title="Select Download Directory")
        if dirname:
            self.download_dir_var.set(dirname)
            self._mark_modified()

    def load_configuration(self, config: ConfigurationSettings):
        """
        Load configuration into the UI.

        Args:
            config: Configuration to load
        """
        self.csv_file_var.set(str(config.csv_file_path) if config.csv_file_path else "")
        self.download_dir_var.set(str(config.download_directory) if config.download_directory else "")
        self.worker_count_var.set(config.worker_count)
        self.max_retries_var.set(config.max_retries)
        self.headless_var.set(config.headless)

        # Reset modified flag when loading
        if hasattr(self.gui, 'config_modified'):
            self.gui.config_modified = False

    def get_configuration(self) -> Optional[ConfigurationSettings]:
        """
        Get configuration from the UI.

        Returns:
            Configuration settings, or None if invalid
        """
        try:
            config = ConfigurationSettings(
                csv_file_path=Path(self.csv_file_var.get()) if self.csv_file_var.get() else None,
                download_directory=Path(self.download_dir_var.get()) if self.download_dir_var.get() else None,
                worker_count=self.worker_count_var.get(),
                max_retries=self.max_retries_var.get(),
                headless=self.headless_var.get()
            )
            return config
        except Exception as e:
            logger.error(f"Error creating configuration: {e}")
            return None

    def update_display(self):
        """Update the display based on current state"""
        # Enable/disable controls based on GUI state
        enabled = self.gui.ui_state.config_loaded
        state = "normal" if enabled else "disabled"

        self.csv_entry.config(state=state)
        self.download_entry.config(state=state)

    def _load_config(self):
        """Load configuration from file"""
        self.gui._load_configuration()

    def _save_config(self):
        """Save current configuration"""
        config = self.get_configuration()
        if config:
            self.gui.current_config = config
            success = self.gui.save_configuration()
            if success:
                self.gui.ui_state.config_loaded = True
                self.update_display()
                # Reset modified flag after successful save
                self.gui.config_modified = False
        else:
            messagebox.showerror("Error", "Invalid configuration settings")

    def _validate_config(self):
        """Validate current configuration"""
        config = self.get_configuration()
        if not config:
            messagebox.showerror("Error", "Invalid configuration settings")
            return

        errors = self.gui.validate_configuration()
        if errors:
            error_text = "\n".join(errors)
            messagebox.showerror("Validation Errors", f"Configuration validation failed:\n{error_text}")
        else:
            messagebox.showinfo("Validation", "Configuration is valid")