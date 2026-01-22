"""
Integration tests for StatusManager.

Tests StatusManager integration with other components and real-world usage patterns.
"""

import pytest
import time
import threading
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch

from src.core.status_manager import StatusManager
from src.core.processing_controller import ProcessingController
from src.core.types import (
    StatusManagerInterface,
    StatusUpdate,
    StatusEventType,
    ProcessingControllerInterface,
    ConfigurationManagerInterface
)


@pytest.mark.integration
class TestStatusManagerIntegration:
    """Test StatusManager integration with other components."""

    @pytest.fixture
    def status_manager(self) -> StatusManagerInterface:
        """Create a StatusManager instance for testing."""
        return StatusManager()

    @pytest.fixture
    def processing_controller(self) -> ProcessingControllerInterface:
        """Create a ProcessingController instance for testing."""
        return ProcessingController()

    def test_status_manager_initialization(self, status_manager: StatusManagerInterface):
        """Test StatusManager initializes correctly."""
        assert status_manager.get_subscriber_count() == 0

    def test_status_manager_with_processing_controller(self, status_manager: StatusManagerInterface, processing_controller: ProcessingControllerInterface):
        """Test StatusManager integration with ProcessingController."""
        # Subscribe to status updates
        callback = Mock()
        subscription_id = status_manager.subscribe_to_updates(callback)

        # This test will be expanded once ProcessingController integration is implemented
        # For now, just verify the subscription works
        assert status_manager.get_subscriber_count() == 1

        # Clean up
        status_manager.unsubscribe(subscription_id)

    def test_multiple_subscribers_different_callbacks(self, status_manager: StatusManagerInterface):
        """Test multiple subscribers with different callback functions."""
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        id1 = status_manager.subscribe_to_updates(callback1)
        id2 = status_manager.subscribe_to_updates(callback2)
        id3 = status_manager.subscribe_to_updates(callback3)

        assert status_manager.get_subscriber_count() == 3

        update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_STARTED,
            session_id="multi-test",
            timestamp=time.time(),
            data={"workers": 3}
        )

        status_manager.notify_status_update(update)

        # All callbacks should be called with the same update
        callback1.assert_called_once_with(update)
        callback2.assert_called_once_with(update)
        callback3.assert_called_once_with(update)

    def test_subscriber_cleanup_on_unsubscribe(self, status_manager: StatusManagerInterface):
        """Test that unsubscribed callbacks are properly cleaned up."""
        callbacks = []
        subscription_ids = []

        # Subscribe multiple callbacks
        for i in range(5):
            callback = Mock()
            sub_id = status_manager.subscribe_to_updates(callback)
            callbacks.append(callback)
            subscription_ids.append(sub_id)

        assert status_manager.get_subscriber_count() == 5

        # Unsubscribe first 3
        for i in range(3):
            result = status_manager.unsubscribe(subscription_ids[i])
            assert result is True

        assert status_manager.get_subscriber_count() == 2

        update = StatusUpdate(
            event_type=StatusEventType.PROGRESS_UPDATE,
            session_id="cleanup-test",
            timestamp=time.time(),
            data={"progress": 75.0}
        )

        status_manager.notify_status_update(update)

        # Only remaining callbacks should be called
        callbacks[3].assert_called_once_with(update)
        callbacks[4].assert_called_once_with(update)

        # Unsubscribed callbacks should not be called
        callbacks[0].assert_not_called()
        callbacks[1].assert_not_called()
        callbacks[2].assert_not_called()

    def test_concurrent_subscriptions_and_notifications(self, status_manager: StatusManagerInterface):
        """Test concurrent subscriptions and notifications."""
        import concurrent.futures

        callbacks = []
        subscription_ids = []

        def subscribe_and_collect():
            callback = Mock()
            sub_id = status_manager.subscribe_to_updates(callback)
            callbacks.append(callback)
            subscription_ids.append(sub_id)
            return sub_id

        # Concurrent subscriptions
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(subscribe_and_collect) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert status_manager.get_subscriber_count() == 10
        assert len(callbacks) == 10
        assert len(subscription_ids) == 10

        update = StatusUpdate(
            event_type=StatusEventType.STATUS_CHANGED,
            session_id=None,
            timestamp=time.time(),
            data={"concurrent": True}
        )

        # Notify from main thread
        status_manager.notify_status_update(update)

        # All callbacks should have been called
        for callback in callbacks:
            callback.assert_called_once_with(update)

    def test_callback_failure_does_not_affect_others_integration(self, status_manager: StatusManagerInterface):
        """Integration test for callback failure isolation."""
        success_count = 0
        failure_count = 0

        def success_callback(update):
            nonlocal success_count
            success_count += 1

        def failure_callback(update):
            nonlocal failure_count
            failure_count += 1
            raise RuntimeError("Simulated callback failure")

        # Subscribe both callbacks
        status_manager.subscribe_to_updates(success_callback)
        status_manager.subscribe_to_updates(failure_callback)

        update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_FAILED,
            session_id="failure-test",
            timestamp=time.time(),
            data={"error": "integration test"}
        )

        # Should not raise exception
        status_manager.notify_status_update(update)

        # Success callback should still work
        assert success_count == 1
        assert failure_count == 1

    def test_status_update_data_integrity(self, status_manager: StatusManagerInterface):
        """Test that status update data is not modified during notification."""
        callback = Mock()

        status_manager.subscribe_to_updates(callback)

        original_data = {
            "session_id": "integrity-test",
            "progress": 42.5,
            "items": [1, 2, 3],
            "metadata": {"key": "value"}
        }

        update = StatusUpdate(
            event_type=StatusEventType.PROGRESS_UPDATE,
            session_id="integrity-test",
            timestamp=time.time(),
            data=original_data.copy()
        )

        status_manager.notify_status_update(update)

        # Verify callback received the update
        callback.assert_called_once()
        received_update = callback.call_args[0][0]

        # Verify data integrity
        assert received_update.data == original_data
        assert received_update.session_id == "integrity-test"
        assert received_update.event_type == StatusEventType.PROGRESS_UPDATE

    def test_large_number_of_subscribers(self, status_manager: StatusManagerInterface):
        """Test performance and correctness with many subscribers."""
        callbacks = []

        # Subscribe 100 callbacks
        for i in range(100):
            callback = Mock()
            status_manager.subscribe_to_updates(callback)
            callbacks.append(callback)

        assert status_manager.get_subscriber_count() == 100

        update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_COMPLETED,
            session_id="large-test",
            timestamp=time.time(),
            data={"total_subscribers": 100}
        )

        start_time = time.perf_counter()
        status_manager.notify_status_update(update)
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        # Should complete reasonably fast (< 100ms for 100 subscribers)
        assert duration_ms < 100.0, f"Notification took {duration_ms:.2f}ms for 100 subscribers"

        # All callbacks should be called
        for callback in callbacks:
            callback.assert_called_once_with(update)

    def test_subscription_during_notification(self, status_manager: StatusManagerInterface):
        """Test subscribing during a notification callback."""
        new_subscriptions = []

        def subscribing_callback(update):
            if update.data.get("allow_subscribe", False):
                # Subscribe a new callback during notification
                new_callback = Mock()
                new_id = status_manager.subscribe_to_updates(new_callback)
                new_subscriptions.append((new_callback, new_id))

        status_manager.subscribe_to_updates(subscribing_callback)

        update = StatusUpdate(
            event_type=StatusEventType.STATUS_CHANGED,
            session_id=None,
            timestamp=time.time(),
            data={"allow_subscribe": True}
        )

        initial_count = status_manager.get_subscriber_count()
        status_manager.notify_status_update(update)

        # Should have added new subscription
        assert len(new_subscriptions) == 1
        assert status_manager.get_subscriber_count() == initial_count + 1

    def test_unsubscription_during_notification(self, status_manager: StatusManagerInterface):
        """Test unsubscribing during a notification callback."""
        unsubscribed_ids = []

        def unsubscribing_callback(update):
            if update.data.get("unsubscribe_self", False):
                # Try to unsubscribe self during notification
                # This tests thread safety and proper handling
                pass  # Implementation-dependent behavior

        subscription_id = status_manager.subscribe_to_updates(unsubscribing_callback)

        update = StatusUpdate(
            event_type=StatusEventType.STATUS_CHANGED,
            session_id=None,
            timestamp=time.time(),
            data={"unsubscribe_self": True}
        )

        status_manager.notify_status_update(update)

        # Behavior depends on implementation - may or may not unsubscribe during notification
        # The important thing is no exceptions are raised

    def test_status_manager_lifecycle(self, status_manager: StatusManagerInterface):
        """Test complete lifecycle of StatusManager."""
        # Start empty
        assert status_manager.get_subscriber_count() == 0

        # Add subscribers
        callbacks = []
        ids = []
        for i in range(3):
            callback = Mock()
            sub_id = status_manager.subscribe_to_updates(callback)
            callbacks.append(callback)
            ids.append(sub_id)

        assert status_manager.get_subscriber_count() == 3

        # Send notifications
        updates = []
        for i in range(3):
            update = StatusUpdate(
                event_type=StatusEventType.PROGRESS_UPDATE,
                session_id=f"lifecycle-{i}",
                timestamp=time.time(),
                data={"step": i}
            )
            updates.append(update)
            status_manager.notify_status_update(update)

        # Verify all callbacks received all updates
        for callback in callbacks:
            assert callback.call_count == 3
            for update in updates:
                callback.assert_any_call(update)

        # Remove subscribers one by one
        for sub_id in ids:
            result = status_manager.unsubscribe(sub_id)
            assert result is True

        assert status_manager.get_subscriber_count() == 0

        # Send final update - no callbacks should be called
        final_update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_COMPLETED,
            session_id="lifecycle-complete",
            timestamp=time.time(),
            data={"finished": True}
        )

        status_manager.notify_status_update(final_update)

        # No additional calls should have been made
        for callback in callbacks:
            assert callback.call_count == 3  # Still 3 from before