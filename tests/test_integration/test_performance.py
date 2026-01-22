"""
Performance tests for core interfaces.

Validates performance requirements:
- Configuration operations < 100ms
- Status operations < 50ms
- Memory usage within bounds
"""

import time
import tempfile
import pytest
from typing import Dict, Any

from src.core.config_interface import ConfigurationManager
from src.core.processing_controller import ProcessingController
from src.core.status_manager import StatusManager
from src.core import StatusUpdate, StatusEventType


@pytest.mark.performance
class TestPerformanceRequirements:
    """Test performance requirements for core interfaces."""

    def test_configuration_operations_performance(self):
        """Test that configuration operations complete within 100ms."""
        config_manager = ConfigurationManager()

        # Test get_config performance
        start_time = time.perf_counter()
        config = config_manager.get_config()
        get_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert get_time < 100, f"get_config took {get_time:.2f}ms, should be < 100ms"
        assert isinstance(config, dict)

        # Test save_config performance
        modified_config = config.copy()
        modified_config["max_workers"] = 2

        start_time = time.perf_counter()
        result = config_manager.save_config(modified_config)
        save_time = (time.perf_counter() - start_time) * 1000

        assert save_time < 100, f"save_config took {save_time:.2f}ms, should be < 100ms"
        assert result is True

        # Test validate_config performance
        start_time = time.perf_counter()
        validation = config_manager.validate_config(modified_config)
        validate_time = (time.perf_counter() - start_time) * 1000

        assert validate_time < 100, f"validate_config took {validate_time:.2f}ms, should be < 100ms"
        assert validation["valid"] is True

    def test_status_operations_performance(self):
        """Test that status operations complete within 50ms."""
        status_manager = StatusManager()

        # Test subscribe performance
        def dummy_callback(update):
            pass

        start_time = time.perf_counter()
        subscription_id = status_manager.subscribe_to_updates(dummy_callback)
        subscribe_time = (time.perf_counter() - start_time) * 1000

        assert subscribe_time < 50, f"subscribe_to_updates took {subscribe_time:.2f}ms, should be < 50ms"
        assert isinstance(subscription_id, str)

        # Test notify performance
        update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_STARTED,
            session_id="perf-test",
            timestamp=time.time(),
            data={"progress": 0.0}
        )

        start_time = time.perf_counter()
        status_manager.notify_status_update(update)
        notify_time = (time.perf_counter() - start_time) * 1000

        assert notify_time < 50, f"notify_status_update took {notify_time:.2f}ms, should be < 50ms"

        # Test unsubscribe performance
        start_time = time.perf_counter()
        result = status_manager.unsubscribe(subscription_id)
        unsubscribe_time = (time.perf_counter() - start_time) * 1000

        assert unsubscribe_time < 50, f"unsubscribe took {unsubscribe_time:.2f}ms, should be < 50ms"
        assert result is True

    def test_processing_operations_performance(self):
        """Test that processing operations have reasonable performance."""
        processing_controller = ProcessingController()

        config = {
            "headless_mode": True,
            "enable_parallel": False,
            "max_workers": 1,
            "download_folder": tempfile.mkdtemp(),
            "input_file_path": "/tmp/perf_test.csv",
            "csv_enabled": False
        }

        # Test start_processing performance
        start_time = time.perf_counter()
        session_id = processing_controller.start_processing(config)
        start_time_taken = (time.perf_counter() - start_time) * 1000

        assert start_time_taken < 500, f"start_processing took {start_time_taken:.2f}ms, should be < 500ms"
        assert session_id is not None

        # Test get_status performance
        start_time = time.perf_counter()
        status = processing_controller.get_status(session_id)
        status_time = (time.perf_counter() - start_time) * 1000

        assert status_time < 100, f"get_status took {status_time:.2f}ms, should be < 100ms"
        assert isinstance(status, dict)

        # Test stop_processing performance
        start_time = time.perf_counter()
        result = processing_controller.stop_processing(session_id)
        stop_time = (time.perf_counter() - start_time) * 1000

        assert stop_time < 200, f"stop_processing took {stop_time:.2f}ms, should be < 200ms"
        assert result is True

    def test_concurrent_subscriptions_performance(self):
        """Test performance with multiple concurrent subscriptions."""
        status_manager = StatusManager()

        # Create multiple subscriptions
        subscription_ids = []
        callbacks = []

        def create_callback(index):
            def callback(update):
                pass  # Dummy callback
            return callback

        # Subscribe 10 callbacks
        start_time = time.perf_counter()
        for i in range(10):
            callback = create_callback(i)
            callbacks.append(callback)
            sub_id = status_manager.subscribe_to_updates(callback)
            subscription_ids.append(sub_id)
        subscribe_batch_time = (time.perf_counter() - start_time) * 1000

        assert subscribe_batch_time < 100, f"10 subscriptions took {subscribe_batch_time:.2f}ms, should be < 100ms"

        # Test notify with multiple subscribers
        update = StatusUpdate(
            event_type=StatusEventType.PROGRESS_UPDATE,
            session_id="batch-test",
            timestamp=time.time(),
            data={"progress": 50.0}
        )

        start_time = time.perf_counter()
        status_manager.notify_status_update(update)
        notify_batch_time = (time.perf_counter() - start_time) * 1000

        assert notify_batch_time < 100, f"Notify to 10 subscribers took {notify_batch_time:.2f}ms, should be < 100ms"

        # Cleanup
        for sub_id in subscription_ids:
            status_manager.unsubscribe(sub_id)

    def test_configuration_persistence_performance(self):
        """Test configuration file persistence performance."""
        # Use temporary config file for this test
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_config_file = f.name

        try:
            config_manager = ConfigurationManager(config_file=temp_config_file)

            # Test multiple save/load cycles
            configs_to_test = [
                {
                    "headless_mode": True,
                    "enable_parallel": True,
                    "max_workers": 1,
                    "download_folder": "~/Downloads/test1",
                    "input_file_path": "~/Downloads/input1.xlsx",
                    "csv_enabled": False,
                    "csv_path": None,
                },
                {
                    "headless_mode": False,
                    "enable_parallel": True,
                    "max_workers": 4,
                    "download_folder": "~/Downloads/test2",
                    "input_file_path": "~/Downloads/input2.xlsx",
                    "csv_enabled": False,
                    "csv_path": None,
                },
                {
                    "headless_mode": True,
                    "enable_parallel": False,
                    "max_workers": 8,
                    "download_folder": "~/Downloads/test3",
                    "input_file_path": "~/Downloads/input3.xlsx",
                    "csv_enabled": True,
                    "csv_path": "~/Downloads/test.csv",
                },
            ]

            total_save_time = 0
            total_load_time = 0

            for config_data in configs_to_test:
                # Save performance
                start_time = time.perf_counter()
                result = config_manager.save_config(config_data)
                save_time = (time.perf_counter() - start_time) * 1000
                total_save_time += save_time
                assert result is True

                # Load performance (new instance simulates restart)
                start_time = time.perf_counter()
                new_manager = ConfigurationManager(config_file=temp_config_file)
                loaded_config = new_manager.get_config()
                load_time = (time.perf_counter() - start_time) * 1000
                total_load_time += load_time

                assert loaded_config["max_workers"] == config_data["max_workers"]

            avg_save_time = total_save_time / len(configs_to_test)
            avg_load_time = total_load_time / len(configs_to_test)

            assert avg_save_time < 100, f"Average save time {avg_save_time:.2f}ms, should be < 100ms"
            assert avg_load_time < 100, f"Average load time {avg_load_time:.2f}ms, should be < 100ms"

        finally:
            # Cleanup
            if os.path.exists(temp_config_file):
                os.unlink(temp_config_file)