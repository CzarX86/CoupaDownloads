"""
Feedback Manager: Enhanced UI Feedback

Central coordinator for UI feedback in the CoupaDownloads application.
Provides thread-safe communication between background download threads and UI components.
"""

import logging
import threading
import queue
from typing import Callable, Any, Optional, Dict, List
from datetime import datetime

from .data_model import (
    ProgressData,
    StatusMessage,
    ErrorInfo,
    DownloadStatistics,
    FeedbackMessage,
    FeedbackMessageType,
    MessagePriority,
    UIFeedbackConfig,
    FeedbackManagerState,
)

logger = logging.getLogger(__name__)


class FeedbackManager:
    """Central coordinator for UI feedback management."""

    def __init__(self):
        """Initialize the feedback manager."""
        self._config: Optional[UIFeedbackConfig] = None
        self._state = FeedbackManagerState()
        self._message_queue: queue.Queue = queue.Queue(maxsize=1000)  # Prevent memory issues
        self._callbacks: Dict[str, List[Callable]] = {}
        self._shutdown_event = threading.Event()
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._worker_thread: Optional[threading.Thread] = None

        # Start message processing thread
        self._start_worker_thread()

    def _start_worker_thread(self) -> None:
        """Start the background thread for processing messages."""
        self._worker_thread = threading.Thread(
            target=self._process_messages,
            name="FeedbackManager-Worker",
            daemon=True
        )
        self._worker_thread.start()

    def _process_messages(self) -> None:
        """Process messages from the queue in background thread."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for message with timeout to allow shutdown
                message = self._message_queue.get(timeout=0.1)
                self._handle_message(message)
                self._message_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing feedback message: {e}")

    def _handle_message(self, message: FeedbackMessage) -> None:
        """Handle a single feedback message."""
        try:
            # Update internal state
            with self._lock:
                self._update_state_from_message(message)
                self._state.last_update = datetime.now()

            # Notify callbacks
            self._notify_callbacks(message.message_type.value, message.data)

        except Exception as e:
            logger.error(f"Error handling message {message.message_type}: {e}")

    def _update_state_from_message(self, message: FeedbackMessage) -> None:
        """Update internal state based on message type."""
        if message.message_type == FeedbackMessageType.PROGRESS_UPDATE:
            if isinstance(message.data, ProgressData):
                self._state.progress_data = message.data
        elif message.message_type == FeedbackMessageType.STATUS_CHANGE:
            if isinstance(message.data, StatusMessage):
                self._state.current_status = message.data
        elif message.message_type == FeedbackMessageType.ERROR_OCCURRED:
            if isinstance(message.data, ErrorInfo):
                self._state.error_history.append(message.data)
                # Keep only recent errors
                if len(self._state.error_history) > (self._config.max_error_history if self._config else 10):
                    self._state.error_history.pop(0)
        elif message.message_type == FeedbackMessageType.STATISTICS_UPDATE:
            if isinstance(message.data, DownloadStatistics):
                self._state.statistics = message.data
        elif message.message_type == FeedbackMessageType.OPERATION_START:
            self._state.is_active = True
        elif message.message_type == FeedbackMessageType.OPERATION_COMPLETE:
            self._state.is_active = False

    def _notify_callbacks(self, event_type: str, data: Any) -> None:
        """Notify registered callbacks for an event type."""
        callbacks = self._callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                # Call callbacks in separate threads to avoid blocking
                threading.Thread(
                    target=callback,
                    args=(data,),
                    name=f"Callback-{event_type}",
                    daemon=True
                ).start()
            except Exception as e:
                logger.error(f"Error in callback for {event_type}: {e}")

    def initialize(self, config: UIFeedbackConfig) -> None:
        """Initialize the feedback manager with configuration."""
        with self._lock:
            self._config = config
            logger.info(f"Feedback manager initialized with config: {config}")

    def start_operation(self, operation_name: str) -> None:
        """Signal the start of a download operation."""
        message = FeedbackMessage(
            message_type=FeedbackMessageType.OPERATION_START,
            data=operation_name,
            priority=MessagePriority.HIGH
        )
        self._enqueue_message(message)

    def update_progress(self, progress_data: ProgressData) -> None:
        """Update progress information."""
        message = FeedbackMessage(
            message_type=FeedbackMessageType.PROGRESS_UPDATE,
            data=progress_data,
            priority=MessagePriority.NORMAL
        )
        self._enqueue_message(message)

    def update_status(self, status: StatusMessage) -> None:
        """Update current status message."""
        message = FeedbackMessage(
            message_type=FeedbackMessageType.STATUS_CHANGE,
            data=status,
            priority=MessagePriority.NORMAL
        )
        self._enqueue_message(message)

    def report_error(self, error: ErrorInfo) -> None:
        """Report an error for display."""
        message = FeedbackMessage(
            message_type=FeedbackMessageType.ERROR_OCCURRED,
            data=error,
            priority=MessagePriority.HIGH
        )
        self._enqueue_message(message)

    def update_statistics(self, stats: DownloadStatistics) -> None:
        """Update download statistics."""
        message = FeedbackMessage(
            message_type=FeedbackMessageType.STATISTICS_UPDATE,
            data=stats,
            priority=MessagePriority.NORMAL
        )
        self._enqueue_message(message)

    def complete_operation(self, success: bool = True) -> None:
        """Signal completion of the operation."""
        message = FeedbackMessage(
            message_type=FeedbackMessageType.OPERATION_COMPLETE,
            data=success,
            priority=MessagePriority.HIGH
        )
        self._enqueue_message(message)

    def _enqueue_message(self, message: FeedbackMessage) -> None:
        """Enqueue a message for processing."""
        try:
            self._message_queue.put(message, timeout=1.0)  # Don't block indefinitely
        except queue.Full:
            logger.warning("Feedback message queue full, dropping message")

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register a callback for specific events."""
        with self._lock:
            if event_type not in self._callbacks:
                self._callbacks[event_type] = []
            if callback not in self._callbacks[event_type]:
                self._callbacks[event_type].append(callback)

    def unregister_callback(self, event_type: str, callback: Callable) -> None:
        """Unregister a callback."""
        with self._lock:
            if event_type in self._callbacks:
                try:
                    self._callbacks[event_type].remove(callback)
                except ValueError:
                    pass  # Callback not found

    def get_current_state(self) -> dict:
        """Get current feedback state snapshot."""
        with self._lock:
            return {
                'progress_data': self._state.progress_data,
                'current_status': self._state.current_status,
                'statistics': self._state.statistics,
                'error_history': self._state.error_history[-5:],  # Last 5 errors
                'is_active': self._state.is_active,
                'last_update': self._state.last_update,
                'queue_size': self._message_queue.qsize()
            }

    def shutdown(self) -> None:
        """Clean shutdown of feedback manager."""
        logger.info("Shutting down feedback manager")
        self._shutdown_event.set()

        # Wait for worker thread to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

        # Clear callbacks
        with self._lock:
            self._callbacks.clear()

        logger.info("Feedback manager shutdown complete")