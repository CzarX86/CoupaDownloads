# Thread-safe GUI communication

"""
Thread-safe communication patterns for GUI-worker coordination.

This module provides utilities for safe communication between background
worker threads/processes and the Tkinter GUI main thread.
"""

import threading
import queue
import time
from datetime import datetime
from typing import Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from ..core.status import StatusMessage, StatusLevel


class GUICommunicator:
    """
    Thread-safe communicator for GUI-background thread coordination.

    This class manages a queue for status messages and provides methods
    for background threads to safely update the GUI.
    """

    def __init__(self, gui_root=None, max_workers: int = 2):
        """
        Initialize the GUI communicator.

        Args:
            gui_root: Tkinter root window for scheduling GUI updates
            max_workers: Maximum worker threads for processing messages
        """
        self.message_queue = queue.Queue()
        self.gui_root = gui_root
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="GUI-Comm")
        self._running = True
        self._shutdown_event = threading.Event()

        # Start message processing thread
        self.executor.submit(self._process_messages)

    def send_status_update(self, message: StatusMessage):
        """
        Send a status update to the GUI (thread-safe).

        Args:
            message: StatusMessage to send
        """
        if self._running:
            self.message_queue.put(message)

    def set_gui_root(self, gui_root):
        """
        Set the Tkinter root for scheduling GUI updates.

        Args:
            gui_root: Tkinter root window
        """
        self.gui_root = gui_root

    def _process_messages(self):
        """Process messages from the queue (runs in background thread)"""
        while not self._shutdown_event.is_set():
            try:
                # Wait for a message with timeout
                message = self.message_queue.get(timeout=0.1)

                # Schedule GUI update in main thread
                if self.gui_root:
                    self.gui_root.after(0, self._handle_message, message)
                else:
                    # If no GUI root, process immediately (for testing)
                    self._handle_message(message)

                self.message_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                # Log error but continue processing
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing GUI message: {e}")

    def _handle_message(self, message: StatusMessage):
        """
        Handle a status message in the GUI thread.

        This method should be overridden by GUI components to handle messages.

        Args:
            message: StatusMessage to handle
        """
        # Default implementation - override in GUI classes
        print(f"GUI Message: {message.level.value}: {message.message}")

    def shutdown(self, timeout: float = 5.0):
        """
        Shutdown the communicator gracefully.

        Args:
            timeout: Maximum time to wait for shutdown
        """
        self._running = False
        self._shutdown_event.set()

        # Wait for message processing to complete
        try:
            self.message_queue.join()  # Wait for all messages to be processed
        except:
            pass

        # Shutdown executor
        self.executor.shutdown(wait=True)


class BackgroundOperation:
    """
    Base class for background operations that communicate with GUI.

    This class provides a standard way for background operations to
    send status updates to the GUI communicator.
    """

    def __init__(self, communicator: GUICommunicator, operation_id: Optional[str] = None):
        """
        Initialize background operation.

        Args:
            communicator: GUICommunicator for status updates
            operation_id: Optional identifier for this operation
        """
        self.communicator = communicator
        self.operation_id = operation_id or f"op_{id(self)}"
        self._cancelled = False

    def send_status(self, message: str, level: str = "info", progress: Optional[int] = None):
        """
        Send a status update to the GUI.

        Args:
            message: Status message text
            level: Message level (info, warning, error, success)
            progress: Optional progress percentage (0-100)
        """
        if self._cancelled:
            return

        # Create status message
        status_msg = StatusMessage(
            timestamp=datetime.now(),
            level=getattr(StatusLevel, level.upper(), StatusLevel.INFO),
            message=message,
            operation_id=self.operation_id,
            progress=progress
        )

        self.communicator.send_status_update(status_msg)

    def is_cancelled(self) -> bool:
        """
        Check if operation has been cancelled.

        Returns:
            True if operation should stop
        """
        return self._cancelled

    def cancel(self):
        """Cancel this operation"""
        self._cancelled = True
        self.send_status("Operation cancelled", "warning")


# Global communicator instance
_gui_communicator: Optional[GUICommunicator] = None

def get_gui_communicator() -> GUICommunicator:
    """
    Get the global GUI communicator instance.

    Returns:
        GUICommunicator instance
    """
    global _gui_communicator
    if _gui_communicator is None:
        _gui_communicator = GUICommunicator()
    return _gui_communicator

def set_gui_communicator(communicator: GUICommunicator):
    """
    Set the global GUI communicator instance.

    Args:
        communicator: GUICommunicator to set
    """
    global _gui_communicator
    _gui_communicator = communicator