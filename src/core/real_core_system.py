# Real core system implementation for GUI integration

"""
Real implementation of CoreSystemInterface using the experimental core system.
"""

import os
import sys
import threading
import time
from typing import Optional, List, Callable
from pathlib import Path

# Add experimental path
experimental_path = Path(__file__).parent.parent / "EXPERIMENTAL"
if str(experimental_path) not in sys.path:
    sys.path.insert(0, str(experimental_path))

from .config import ConfigurationSettings
from .status import StatusMessage
from .interfaces import CoreSystemInterface, OperationHandle

# Import experimental core
from EXPERIMENTAL.core.main import MainApp
from EXPERIMENTAL.corelib.models import HeadlessConfiguration


class RealCoreSystem(CoreSystemInterface):
    """
    Real implementation using the experimental core system.
    """

    def __init__(self):
        self._active_operations = {}
        self._config = None

    def load_configuration(self) -> Optional[ConfigurationSettings]:
        """Load configuration from experimental config"""
        try:
            from EXPERIMENTAL.corelib.config import Config
            # Create a ConfigurationSettings from experimental config
            config = ConfigurationSettings()
            
            # Use default CSV file path if not configured
            excel_path = Config.EXCEL_FILE_PATH
            if not excel_path:
                excel_path = Config.get_csv_file_path()
            
            config.csv_file_path = Path(excel_path) if excel_path else None
            config.download_directory = Path(Config.DOWNLOAD_FOLDER) if Config.DOWNLOAD_FOLDER else None
            config.worker_count = getattr(Config, 'PROC_WORKERS', 4)
            config.headless = True  # Default to headless mode unless user changes it
            self._config = config
            return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return None

    def save_configuration(self, config: ConfigurationSettings) -> bool:
        """Save configuration to experimental config"""
        try:
            from EXPERIMENTAL.corelib.config import Config
            Config.EXCEL_FILE_PATH = str(config.csv_file_path) if config.csv_file_path else ""
            Config.DOWNLOAD_FOLDER = str(config.download_directory) if config.download_directory else "/tmp/downloads"
            Config.PROC_WORKERS = config.worker_count
            # Note: headless setting is handled in start_downloads via HeadlessConfiguration
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False

    def validate_configuration(self, config: ConfigurationSettings) -> List[str]:
        """Validate configuration"""
        errors = []

        if not config.csv_file_path or not os.path.exists(config.csv_file_path):
            errors.append(f"CSV file not found: {config.csv_file_path}")

        if not config.download_directory:
            errors.append("Download directory not specified")

        if config.worker_count < 1:
            errors.append("Worker count must be at least 1")

        return errors

    def start_downloads(
        self,
        config: ConfigurationSettings,
        status_callback: Callable[[StatusMessage], None],
        gui_communicator=None
    ) -> OperationHandle:
        """Start real downloads using experimental core system"""
        handle = OperationHandle()

        # Store configuration
        self._config = config

        # Create headless config from GUI configuration
        headless_config = HeadlessConfiguration(enabled=config.headless)

        def run_downloads():
            try:
                # Disable interactive UI mode for GUI context
                import os
                original_interactive = os.environ.get('ENABLE_INTERACTIVE_UI', 'True')
                os.environ['ENABLE_INTERACTIVE_UI'] = 'False'
                
                try:
                    # Create MainApp instance
                    app = MainApp(enable_parallel=config.worker_count > 1, max_workers=config.worker_count)
                    app.set_headless_configuration(headless_config)

                    # Mark operation as running
                    self._active_operations[id(handle)] = "running"

                    # Send initial status
                    status_callback(StatusMessage.info("Starting downloads...", progress=0))

                    # Override the app's print function to capture status updates
                    original_print = print
                    def capture_print(*args, **kwargs):
                        message = ' '.join(str(arg) for arg in args)
                        # Try to extract progress information from messages
                        if 'Processing PO' in message and '/' in message:
                            # Extract progress from "Processing PO 1/10"
                            try:
                                parts = message.split('/')
                                if len(parts) == 2:
                                    current = int(parts[0].split()[-1])
                                    total = int(parts[1].split()[0])
                                    progress = int((current / total) * 100)
                                    status_callback(StatusMessage.info(f"Processing PO {current}/{total}", progress=progress))
                            except:
                                pass
                        elif '✅' in message or '❌' in message or '📭' in message:
                            # Status messages with emojis
                            status_callback(StatusMessage.info(message))
                        elif 'Starting processing' in message:
                            status_callback(StatusMessage.info("Initializing download process...", progress=5))
                        elif 'Using' in message and 'worker' in message:
                            status_callback(StatusMessage.info(message, progress=10))
                        elif '🚀 Starting' in message:
                            status_callback(StatusMessage.info("Connecting to Coupa system...", progress=20))
                        elif '🎉 Processing complete' in message:
                            status_callback(StatusMessage.info("Downloads completed successfully!", progress=100))
                            self._active_operations[id(handle)] = "completed"
                        elif '❌ Failed' in message:
                            status_callback(StatusMessage.error("Download process failed"))
                            self._active_operations[id(handle)] = "error"

                        # Still print to console
                        original_print(*args, **kwargs)

                    # Temporarily replace print
                    import builtins
                    builtins.print = capture_print

                    try:
                        # Run the main app
                        app.run()

                        # Check if we have results
                        if hasattr(app, '_last_parallel_report') and app._last_parallel_report:
                            report = app._last_parallel_report
                            successful = report.get('results', [])
                            total = len(successful)
                            if total > 0:
                                status_callback(StatusMessage.info(f"Processed {total} POs successfully", progress=100))
                                self._active_operations[id(handle)] = "completed"
                            else:
                                status_callback(StatusMessage.info("No POs to process", progress=100))
                                self._active_operations[id(handle)] = "completed"
                        else:
                            status_callback(StatusMessage.info("Download process completed", progress=100))
                            self._active_operations[id(handle)] = "completed"

                    finally:
                        # Restore original print
                        builtins.print = original_print

                        # Close the app
                        app.close()
                        
                finally:
                    # Restore original interactive UI setting
                    os.environ['ENABLE_INTERACTIVE_UI'] = original_interactive

            except Exception as e:
                error_msg = f"Download failed: {e}"
                status_callback(StatusMessage.error(error_msg))
                self._active_operations[id(handle)] = "error"
                print(f"Error in download thread: {e}")

        # Start download thread
        thread = threading.Thread(target=run_downloads, daemon=True)
        thread.start()

        return handle

    def stop_downloads(self, handle: OperationHandle) -> bool:
        """Stop downloads"""
        operation_id = id(handle)
        if operation_id in self._active_operations:
            current_status = self._active_operations[operation_id]
            if current_status == "running":
                self._active_operations[operation_id] = "stopped"
                return True
            elif current_status in ("completed", "error", "stopped"):
                return True
        return False

    def get_operation_status(self, handle: OperationHandle) -> str:
        """Get operation status"""
        operation_id = id(handle)
        return self._active_operations.get(operation_id, "NOT_STARTED")