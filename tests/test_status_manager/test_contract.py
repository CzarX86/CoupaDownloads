"""
Contract tests for StatusManager interface.

Tests the StatusManager contract defined in StatusManagerInterface.
All tests must pass before implementation and after any changes.
"""

import pytest
import time
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock

from src.core.status_manager import StatusManager
from src.core.types import (
    StatusManagerInterface,
    StatusUpdate,
    StatusEventType,
    StatusCallback,
    StatusError
)


class TestStatusManagerContract:
    """Test StatusManager interface contract compliance."""

    @pytest.fixture
    def status_manager(self) -> StatusManagerInterface:
        """Create a StatusManager instance for testing."""
        return StatusManager()

    def test_subscribe_to_updates_returns_subscription_id(self, status_manager: StatusManagerInterface):
        """Test subscribe_to_updates returns a string subscription ID."""
        callback = Mock()
        subscription_id = status_manager.subscribe_to_updates(callback)

        assert isinstance(subscription_id, str)
        assert len(subscription_id) > 0

    def test_unsubscribe_returns_bool(self, status_manager: StatusManagerInterface):
        """Test unsubscribe returns boolean."""
        callback = Mock()
        subscription_id = status_manager.subscribe_to_updates(callback)

        result = status_manager.unsubscribe(subscription_id)
        assert isinstance(result, bool)

    def test_unsubscribe_valid_subscription(self, status_manager: StatusManagerInterface):
        """Test unsubscribe with valid subscription ID."""
        callback = Mock()
        subscription_id = status_manager.subscribe_to_updates(callback)

        result = status_manager.unsubscribe(subscription_id)
        assert result is True

    def test_unsubscribe_invalid_subscription(self, status_manager: StatusManagerInterface):
        """Test unsubscribe with invalid subscription ID."""
        result = status_manager.unsubscribe("invalid-id")
        assert result is False

    def test_notify_status_update_accepts_status_update(self, status_manager: StatusManagerInterface):
        """Test notify_status_update accepts StatusUpdate object."""
        update = StatusUpdate(
            event_type=StatusEventType.STATUS_CHANGED,
            session_id="test-session",
            timestamp=time.time(),
            data={"status": "running"}
        )

        # Should not raise exception
        status_manager.notify_status_update(update)

    def test_get_subscriber_count_returns_int(self, status_manager: StatusManagerInterface):
        """Test get_subscriber_count returns integer."""
        count = status_manager.get_subscriber_count()
        assert isinstance(count, int)
        assert count >= 0

    def test_multiple_subscriptions(self, status_manager: StatusManagerInterface):
        """Test multiple subscriptions work independently."""
        callback1 = Mock()
        callback2 = Mock()

        id1 = status_manager.subscribe_to_updates(callback1)
        id2 = status_manager.subscribe_to_updates(callback2)

        assert id1 != id2

        count = status_manager.get_subscriber_count()
        assert count == 2

    def test_subscription_callback_execution(self, status_manager: StatusManagerInterface):
        """Test that subscribed callbacks are executed on notify."""
        callback = Mock()
        subscription_id = status_manager.subscribe_to_updates(callback)

        update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_STARTED,
            session_id="test-session",
            timestamp=time.time(),
            data={"message": "started"}
        )

        status_manager.notify_status_update(update)

        callback.assert_called_once_with(update)

    def test_unsubscribe_stops_callback_execution(self, status_manager: StatusManagerInterface):
        """Test that unsubscribed callbacks are not executed."""
        callback = Mock()
        subscription_id = status_manager.subscribe_to_updates(callback)

        # Unsubscribe
        result = status_manager.unsubscribe(subscription_id)
        assert result is True

        update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_COMPLETED,
            session_id="test-session",
            timestamp=time.time(),
            data={"message": "completed"}
        )

        status_manager.notify_status_update(update)

        callback.assert_not_called()

    def test_callback_failure_handling(self, status_manager: StatusManagerInterface):
        """Test that callback failures don't break the system."""
        failing_callback = Mock(side_effect=Exception("Callback failed"))
        working_callback = Mock()

        id1 = status_manager.subscribe_to_updates(failing_callback)
        id2 = status_manager.subscribe_to_updates(working_callback)

        update = StatusUpdate(
            event_type=StatusEventType.STATUS_CHANGED,
            session_id=None,
            timestamp=time.time(),
            data={"status": "error"}
        )

        # Should not raise exception despite failing callback
        status_manager.notify_status_update(update)

        # Working callback should still be called
        working_callback.assert_called_once_with(update)

    def test_callback_failure_unsubscribe_after_three_failures(self, status_manager: StatusManagerInterface):
        """Test that callbacks are unsubscribed after 3 consecutive failures."""
        failing_callback = Mock(side_effect=Exception("Persistent failure"))

        subscription_id = status_manager.subscribe_to_updates(failing_callback)

        update = StatusUpdate(
            event_type=StatusEventType.STATUS_CHANGED,
            session_id=None,
            timestamp=time.time(),
            data={"status": "error"}
        )

        # First failure
        status_manager.notify_status_update(update)
        assert status_manager.get_subscriber_count() == 1

        # Second failure
        status_manager.notify_status_update(update)
        assert status_manager.get_subscriber_count() == 1

        # Third failure - should unsubscribe
        status_manager.notify_status_update(update)
        assert status_manager.get_subscriber_count() == 0

    def test_thread_safety_basic(self, status_manager: StatusManagerInterface):
        """Test basic thread safety of subscription operations."""
        import threading
        import time

        results = []
        errors = []

        def subscribe_worker():
            try:
                callback = Mock()
                sub_id = status_manager.subscribe_to_updates(callback)
                results.append(("subscribe", sub_id))
            except Exception as e:
                errors.append(("subscribe", str(e)))

        def unsubscribe_worker(sub_id):
            try:
                result = status_manager.unsubscribe(sub_id)
                results.append(("unsubscribe", result))
            except Exception as e:
                errors.append(("unsubscribe", str(e)))

        # Start multiple subscription threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=subscribe_worker)
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        # Should have 5 subscriptions
        assert status_manager.get_subscriber_count() == 5
        assert len(results) == 5
        assert len(errors) == 0

    @pytest.mark.performance
    def test_notify_performance(self, status_manager: StatusManagerInterface):
        """Test that notify operations complete within performance requirements (<50ms)."""
        # Subscribe multiple callbacks
        callbacks = []
        for i in range(10):
            callback = Mock()
            status_manager.subscribe_to_updates(callback)
            callbacks.append(callback)

        update = StatusUpdate(
            event_type=StatusEventType.PROGRESS_UPDATE,
            session_id="perf-test",
            timestamp=time.time(),
            data={"progress": 50.0}
        )

        start_time = time.perf_counter()
        status_manager.notify_status_update(update)
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000

        # Should complete in less than 50ms
        assert duration_ms < 50.0, f"Notification took {duration_ms:.2f}ms, exceeds 50ms limit"

        # All callbacks should have been called
        for callback in callbacks:
            callback.assert_called_once_with(update)

    def test_status_update_event_types(self, status_manager: StatusManagerInterface):
        """Test that all StatusEventType values are handled."""
        callback = Mock()
        status_manager.subscribe_to_updates(callback)

        for event_type in StatusEventType:
            update = StatusUpdate(
                event_type=event_type,
                session_id="test-session" if event_type != StatusEventType.STATUS_CHANGED else None,
                timestamp=time.time(),
                data={"test": True}
            )

            status_manager.notify_status_update(update)
            callback.assert_called_with(update)

    def test_subscription_id_uniqueness(self, status_manager: StatusManagerInterface):
        """Test that subscription IDs are unique."""
        callback = Mock()

        ids = set()
        for i in range(100):
            sub_id = status_manager.subscribe_to_updates(callback)
            assert sub_id not in ids
            ids.add(sub_id)

        assert len(ids) == 100

    def test_empty_subscriptions_no_errors(self, status_manager: StatusManagerInterface):
        """Test that notifying with no subscriptions doesn't cause errors."""
        update = StatusUpdate(
            event_type=StatusEventType.STATUS_CHANGED,
            session_id=None,
            timestamp=time.time(),
            data={"status": "idle"}
        )

        # Should not raise exception
        status_manager.notify_status_update(update)

    def test_callback_exception_isolation(self, status_manager: StatusManagerInterface):
        """Test that one callback exception doesn't affect others."""
        exception_callback = Mock(side_effect=ValueError("Test exception"))
        normal_callback1 = Mock()
        normal_callback2 = Mock()

        status_manager.subscribe_to_updates(exception_callback)
        status_manager.subscribe_to_updates(normal_callback1)
        status_manager.subscribe_to_updates(normal_callback2)

        update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_FAILED,
            session_id="test-session",
            timestamp=time.time(),
            data={"error": "test"}
        )

        # Should not raise exception
        status_manager.notify_status_update(update)

        # Normal callbacks should still be called
        normal_callback1.assert_called_once_with(update)
        normal_callback2.assert_called_once_with(update)