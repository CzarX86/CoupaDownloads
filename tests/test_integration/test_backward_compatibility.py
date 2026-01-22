"""
Backward compatibility tests for core interfaces.

Tests that the new interfaces maintain compatibility with existing CLI usage patterns
and don't break expected workflows.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.core import ConfigurationManager, ProcessingController, StatusManager


@pytest.mark.integration
class TestBackwardCompatibility:
    """Test backward compatibility with existing CLI patterns."""

    def test_configuration_manager_replaces_direct_config_access(self):
        """Test ConfigurationManager provides same interface as direct config access."""
        config_manager = ConfigurationManager()

        # Test that it provides the same configuration structure as expected by CLI
        config = config_manager.get_config()

        # Verify required CLI configuration keys are present
        required_keys = {
            "headless_mode", "enable_parallel", "max_workers",
            "download_folder", "input_file_path"
        }

        for key in required_keys:
            assert key in config, f"Missing required config key: {key}"

        # Test configuration persistence (like CLI would use)
        modified_config = config.copy()
        modified_config["max_workers"] = 5
        modified_config["headless_mode"] = False

        assert config_manager.save_config(modified_config) is True

        # Verify persistence
        loaded_config = config_manager.get_config()
        assert loaded_config["max_workers"] == 5
        assert loaded_config["headless_mode"] is False

    def test_processing_controller_replaces_direct_mainapp_calls(self):
        """Test ProcessingController provides same interface as direct MainApp calls."""
        processing_controller = ProcessingController()

        # Test configuration validation (like CLI would do)
        valid_config = {
            "headless_mode": True,
            "enable_parallel": False,
            "max_workers": 2,
            "download_folder": "/tmp/test_downloads",
            "input_file_path": "/tmp/test_input.csv",
            "csv_enabled": False
        }

        # Should accept valid config
        session_id = processing_controller.start_processing(valid_config)
        assert isinstance(session_id, str)
        assert len(session_id) > 0

        # Should be able to get status (like CLI status checks)
        status = processing_controller.get_status(session_id)
        assert isinstance(status, dict)
        assert "session_id" in status
        assert "state" in status

        # Should be able to stop (like CLI stop command)
        stopped = processing_controller.stop_processing(session_id)
        assert stopped is True

    def test_status_manager_provides_ui_integration_points(self):
        """Test StatusManager provides the callback integration points UI needs."""
        status_manager = StatusManager()

        # Test subscription system (UI would use this for real-time updates)
        callback_calls = []

        def ui_callback(update):
            callback_calls.append(update)

        subscription_id = status_manager.subscribe_to_updates(ui_callback)
        assert isinstance(subscription_id, str)

        # Simulate status updates that would come from processing
        from src.core import StatusUpdate, StatusEventType
        import time

        update = StatusUpdate(
            event_type=StatusEventType.PROCESSING_STARTED,
            session_id="test-session",
            timestamp=time.time(),
            data={"progress": 0.0}
        )

        status_manager.notify_status_update(update)

        # UI callback should have been called
        assert len(callback_calls) == 1
        assert callback_calls[0].event_type == StatusEventType.PROCESSING_STARTED

        # Test unsubscription (UI cleanup)
        unsubscribed = status_manager.unsubscribe(subscription_id)
        assert unsubscribed is True

        # Further updates should not call the callback
        update2 = StatusUpdate(
            event_type=StatusEventType.PROGRESS_UPDATE,
            session_id="test-session",
            timestamp=time.time(),
            data={"progress": 50.0}
        )

        status_manager.notify_status_update(update2)
        assert len(callback_calls) == 1  # Still only 1 call

    def test_interface_composition_matches_cli_workflow(self):
        """Test that interface composition matches expected CLI workflow."""
        # Create all interfaces
        config_manager = ConfigurationManager()
        processing_controller = ProcessingController()
        status_manager = StatusManager()

        # Simulate complete CLI workflow using interfaces
        workflow_events = []

        def workflow_callback(update):
            workflow_events.append(update)

        # 1. Setup status monitoring (CLI would do this)
        sub_id = status_manager.subscribe_to_updates(workflow_callback)

        # 2. Load configuration (CLI startup)
        config = config_manager.get_config()
        config.update({
            "headless_mode": True,
            "enable_parallel": False,
            "max_workers": 1,
            "download_folder": tempfile.mkdtemp(),
            "input_file_path": "/tmp/test.csv",
            "csv_enabled": False
        })

        # 3. Start processing (CLI run command)
        session_id = processing_controller.start_processing(config)

        # 4. Simulate processing lifecycle events (real processing would send these)
        from src.core import StatusUpdate, StatusEventType
        import time

        events_to_send = [
            StatusEventType.PROCESSING_STARTED,
            StatusEventType.PROGRESS_UPDATE,
            StatusEventType.PROCESSING_COMPLETED
        ]

        for event_type in events_to_send:
            update = StatusUpdate(
                event_type=event_type,
                session_id=session_id,
                timestamp=time.time(),
                data={"step": event_type.value}
            )
            status_manager.notify_status_update(update)

        # 5. Check final status (CLI status command)
        final_status = processing_controller.get_status(session_id)
        # Processing may still be running or completed, but should have valid state
        assert final_status["state"] in ["starting", "running", "completed", "failed"]

        # 6. Cleanup (CLI shutdown)
        processing_controller.stop_processing(session_id)
        status_manager.unsubscribe(sub_id)

        # Verify workflow completed with expected events
        assert len(workflow_events) == 3
        event_types = [e.event_type for e in workflow_events]
        assert StatusEventType.PROCESSING_STARTED in event_types
        assert StatusEventType.PROGRESS_UPDATE in event_types
        assert StatusEventType.PROCESSING_COMPLETED in event_types

    def test_error_handling_maintains_cli_compatibility(self):
        """Test that error handling maintains CLI compatibility."""
        processing_controller = ProcessingController()

        # Test invalid configuration (CLI would validate this)
        invalid_config = {"invalid": "config"}

        with pytest.raises(ValueError):
            processing_controller.start_processing(invalid_config)

        # Test invalid session operations (CLI would handle gracefully)
        invalid_stop = processing_controller.stop_processing("nonexistent-session")
        assert invalid_stop is False

        invalid_status = processing_controller.get_status("nonexistent-session")
        # Should return some indication of invalid session
        assert isinstance(invalid_status, dict)

    def test_configuration_file_integration(self):
        """Test configuration file integration matches CLI expectations."""
        config_manager = ConfigurationManager()

        # Test default configuration loading
        config = config_manager.get_config()
        assert isinstance(config, dict)

        # Test configuration modification and persistence
        original_max_workers = config.get("max_workers", 1)
        config["max_workers"] = original_max_workers + 1

        assert config_manager.save_config(config) is True

        # Verify persistence across instances (like CLI restart)
        new_config_manager = ConfigurationManager()
        loaded_config = new_config_manager.get_config()
        assert loaded_config["max_workers"] == original_max_workers + 1

        # Test configuration validation
        invalid_config = {"max_workers": "not_a_number"}
        validation = config_manager.validate_config(invalid_config)
        assert validation["valid"] is False

        # Test reset to defaults
        assert config_manager.reset_to_defaults() is True
        reset_config = config_manager.get_config()
        assert reset_config["max_workers"] == 4  # DEFAULT_CONFIG value

    def test_processing_isolation_between_sessions(self):
        """Test that processing sessions are properly isolated (CLI requirement)."""
        processing_controller = ProcessingController()

        config = {
            "headless_mode": True,
            "enable_parallel": False,
            "max_workers": 1,
            "download_folder": "/tmp/iso_test",
            "input_file_path": "/tmp/iso_test.csv",
            "csv_enabled": False
        }

        # Start first session
        session1 = processing_controller.start_processing(config)
        assert session1 is not None

        # Attempt to start second session (should fail - single session constraint)
        with pytest.raises(RuntimeError):
            processing_controller.start_processing(config)

        # Stop first session
        processing_controller.stop_processing(session1)

        # Now second session should work
        session2 = processing_controller.start_processing(config)
        assert session2 is not None
        assert session2 != session1  # Different session

        # Clean up
        processing_controller.stop_processing(session2)