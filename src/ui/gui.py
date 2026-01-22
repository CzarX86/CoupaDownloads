# Main GUI application window

"""
Main Tkinter GUI application for CoupaDownloads.

This module provides the main application window that integrates
all GUI components for configuration and control of downloads.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional

from .state import UIState, OperationStatus
from .config_panel import ConfigPanel
from .control_panel import ControlPanel
from .status_display import StatusDisplay
from .communication import GUICommunicator, get_gui_communicator
from .feedback_manager import FeedbackManager
from .components.progress_display import ProgressDisplay
from .components.status_panel import StatusPanel
from .components.error_display import ErrorDisplay
from .components.statistics_panel import StatisticsPanel
from .data_model import StatusType
from ..core.interfaces import get_core_system, CoreSystemInterface
from ..core.config import ConfigurationSettings

logger = logging.getLogger(__name__)


class CoupaDownloadsGUI:
    """
    Main GUI application window for CoupaDownloads.

    This class creates and manages the main Tkinter window with all
    GUI components for configuring and controlling download operations.
    """

    def __init__(self, root: tk.Tk):
        """
        Initialize the GUI application.

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("CoupaDownloads")
        self.root.geometry("900x700")  # Reduced size for more compact layout
        self.root.resizable(True, True)
        self.root.minsize(800, 600)  # Set minimum size to prevent content from being too cramped

        # Initialize core components
        self.core_system: CoreSystemInterface = get_core_system()
        self.ui_state = UIState()
        self.communicator = get_gui_communicator()
        self.communicator.set_gui_root(self.root)

        # Initialize enhanced UI feedback system
        from .data_model import UIFeedbackConfig
        self.feedback_config = UIFeedbackConfig()
        self.feedback_manager = FeedbackManager()
        self.feedback_manager.initialize(self.feedback_config)

        # Current configuration
        self.current_config: Optional[ConfigurationSettings] = None
        self.config_modified = False

        # Create GUI components
        self._create_menu()
        self._create_main_layout()
        self._setup_communication()

        # Load initial configuration
        self._load_configuration()

        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        logger.info("CoupaDownloads GUI initialized")

    def _create_menu(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self._on_closing)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_main_layout(self):
        """Create the main window layout"""
        # Configure root window grid weights for proper resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Create main frame that fills the window with minimal padding
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)  # Title
        main_frame.rowconfigure(1, weight=0)  # Config panel
        main_frame.rowconfigure(2, weight=0)  # Control panel
        main_frame.rowconfigure(3, weight=0)  # Progress display
        main_frame.rowconfigure(4, weight=1)  # Status panel (more weight)
        main_frame.rowconfigure(5, weight=0)  # Error display
        main_frame.rowconfigure(6, weight=0)  # Statistics panel

        # Create content directly in main frame
        self._create_content(main_frame)

    def _create_content(self, parent):
        """Create the main content inside the parent frame"""
        # Title - minimal font
        title_label = ttk.Label(
            parent,
            text="CoupaDownloads",
            font=("Arial", 12, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 5), sticky="w")

        # Configuration panel
        self.config_panel = ConfigPanel(parent, self)
        self.config_panel.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        # Control panel
        self.control_panel = ControlPanel(parent, self)
        self.control_panel.grid(row=2, column=0, sticky="ew", pady=(0, 5))

        # Progress display
        self.progress_display = ProgressDisplay(parent, self.feedback_config)
        self.progress_display.register_with_feedback_manager(self.feedback_manager)
        self.progress_display.grid(row=3, column=0, sticky="ew", pady=(0, 5))

        # Status panel
        self.status_panel = StatusPanel(parent, self.feedback_config)
        self.status_panel.register_with_feedback_manager(self.feedback_manager)
        self.status_panel.grid(row=4, column=0, sticky="nsew", pady=(0, 5))

        # Error display
        self.error_display = ErrorDisplay(parent, self.feedback_config)
        self.error_display.register_with_feedback_manager(self.feedback_manager)
        self.error_display.grid(row=5, column=0, sticky="ew", pady=(0, 5))

        # Statistics panel
        self.statistics_panel = StatisticsPanel(parent, self.feedback_config)
        self.statistics_panel.register_with_feedback_manager(self.feedback_manager)
        self.statistics_panel.grid(row=6, column=0, sticky="ew", pady=(0, 0))

        # Keep old status display for compatibility (hidden or removed)
        # self.status_display = StatusDisplay(parent, self)
        # self.status_display.grid(row=7, column=0, sticky="nsew", pady=(0, 0))

        # Configure grid weights for parent frame
        parent.columnconfigure(0, weight=1)

    def _bind_mousewheel(self):
        """Bind mousewheel to canvas scrolling"""
        # Removed - no longer using canvas for scrolling
        pass

    def _setup_communication(self):
        """Setup communication with background operations"""
        # Override the communicator's message handler
        original_handler = self.communicator._handle_message
        self.communicator._handle_message = self._handle_status_message

    def _handle_status_message(self, message):
        """Handle status messages from background operations"""
        # Update UI state based on message
        if message.progress is not None:
            self.ui_state.progress_percentage = message.progress

        # Update enhanced feedback system
        from ..core.status import StatusMessage as CoreStatusMessage
        from .data_model import StatusMessage, StatusType

        if isinstance(message, CoreStatusMessage):
            # Convert core message to feedback message
            feedback_message = StatusMessage(
                message_type=self._map_status_type(message.level),
                title=message.operation_id or "Operation",
                message=message.message
            )
            self.feedback_manager.update_status(feedback_message)

        # Update old status display for compatibility
        if hasattr(self, 'status_display'):
            self.status_display.update_status(message)

        # Update control panel state
        self.control_panel.update_button_states()

    def _map_status_type(self, level: str) -> StatusType:
        """Map core status level to feedback StatusType."""
        level_map = {
            'info': StatusType.INFO,
            'success': StatusType.SUCCESS,
            'warning': StatusType.WARNING,
            'error': StatusType.ERROR,
            'progress': StatusType.PROGRESS
        }
        return level_map.get(level, StatusType.INFO)

    def _load_configuration(self):
        """Load configuration from core system"""
        try:
            self.current_config = self.core_system.load_configuration()
            if self.current_config:
                self.ui_state.config_loaded = True
                # Ensure reasonable defaults if the loaded config is missing fields
                if not hasattr(self.current_config, 'worker_count') or self.current_config.worker_count in (None, 0, 1):
                    self.current_config.worker_count = ConfigurationSettings().worker_count
                if not hasattr(self.current_config, 'headless'):
                    self.current_config.headless = ConfigurationSettings().headless

                self.config_panel.load_configuration(self.current_config)
                logger.info("Configuration loaded successfully")
            else:
                default_config = ConfigurationSettings()
                self.current_config = default_config
                self.config_panel.load_configuration(default_config)
                self.ui_state.config_loaded = True
                logger.info("No configuration found, using default settings")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self.ui_state.config_loaded = False
            messagebox.showerror("Configuration Error", f"Failed to load configuration: {e}")

        # Update UI to reflect loaded state
        self.config_panel.update_display()
        self.control_panel.update_button_states()

    def save_configuration(self) -> bool:
        """
        Save current configuration.

        Returns:
            True if saved successfully
        """
        if not self.current_config:
            return False

        try:
            success = self.core_system.save_configuration(self.current_config)
            if success:
                logger.info("Configuration saved successfully")
                messagebox.showinfo("Success", "Configuration saved successfully")
            else:
                logger.error("Failed to save configuration")
                messagebox.showerror("Error", "Failed to save configuration")
            return success
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            messagebox.showerror("Error", f"Error saving configuration: {e}")
            return False

    def validate_configuration(self) -> list[str]:
        """
        Validate current configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        if not self.current_config:
            return ["No configuration loaded"]

        return self.core_system.validate_configuration(self.current_config)

    def start_downloads(self):
        """Start download operations"""
        if not self.current_config:
            messagebox.showerror("Error", "No configuration loaded")
            return

        # Validate configuration
        errors = self.validate_configuration()
        if errors:
            error_text = "\n".join(errors)
            messagebox.showerror("Configuration Error", f"Invalid configuration:\n{error_text}")
            return

        try:
            # Update runtime configuration for experimental core system
            if self.current_config.download_directory:
                # Update the experimental config with the current download directory
                from EXPERIMENTAL.corelib.config import Config
                Config.DOWNLOAD_FOLDER = str(self.current_config.download_directory)
                Config.ensure_download_folder_exists()
                logger.info(f"Updated download folder to: {Config.DOWNLOAD_FOLDER}")
                
                # Add status message about download location
                from ..core.status import StatusMessage
                location_message = StatusMessage.info(
                    message=f"Files will be saved to: {Config.DOWNLOAD_FOLDER}",
                    operation_id="download_setup"
                )
                self._handle_status_message(location_message)
                
                # Show user where files will be saved
                messagebox.showinfo("Download Location", f"Files will be saved to:\n{Config.DOWNLOAD_FOLDER}")
            else:
                messagebox.showwarning("No Download Directory", "No download directory specified. Files will be saved to the default location.")

            # Update UI state
            self.ui_state.update_operation_status(OperationStatus.RUNNING, "Starting downloads...")

            # Notify feedback manager
            self.feedback_manager.start_operation("download_batch")

            # Start downloads through core system
            handle = self.core_system.start_downloads(
                self.current_config,
                self._handle_status_message,
                self.communicator
            )

            # Store operation handle
            self.current_operation = handle

            # Update UI
            self.control_panel.update_button_states()

            logger.info("Download operation started")

        except Exception as e:
            logger.error(f"Failed to start downloads: {e}")
            self.ui_state.update_operation_status(OperationStatus.ERROR, f"Failed to start: {e}")
            messagebox.showerror("Error", f"Failed to start downloads: {e}")

    def stop_downloads(self):
        """Stop download operations"""
        if not hasattr(self, 'current_operation'):
            return

        try:
            success = self.core_system.stop_downloads(self.current_operation)
            if success:
                self.ui_state.update_operation_status(OperationStatus.STOPPED, "Stopping downloads...")
                logger.info("Download operation stop requested")
            else:
                logger.warning("Failed to send stop signal")

        except Exception as e:
            logger.error(f"Error stopping downloads: {e}")
            messagebox.showerror("Error", f"Error stopping downloads: {e}")

    def _on_closing(self):
        """Handle window close event"""
        # Check if downloads are running
        if self.ui_state.operation_running:
            result = messagebox.askyesnocancel(
                "Confirm Exit",
                "Downloads are currently running. Do you want to stop them and exit?"
            )

            if result is None:  # Cancel
                return
            elif result:  # Yes - stop and exit
                self.stop_downloads()
                # Give a moment for stop signal
                self.root.after(1000, self._do_close)
                return
            # No - just exit without stopping

        # Check if configuration needs saving
        if self.config_modified and self.current_config:
            result = messagebox.askyesnocancel(
                "Save Configuration",
                "Configuration has been modified. Do you want to save changes?"
            )

            if result is None:  # Cancel
                return
            elif result:  # Yes - save and exit
                if not self.save_configuration():
                    result = messagebox.askyesno(
                        "Save Failed",
                        "Failed to save configuration. Exit anyway?"
                    )
                    if not result:
                        return

        # Clean shutdown
        self._do_close()

    def _do_close(self):
        """Perform the actual window closing"""
        self.communicator.shutdown()
        self.root.destroy()

    def _show_about(self):
        """Show about dialog"""
        about_text = """CoupaDownloads GUI

A graphical interface for configuring and controlling
Coupa download operations.

Version: 0.1.0
"""
        messagebox.showinfo("About CoupaDownloads", about_text)

    def run(self):
        """Start the GUI event loop"""
        try:
            self.root.mainloop()
        except Exception as e:
            logger.critical(f"Unhandled GUI exception: {e}", exc_info=True)
            messagebox.showerror("Critical Error", f"An unexpected error occurred:\n{e}\n\nPlease check the logs for more details.")
            self._do_close()