"""
Thread safety validation tests for core interfaces.

Ensures all interfaces are safe for concurrent access from UI threads.
"""

import threading
import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from src.core.config_interface import ConfigurationManager
from src.core.processing_controller import ProcessingController
from src.core.status_manager import StatusManager
from src.core import StatusUpdate, StatusEventType


@pytest.mark.thread_safety
class TestThreadSafety:
    """Test thread safety of core interfaces for UI integration."""

    def test_configuration_manager_thread_safety(self):
        """Test ConfigurationManager is thread-safe under concurrent access."""
        config_manager = ConfigurationManager()

        results = []
        errors = []

        def worker(worker_id: int):
            try:
                # Each worker performs multiple operations
                for i in range(10):
                    # Read operation
                    config = config_manager.get_config()
                    assert isinstance(config, dict)

                    # Modify and save - ensure all required fields are present
                    modified = config.copy()
                    modified["max_workers"] = worker_id * 10 + i + 1  # Ensure >= 1
                    # Ensure all required fields are present
                    required_fields = {
                        "headless_mode", "enable_parallel", "max_workers",
                        "download_folder", "input_file_path"
                    }
                    for field in required_fields:
                        if field not in modified:
                            modified[field] = config.get(field, "")
                    result = config_manager.save_config(modified)
                    if not result:
                        validation = config_manager.validate_config(modified)
                        errors.append(f"worker_{worker_id}: save failed, validation: {validation}")
                        continue
                    assert result is True

                    # Validate
                    validation = config_manager.validate_config(modified)
                    assert validation["valid"] is True

                    results.append(f"worker_{worker_id}_iter_{i}")

            except Exception as e:
                errors.append(f"worker_{worker_id}: {e}")

        # Run 5 workers concurrently
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 50  # 5 workers * 10 iterations each

    def test_status_manager_thread_safety(self):
        """Test StatusManager is thread-safe with concurrent subscriptions and notifications."""
        status_manager = StatusManager()

        received_updates = []
        subscription_errors = []

        def subscriber_callback(update):
            received_updates.append(update)

        def subscription_worker(worker_id: int):
            try:
                # Subscribe
                sub_id = status_manager.subscribe_to_updates(subscriber_callback)
                assert isinstance(sub_id, str)

                # Wait a bit for notifications
                time.sleep(0.1)

                # Unsubscribe
                result = status_manager.unsubscribe(sub_id)
                assert result is True

            except Exception as e:
                subscription_errors.append(f"sub_worker_{worker_id}: {e}")

        def notification_worker(worker_id: int):
            try:
                # Send multiple notifications
                for i in range(5):
                    update = StatusUpdate(
                        event_type=StatusEventType.PROGRESS_UPDATE,
                        session_id=f"thread_test_{worker_id}",
                        timestamp=time.time(),
                        data={"progress": i * 20, "worker": worker_id}
                    )
                    status_manager.notify_status_update(update)
                    time.sleep(0.01)  # Small delay between notifications

            except Exception as e:
                subscription_errors.append(f"notify_worker_{worker_id}: {e}")

        # Start notification thread
        notify_thread = threading.Thread(target=notification_worker, args=(0,))
        notify_thread.start()

        # Start multiple subscription threads
        sub_threads = []
        for i in range(3):
            t = threading.Thread(target=subscription_worker, args=(i,))
            sub_threads.append(t)
            t.start()

        # Wait for all threads
        notify_thread.join()
        for t in sub_threads:
            t.join()

        # Verify no errors
        assert len(subscription_errors) == 0, f"Thread safety errors: {subscription_errors}"

        # Verify updates were received (at least some, depending on timing)
        assert len(received_updates) > 0, "No updates were received by subscribers"

        # Verify all received updates are valid
        for update in received_updates:
            assert isinstance(update, StatusUpdate)
            assert update.event_type == StatusEventType.PROGRESS_UPDATE
            assert "progress" in update.data

    def test_processing_controller_thread_safety(self):
        """Test ProcessingController handles concurrent status requests safely."""
        processing_controller = ProcessingController()

        # Start a processing session
        config = {
            "headless_mode": True,
            "enable_parallel": False,
            "max_workers": 1,
            "download_folder": "/tmp/thread_test",
            "input_file_path": "/tmp/thread_test.csv",
            "csv_enabled": False
        }

        session_id = processing_controller.start_processing(config)
        assert session_id is not None

        status_results = []
        status_errors = []

        def status_worker(worker_id: int):
            try:
                # Each worker requests status multiple times
                for i in range(20):
                    status = processing_controller.get_status(session_id)
                    assert isinstance(status, dict)
                    status_results.append(f"worker_{worker_id}_iter_{i}: {status.get('state', 'unknown')}")

            except Exception as e:
                status_errors.append(f"status_worker_{worker_id}: {e}")

        # Run multiple status request threads concurrently
        threads = []
        for i in range(5):
            t = threading.Thread(target=status_worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors
        assert len(status_errors) == 0, f"Thread safety errors: {status_errors}"
        assert len(status_results) == 100  # 5 workers * 20 requests each

        # Clean up
        processing_controller.stop_processing(session_id)

    def test_cross_interface_thread_safety(self):
        """Test thread safety when all interfaces are used together."""
        config_manager = ConfigurationManager()
        processing_controller = ProcessingController()
        status_manager = StatusManager()

        operation_results = []
        operation_errors = []

        def ui_worker(worker_id: int):
            """Simulates UI thread operations."""
            try:
                # Subscribe to status updates
                updates_received = []

                def status_callback(update):
                    updates_received.append(update)

                sub_id = status_manager.subscribe_to_updates(status_callback)

                # Perform configuration operations
                config = config_manager.get_config()
                modified_config = config.copy()
                modified_config["max_workers"] = worker_id + 1
                config_manager.save_config(modified_config)

                # Start processing if not already started
                session_id = f"ui_session_{worker_id}"
                try:
                    proc_session = processing_controller.start_processing(modified_config)
                    if proc_session:
                        # Get status
                        status = processing_controller.get_status(proc_session)
                        operation_results.append(f"ui_{worker_id}_started_processing")

                        # Send some status updates
                        update = StatusUpdate(
                            event_type=StatusEventType.PROCESSING_STARTED,
                            session_id=proc_session,
                            timestamp=time.time(),
                            data={"ui_worker": worker_id}
                        )
                        status_manager.notify_status_update(update)

                        # Stop processing
                        processing_controller.stop_processing(proc_session)
                        operation_results.append(f"ui_{worker_id}_stopped_processing")
                    else:
                        operation_results.append(f"ui_{worker_id}_processing_not_started")
                except RuntimeError as e:
                    # Processing already running or other validation error
                    operation_results.append(f"ui_{worker_id}_processing_already_active")
                    # Still try to get status if we can determine session
                    try:
                        # Just get status of any active session
                        status = processing_controller.get_status("any")
                        operation_results.append(f"ui_{worker_id}_checked_status")
                    except:
                        pass

                # Unsubscribe
                status_manager.unsubscribe(sub_id)

                # Verify some updates were received
                if len(updates_received) > 0:
                    operation_results.append(f"ui_{worker_id}_received_{len(updates_received)}_updates")

            except Exception as e:
                operation_errors.append(f"ui_worker_{worker_id}: {e}")

        def background_worker(worker_id: int):
            """Simulates background processing operations."""
            try:
                # Send periodic status updates
                for i in range(3):
                    update = StatusUpdate(
                        event_type=StatusEventType.PROGRESS_UPDATE,
                        session_id=f"bg_session_{worker_id}",
                        timestamp=time.time(),
                        data={"progress": (i + 1) * 33, "bg_worker": worker_id}
                    )
                    status_manager.notify_status_update(update)
                    time.sleep(0.01)

                operation_results.append(f"bg_{worker_id}_sent_updates")

                # Try to read configuration
                config = config_manager.get_config()
                assert isinstance(config, dict)
                operation_results.append(f"bg_{worker_id}_read_config")

            except Exception as e:
                operation_errors.append(f"bg_worker_{worker_id}: {e}")

        # Start background workers
        bg_threads = []
        for i in range(2):
            t = threading.Thread(target=background_worker, args=(i,))
            bg_threads.append(t)
            t.start()

        # Start UI workers
        ui_threads = []
        for i in range(3):
            t = threading.Thread(target=ui_worker, args=(i,))
            ui_threads.append(t)
            t.start()

        # Wait for all threads
        for t in bg_threads + ui_threads:
            t.join()

        # Verify no errors occurred
        assert len(operation_errors) == 0, f"Cross-interface thread safety errors: {operation_errors}"

        # Verify operations completed
        assert len(operation_results) > 0, "No operations completed successfully"

        # Verify we have results from both UI and background workers
        ui_results = [r for r in operation_results if r.startswith("ui_")]
        bg_results = [r for r in operation_results if r.startswith("bg_")]

        assert len(ui_results) > 0, "No UI worker operations completed"
        assert len(bg_results) > 0, "No background worker operations completed"

    def test_subscription_failure_handling(self):
        """Test that failing subscribers don't break the status manager."""
        status_manager = StatusManager()

        call_counts = {"good": 0, "bad": 0}

        def good_callback(update):
            call_counts["good"] += 1

        def bad_callback(update):
            call_counts["bad"] += 1
            raise Exception("Subscriber failed")

        # Subscribe both callbacks
        good_sub = status_manager.subscribe_to_updates(good_callback)
        bad_sub = status_manager.subscribe_to_updates(bad_callback)

        # Send update - bad callback should fail but not break the system
        update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_STARTED,
            session_id="failure_test",
            timestamp=time.time(),
            data={}
        )

        # This should not raise an exception
        status_manager.notify_status_update(update)

        # Good callback should have been called
        assert call_counts["good"] == 1

        # Bad callback should have been called once but not yet unsubscribed (needs 3 failures)
        assert call_counts["bad"] == 1

        # Send second update
        status_manager.notify_status_update(update)
        assert call_counts["good"] == 2
        assert call_counts["bad"] == 2

        # Send third update - bad callback should be unsubscribed after this
        status_manager.notify_status_update(update)
        assert call_counts["good"] == 3
        assert call_counts["bad"] == 3

        # Send fourth update - bad callback should not be called again
        status_manager.notify_status_update(update)
        assert call_counts["good"] == 4
        assert call_counts["bad"] == 3  # Still 3, not called again

        # Clean up
        status_manager.unsubscribe(good_sub)