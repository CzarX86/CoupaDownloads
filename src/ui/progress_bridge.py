"""
Progress Bridge: Connect Download Operations to UI Feedback

Provides integration points for connecting download operations to the UI feedback system.
Allows existing download code to update progress indicators without major refactoring.
"""

from typing import Optional, Callable, Any
import threading
import time
from contextlib import contextmanager

from src.ui.data_model import ProgressData, UIFeedbackConfig
from src.ui.feedback_manager import FeedbackManager


class ProgressBridge:
    """
    Bridge between download operations and UI progress indicators.

    Provides a simple interface for download operations to report progress
    that gets automatically forwarded to UI components.
    """

    def __init__(self, feedback_manager: FeedbackManager):
        """
        Initialize the progress bridge.

        Args:
            feedback_manager: FeedbackManager instance to send updates to
        """
        self.feedback_manager = feedback_manager
        self._lock = threading.Lock()
        self._current_progress = ProgressData()
        self._operation_active = False

    def start_operation(self, total_files: int, operation_name: str = "Download Operation"):
        """
        Start a new download operation.

        Args:
            total_files: Total number of files to download
            operation_name: Name of the operation for status messages
        """
        with self._lock:
            self._current_progress = ProgressData(
                total_files=total_files,
                completed_files=0,
                current_file=None
            )
            self._operation_active = True

        self.feedback_manager.start_operation(operation_name)
        self._send_progress_update()

    def update_file_progress(self, filename: str, bytes_downloaded: int = 0, total_bytes: int = 0):
        """
        Update progress for the current file being downloaded.

        Args:
            filename: Name of the file being downloaded
            bytes_downloaded: Bytes downloaded so far for this file
            total_bytes: Total bytes for this file
        """
        with self._lock:
            if not self._operation_active:
                return

            self._current_progress.current_file = filename
            self._current_progress.bytes_downloaded = bytes_downloaded
            self._current_progress.total_bytes = total_bytes

        self._send_progress_update()

    def complete_file(self, filename: str):
        """
        Mark a file as completed.

        Args:
            filename: Name of the completed file
        """
        with self._lock:
            if not self._operation_active:
                return

            self._current_progress.completed_files += 1
            self._current_progress.current_file = filename
            self._current_progress.bytes_downloaded = 0
            self._current_progress.total_bytes = 0

        self._send_progress_update()

    def complete_operation(self, success: bool = True):
        """
        Complete the download operation.

        Args:
            success: Whether the operation completed successfully
        """
        with self._lock:
            self._operation_active = False

        self.feedback_manager.complete_operation(success)

    def _send_progress_update(self):
        """Send current progress to feedback manager."""
        with self._lock:
            progress_copy = ProgressData(
                total_files=self._current_progress.total_files,
                completed_files=self._current_progress.completed_files,
                current_file=self._current_progress.current_file,
                current_file_size=self._current_progress.current_file_size,
                bytes_downloaded=self._current_progress.bytes_downloaded,
                total_bytes=self._current_progress.total_bytes,
                start_time=self._current_progress.start_time,
                estimated_time_remaining=self._current_progress.estimated_time_remaining,
                download_speed=self._current_progress.download_speed
            )

        self.feedback_manager.update_progress(progress_copy)


class ProgressContext:
    """
    Context manager for progress tracking in download operations.

    Provides automatic progress updates and cleanup for download operations.
    """

    def __init__(self, progress_bridge: ProgressBridge, total_files: int, operation_name: str = "Download"):
        """
        Initialize progress context.

        Args:
            progress_bridge: ProgressBridge instance
            total_files: Total number of files
            operation_name: Name of the operation
        """
        self.progress_bridge = progress_bridge
        self.total_files = total_files
        self.operation_name = operation_name
        self._entered = False

    def __enter__(self):
        """Start the progress tracking."""
        self.progress_bridge.start_operation(self.total_files, self.operation_name)
        self._entered = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Complete the progress tracking."""
        success = exc_type is None
        self.progress_bridge.complete_operation(success)
        self._entered = False

    def file_start(self, filename: str, file_size: Optional[int] = None):
        """
        Mark the start of downloading a file.

        Args:
            filename: Name of the file
            file_size: Size of the file in bytes (optional)
        """
        if self._entered:
            with self.progress_bridge._lock:
                self.progress_bridge._current_progress.current_file_size = file_size
            self.progress_bridge.update_file_progress(filename, 0, file_size or 0)

    def file_progress(self, filename: str, bytes_downloaded: int, total_bytes: int):
        """
        Update progress for current file.

        Args:
            filename: Name of the file
            bytes_downloaded: Bytes downloaded so far
            total_bytes: Total bytes for the file
        """
        if self._entered:
            self.progress_bridge.update_file_progress(filename, bytes_downloaded, total_bytes)

    def file_complete(self, filename: str):
        """
        Mark a file as completed.

        Args:
            filename: Name of the completed file
        """
        if self._entered:
            self.progress_bridge.complete_file(filename)


# Global bridge instance for easy access
_progress_bridge: Optional[ProgressBridge] = None


def initialize_progress_bridge(feedback_manager: FeedbackManager) -> ProgressBridge:
    """
    Initialize the global progress bridge.

    Args:
        feedback_manager: FeedbackManager instance

    Returns:
        ProgressBridge: The initialized bridge
    """
    global _progress_bridge
    _progress_bridge = ProgressBridge(feedback_manager)
    return _progress_bridge


def get_progress_bridge() -> Optional[ProgressBridge]:
    """
    Get the global progress bridge instance.

    Returns:
        ProgressBridge or None: The global bridge instance
    """
    return _progress_bridge


@contextmanager
def download_progress(total_files: int, operation_name: str = "Download"):
    """
    Context manager for download operations with automatic progress tracking.

    Usage:
        with download_progress(5, "PDF Downloads") as progress:
            for i, file in enumerate(files):
                progress.file_start(file.name, file.size)
                # Download file...
                progress.file_complete(file.name)

    Args:
        total_files: Total number of files to download
        operation_name: Name of the operation
    """
    bridge = get_progress_bridge()
    if bridge:
        with ProgressContext(bridge, total_files, operation_name) as context:
            yield context
    else:
        # No bridge available, provide dummy context
        class DummyContext:
            def file_start(self, *args, **kwargs): pass
            def file_progress(self, *args, **kwargs): pass
            def file_complete(self, *args, **kwargs): pass

        yield DummyContext()