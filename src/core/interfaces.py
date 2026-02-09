# Core system interfaces for GUI integration

"""
Interface definitions for GUI-core system communication.

These interfaces define the contract between the Tkinter GUI and the
CoupaDownloads core system for configuration management and operation control.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Callable, Protocol
from pathlib import Path

from .config import ConfigurationSettings
from .status import StatusMessage
from .config_handler import ConfigHandler


class OperationHandle:
    """
    Opaque handle for tracking download operations.

    This is returned by start_downloads and used for stop_downloads and status queries.
    """
    pass


class CoreSystemInterface(Protocol):
    """
    Protocol defining the interface that the GUI uses to interact with the core system.

    This protocol ensures the GUI can work with different implementations of the core system.
    """

    # Configuration Management
    def load_configuration(self) -> Optional[ConfigurationSettings]:
        """
        Load persisted configuration.

        Returns:
            ConfigurationSettings if available, None otherwise
        """
        ...

    def save_configuration(self, config: ConfigurationSettings) -> bool:
        """
        Persist configuration changes.

        Args:
            config: Configuration to save

        Returns:
            True if saved successfully
        """
        ...

    def validate_configuration(self, config: ConfigurationSettings) -> List[str]:
        """
        Validate configuration against business rules.

        Args:
            config: Configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        ...

    # Operation Control
    def start_downloads(
        self,
        config: ConfigurationSettings,
        status_callback: Callable[[StatusMessage], None],
        gui_communicator=None
    ) -> OperationHandle:
        """
        Initiate download operations with status callback.

        Args:
            config: Validated configuration
            status_callback: Function called with status updates
            gui_communicator: Optional GUI communicator for thread-safe updates

        Returns:
            Handle for tracking the operation
        """
        ...

    def stop_downloads(self, handle: OperationHandle) -> bool:
        """
        Gracefully stop download operations.

        Args:
            handle: Operation handle from start_downloads

        Returns:
            True if stop signal sent successfully
        """
        ...

    def get_operation_status(self, handle: OperationHandle) -> str:
        """
        Get current status of download operation.

        Args:
            handle: Operation handle from start_downloads

        Returns:
            Status string (NOT_STARTED, RUNNING, COMPLETED, ERROR, STOPPED)
        """
        ...


# Stub Implementation for Development
class CoreSystemStub:
    """
    Stub implementation of CoreSystemInterface for GUI development and testing.

    This provides mock responses to allow GUI development before core integration.
    """

    def __init__(self):
        self._config_handler = ConfigHandler()
        self._active_operations = {}

    def load_configuration(self) -> Optional[ConfigurationSettings]:
        """Load configuration using config handler"""
        return self._config_handler.load_configuration()

    def save_configuration(self, config: ConfigurationSettings) -> bool:
        """Save configuration using config handler"""
        return self._config_handler.save_configuration(config)

    def validate_configuration(self, config: ConfigurationSettings) -> List[str]:
        """Stub: Basic validation"""
        return config.get_validation_errors()

    def start_downloads(
        self,
        config: ConfigurationSettings,
        status_callback: Callable[[StatusMessage], None],
        gui_communicator=None
    ) -> OperationHandle:
        """Stub: Simulate download operation with progress updates"""
        import threading
        import time

        handle = OperationHandle()

        # Simulate starting downloads
        status_msg = StatusMessage.info("Starting downloads...", progress=0)
        if gui_communicator and hasattr(gui_communicator, 'send_status_update'):
            # Use GUI communicator for thread-safe updates
            gui_communicator.send_status_update(status_msg)
        else:
            # Fallback to direct callback
            status_callback(status_msg)

        # Mark operation as running
        self._active_operations[id(handle)] = "running"

        # Start background thread to simulate progress
        def simulate_downloads():
            try:
                total_steps = 20  # More steps for smoother progress
                for step in range(total_steps + 1):
                    # Check if operation was stopped
                    if self._active_operations.get(id(handle)) != "running":
                        stop_msg = StatusMessage.info("Downloads stopped by user", progress=0)
                        if gui_communicator and hasattr(gui_communicator, 'send_status_update'):
                            gui_communicator.send_status_update(stop_msg)
                        else:
                            status_callback(stop_msg)
                        break

                    progress = int((step / total_steps) * 100)

                    if step == 0:
                        msg = StatusMessage.info("Initializing workers...", progress=progress)
                    elif step == 2:
                        msg = StatusMessage.info("Loading configuration...", progress=progress)
                    elif step == 5:
                        msg = StatusMessage.info("Connecting to Coupa...", progress=progress)
                    elif step < total_steps - 2:
                        msg = StatusMessage.info(f"Downloading item {step-5}/{total_steps-7}...", progress=progress)
                    elif step == total_steps - 2:
                        msg = StatusMessage.info("Finalizing downloads...", progress=progress)
                    else:
                        msg = StatusMessage.info("Downloads completed successfully!", progress=100)
                        self._active_operations[id(handle)] = "completed"

                    # Send message via communicator or direct callback
                    if gui_communicator and hasattr(gui_communicator, 'send_status_update'):
                        gui_communicator.send_status_update(msg)
                    else:
                        status_callback(msg)

                    time.sleep(1)  # Faster updates for better feedback

                # If not stopped and not completed, mark as completed
                if self._active_operations.get(id(handle)) == "running":
                    final_msg = StatusMessage.info("Downloads completed successfully!", progress=100)
                    if gui_communicator and hasattr(gui_communicator, 'send_status_update'):
                        gui_communicator.send_status_update(final_msg)
                    else:
                        status_callback(final_msg)
                    self._active_operations[id(handle)] = "completed"

            except Exception as e:
                error_msg = StatusMessage.error(f"Download failed: {e}")
                if gui_communicator and hasattr(gui_communicator, 'send_status_update'):
                    gui_communicator.send_status_update(error_msg)
                else:
                    status_callback(error_msg)
                self._active_operations[id(handle)] = "error"

        # Start simulation thread
        thread = threading.Thread(target=simulate_downloads, daemon=True)
        thread.start()

        return handle

    def stop_downloads(self, handle: OperationHandle) -> bool:
        """Stub: Simulate stopping downloads"""
        operation_id = id(handle)
        if operation_id in self._active_operations:
            current_status = self._active_operations[operation_id]
            if current_status == "running":
                self._active_operations[operation_id] = "stopped"
                return True
            elif current_status in ("completed", "error", "stopped"):
                # Already finished
                return True
        return False

    def get_operation_status(self, handle: OperationHandle) -> str:
        """Stub: Return operation status"""
        operation_id = id(handle)
        return self._active_operations.get(operation_id, "NOT_STARTED")


# Factory function for getting core system interface
def get_core_system() -> CoreSystemInterface:
    """
    Factory function to get the core system interface.

    Returns:
        CoreSystemInterface implementation
    """
    # For GUI integration, return real implementation
    # In production, this would return the real core system
    try:
        from .real_core_system import RealCoreSystem
        return RealCoreSystem()
    except ImportError:
        # Fallback to stub for development
        return CoreSystemStub()