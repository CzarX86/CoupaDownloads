"""
Integration tests for all three core interfaces working together.

Tests the complete interface ecosystem with realistic usage patterns.
"""

import pytest
import time
import threading
from typing import Dict, Any, List
from unittest.mock import Mock

from src.core import (
    ConfigurationManager,
    ProcessingController,
    StatusManager,
    StatusUpdate,
    StatusEventType,
    ProcessingStatus
)


@pytest.mark.integration
class TestCoreInterfacesIntegration:
    """Test all three interfaces working together."""

    @pytest.fixture
    def config_manager(self) -> ConfigurationManager:
        """Create ConfigurationManager instance."""
        return ConfigurationManager()

    @pytest.fixture
    def processing_controller(self) -> ProcessingController:
        """Create ProcessingController instance."""
        return ProcessingController()

    @pytest.fixture
    def status_manager(self) -> StatusManager:
        """Create StatusManager instance."""
        return StatusManager()

    def test_complete_workflow_with_status_updates(
        self,
        config_manager: ConfigurationManager,
        processing_controller: ProcessingController,
        status_manager: StatusManager
    ):
        """Test complete workflow: config -> processing -> status updates."""
        # Setup status monitoring (manual integration - UI would do this)
        status_updates = []
        def status_callback(update: StatusUpdate):
            status_updates.append(update)

        subscription_id = status_manager.subscribe_to_updates(status_callback)

        # 1. Configure processing
        config = {
            "headless_mode": True,
            "enable_parallel": False,
            "max_workers": 1,
            "download_folder": "/tmp/test",
            "input_file_path": "/tmp/test.csv",
            "csv_enabled": False
        }

        config_saved = config_manager.save_config(config)
        assert config_saved is True

        retrieved_config = config_manager.get_config()
        assert retrieved_config["headless_mode"] is True
        assert retrieved_config["max_workers"] == 1

        # 2. Start processing
        session_id = processing_controller.start_processing(retrieved_config)
        assert isinstance(session_id, str)
        assert len(session_id) > 0

        # Manually send status update (UI would do this based on processing events)
        update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_STARTED,
            session_id=session_id,
            timestamp=time.time(),
            data={"message": "Processing started"}
        )
        status_manager.notify_status_update(update)

        # Should have received processing started update
        assert len(status_updates) >= 1
        start_update = status_updates[0]
        assert start_update.event_type == StatusEventType.PROCESSING_STARTED
        assert start_update.session_id == session_id

        # 3. Check processing status
        status = processing_controller.get_status(session_id)
        assert isinstance(status, dict)
        assert status["session_id"] == session_id
        assert status["state"] in ["starting", "running", "completed", "failed"]

        # 4. Stop processing
        stopped = processing_controller.stop_processing(session_id)
        assert stopped is True

        # Manually send completion update
        completion_update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_COMPLETED,
            session_id=session_id,
            timestamp=time.time(),
            data={"message": "Processing completed"}
        )
        status_manager.notify_status_update(completion_update)

        # Should have received processing completed update
        completion_updates = [u for u in status_updates if u.event_type == StatusEventType.PROCESSING_COMPLETED]
        assert len(completion_updates) >= 1

        # 5. Verify final status
        final_status = processing_controller.get_status(session_id)
        assert final_status["state"] in ["completed", "stopped", "failed"]

        # Cleanup
        status_manager.unsubscribe(subscription_id)

    def test_configuration_persistence_across_interfaces(
        self,
        config_manager: ConfigurationManager,
        processing_controller: ProcessingController
    ):
        """Test configuration persistence works across interface usage."""
        # Set configuration
        config = {
            "headless_mode": False,
            "enable_parallel": True,
            "max_workers": 3,
            "download_folder": "/tmp/persist_test",
            "input_file_path": "/tmp/persist.csv",
            "csv_enabled": True,
            "csv_path": "/tmp/persist.csv"
        }

        assert config_manager.save_config(config) is True

        # Use configuration in processing
        retrieved_config = config_manager.get_config()
        session_id = processing_controller.start_processing(retrieved_config)
        assert session_id is not None

        # Stop processing
        processing_controller.stop_processing(session_id)

        # Verify configuration still persists
        final_config = config_manager.get_config()
        assert final_config["enable_parallel"] is True
        assert final_config["max_workers"] == 3
        assert final_config["csv_enabled"] is True

    def test_status_updates_during_processing_lifecycle(
        self,
        processing_controller: ProcessingController,
        status_manager: StatusManager
    ):
        """Test status updates throughout processing lifecycle."""
        updates_received = []
        def capture_updates(update: StatusUpdate):
            updates_received.append(update)

        subscription_id = status_manager.subscribe_to_updates(capture_updates)

        # Start processing
        config = {
            "headless_mode": True,
            "enable_parallel": False,
            "max_workers": 1,
            "download_folder": "/tmp/lifecycle",
            "input_file_path": "/tmp/lifecycle.csv",
            "csv_enabled": False
        }

        session_id = processing_controller.start_processing(config)

        # Manually send status updates (UI would monitor processing and send updates)
        status_manager.notify_status_update(StatusUpdate(
            event_type=StatusEventType.PROCESSING_STARTED,
            session_id=session_id,
            timestamp=time.time(),
            data={"message": "started"}
        ))

        # Wait a bit for processing to start
        time.sleep(0.1)

        # Stop processing
        processing_controller.stop_processing(session_id)

        # Send completion update
        status_manager.notify_status_update(StatusUpdate(
            event_type=StatusEventType.PROCESSING_COMPLETED,
            session_id=session_id,
            timestamp=time.time(),
            data={"message": "completed"}
        ))

        # Verify we received status updates
        assert len(updates_received) >= 2  # At least start and completion

        event_types = [u.event_type for u in updates_received]
        assert StatusEventType.PROCESSING_STARTED in event_types
        assert StatusEventType.PROCESSING_COMPLETED in event_types

        # All updates should have the same session_id
        session_ids = [u.session_id for u in updates_received]
        assert all(sid == session_id for sid in session_ids if sid is not None)

        # Cleanup
        status_manager.unsubscribe(subscription_id)

    def test_thread_safety_across_interfaces(
        self,
        config_manager: ConfigurationManager,
        processing_controller: ProcessingController,
        status_manager: StatusManager
    ):
        """Test thread safety when using all interfaces concurrently."""
        results = []
        errors = []

        def worker_thread(thread_id: int):
            try:
                # Each thread creates its own ProcessingController instance
                from src.core import ProcessingController as PC
                thread_processing_controller = PC()

                # Each thread does a complete workflow
                config = {
                    "headless_mode": True,
                    "enable_parallel": False,
                    "max_workers": 1,
                    "download_folder": f"/tmp/thread_{thread_id}",
                    "input_file_path": f"/tmp/thread_{thread_id}.csv",
                    "csv_enabled": False
                }

                # Configure (shared config_manager)
                config_saved = config_manager.save_config(config)
                results.append(("config", thread_id, config_saved))

                # Subscribe to updates (shared status_manager)
                updates = []
                def update_callback(update: StatusUpdate):
                    updates.append(update)

                sub_id = status_manager.subscribe_to_updates(update_callback)

                # Start processing (own processing_controller)
                session_id = thread_processing_controller.start_processing(config_manager.get_config())
                results.append(("start", thread_id, session_id))

                # Send manual status update
                status_manager.notify_status_update(StatusUpdate(
                    event_type=StatusEventType.PROCESSING_STARTED,
                    session_id=session_id,
                    timestamp=time.time(),
                    data={"thread": thread_id}
                ))

                # Wait briefly
                time.sleep(0.05)

                # Stop processing
                stopped = thread_processing_controller.stop_processing(session_id)
                results.append(("stop", thread_id, stopped))

                # Send completion update
                status_manager.notify_status_update(StatusUpdate(
                    event_type=StatusEventType.PROCESSING_COMPLETED,
                    session_id=session_id,
                    timestamp=time.time(),
                    data={"thread": thread_id}
                ))

                # Unsubscribe
                unsubscribed = status_manager.unsubscribe(sub_id)
                results.append(("unsubscribe", thread_id, unsubscribed))

                # Verify updates received
                results.append(("updates", thread_id, len(updates)))

            except Exception as e:
                errors.append((thread_id, str(e)))

        # Run multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker_thread, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        # Verify results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 25  # 5 results per thread

        # Check that all operations succeeded
        for result_type, thread_id, value in results:
            if result_type in ["config", "stop", "unsubscribe"]:
                assert value is True, f"{result_type} failed for thread {thread_id}"
            elif result_type == "start":
                assert isinstance(value, str), f"Invalid session_id for thread {thread_id}"
            elif result_type == "updates":
                assert value >= 2, f"Insufficient updates for thread {thread_id}: {value}"

    def test_error_handling_integration(
        self,
        config_manager: ConfigurationManager,
        processing_controller: ProcessingController,
        status_manager: StatusManager
    ):
        """Test error handling across all interfaces."""
        # Test invalid configuration
        invalid_config = {"invalid": "config"}
        validation = config_manager.validate_config(invalid_config)
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0

        # Test processing with invalid config should fail
        with pytest.raises(ValueError):
            processing_controller.start_processing(invalid_config)

        # Test status updates with invalid data
        with pytest.raises(ValueError):
            status_manager.notify_status_update("invalid update")  # type: ignore

        # Test invalid subscription operations
        invalid_unsubscribe = status_manager.unsubscribe("nonexistent-id")
        assert invalid_unsubscribe is False

    def test_performance_requirements_integration(
        self,
        config_manager: ConfigurationManager,
        processing_controller: ProcessingController,
        status_manager: StatusManager
    ):
        """Test that all interfaces meet performance requirements."""
        # Configuration operations < 100ms
        config = {
            "headless_mode": True,
            "enable_parallel": False,
            "max_workers": 1,
            "download_folder": "/tmp/perf",
            "input_file_path": "/tmp/perf.csv",
            "csv_enabled": False
        }

        # Test config save/get performance
        start_time = time.perf_counter()
        config_manager.save_config(config)
        config_manager.get_config()
        config_manager.validate_config(config)
        end_time = time.perf_counter()

        config_duration = (end_time - start_time) * 1000
        assert config_duration < 100.0, f"Config operations took {config_duration:.2f}ms"

        # Status operations < 50ms
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

        status_duration = (end_time - start_time) * 1000
        assert status_duration < 50.0, f"Status notification took {status_duration:.2f}ms"

        # All callbacks should have been called
        for callback in callbacks:
            callback.assert_called_once_with(update)

    def test_interface_isolation(
        self,
        config_manager: ConfigurationManager,
        processing_controller: ProcessingController,
        status_manager: StatusManager
    ):
        """Test that interfaces remain isolated and don't interfere with each other."""
        # Start with clean state
        assert status_manager.get_subscriber_count() == 0

        # Use each interface independently
        config = config_manager.get_config()
        assert isinstance(config, dict)

        # Subscribe to status updates
        callback = Mock()
        sub_id = status_manager.subscribe_to_updates(callback)
        assert status_manager.get_subscriber_count() == 1

        # Start processing (don't check is_processing_active since timing is unpredictable)
        session_id = processing_controller.start_processing(config)
        assert isinstance(session_id, str)

        # Stop processing
        stopped = processing_controller.stop_processing(session_id)
        assert stopped is True

        # Unsubscribe
        status_manager.unsubscribe(sub_id)
        assert status_manager.get_subscriber_count() == 0

        # Verify each interface still works independently
        new_config = config_manager.get_config()
        assert new_config == config

        new_sub_id = status_manager.subscribe_to_updates(callback)
        assert status_manager.get_subscriber_count() == 1
        status_manager.unsubscribe(new_sub_id)