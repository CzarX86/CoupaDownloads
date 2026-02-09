"""
StatusManager implementation.

Provides real-time status updates through a subscription system with thread safety
and callback failure handling.
"""

import threading
import time
import uuid
from typing import Dict, Any, Callable, List, Optional
from collections import defaultdict

from .types import (
    StatusManagerInterface,
    StatusUpdate,
    StatusCallback,
    StatusError
)


class StatusManager(StatusManagerInterface):
    """
    Thread-safe status update manager with subscription system.

    Provides real-time status updates through callbacks with automatic cleanup
    of failing subscribers and thread-safe operations.
    """

    def __init__(self):
        """Initialize StatusManager with thread-safe data structures."""
        self._lock = threading.RLock()
        self._subscribers: Dict[str, StatusCallback] = {}
        self._failure_counts: Dict[str, int] = defaultdict(int)
        self._max_failures = 3

    def subscribe_to_updates(self, callback: StatusCallback) -> str:
        """
        Subscribe to status updates.

        Args:
            callback: Function to call when status updates occur.

        Returns:
            Subscription ID string for unsubscribing.
        """
        if not callable(callback):
            raise ValueError("Callback must be callable")

        subscription_id = str(uuid.uuid4())

        with self._lock:
            self._subscribers[subscription_id] = callback
            # Reset failure count for new subscription
            if subscription_id in self._failure_counts:
                del self._failure_counts[subscription_id]

        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from status updates.

        Args:
            subscription_id: ID returned from subscribe_to_updates.

        Returns:
            True if unsubscribed successfully, False otherwise.
        """
        with self._lock:
            if subscription_id in self._subscribers:
                del self._subscribers[subscription_id]
                # Clean up failure count
                if subscription_id in self._failure_counts:
                    del self._failure_counts[subscription_id]
                return True
            return False

    def notify_status_update(self, update: StatusUpdate) -> None:
        """
        Notify all subscribers of a status update.

        Args:
            update: StatusUpdate to broadcast to subscribers.

        Raises:
            ValueError: If update is not a StatusUpdate instance.
        """
        if not isinstance(update, StatusUpdate):
            raise ValueError("Update must be a StatusUpdate instance")

        # Get a snapshot of subscribers to avoid holding lock during callbacks
        with self._lock:
            current_subscribers = self._subscribers.copy()

        # Track failed subscriptions for cleanup
        failed_subscriptions = []

        # Notify all subscribers
        for subscription_id, callback in current_subscribers.items():
            try:
                callback(update)
                # Reset failure count on successful call
                with self._lock:
                    if subscription_id in self._failure_counts:
                        del self._failure_counts[subscription_id]
            except Exception:
                # Handle callback failure
                with self._lock:
                    self._failure_counts[subscription_id] += 1
                    if self._failure_counts[subscription_id] >= self._max_failures:
                        failed_subscriptions.append(subscription_id)

        # Clean up failed subscriptions
        for subscription_id in failed_subscriptions:
            self.unsubscribe(subscription_id)

    def get_subscriber_count(self) -> int:
        """
        Get number of active subscribers.

        Returns:
            Number of currently subscribed callbacks.
        """
        with self._lock:
            return len(self._subscribers)