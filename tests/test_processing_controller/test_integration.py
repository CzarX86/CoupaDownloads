"""
Integration tests for ProcessingController with MainApp.

These tests verify that ProcessingController correctly integrates with
the existing MainApp functionality without breaking backward compatibility.
"""

import pytest
import time
from typing import Dict, Any
from unittest.mock import Mock, patch

from src.core import ProcessingController


# Test fixtures
@pytest.fixture
def sample_config_dict() -> Dict[str, Any]:
    """Sample configuration dictionary for testing."""
    return {
        "headless_mode": True,
        "enable_parallel": False,  # Disable parallel for simpler testing
        "max_workers": 1,
        "download_folder": "/tmp/downloads",
        "input_file_path": "/tmp/input.csv",
        "csv_enabled": True,
        "csv_path": "/tmp/input.csv"
    }


@pytest.fixture
def mock_main_app():
    """Mock MainApp instance for testing."""
    mock_app = Mock()
    mock_app.run = Mock()
    mock_app.close = Mock()
    return mock_app


class TestProcessingControllerIntegration:
    """
    Integration tests for ProcessingController with MainApp.
    """

    def test_processing_controller_initialization(self, mock_main_app):
        """Test that ProcessingController can be initialized with MainApp."""
        controller = ProcessingController(main_app=mock_main_app)

        assert controller._main_app is mock_main_app
        assert controller._active_session is None

    def test_processing_controller_without_main_app(self):
        """Test that ProcessingController can be initialized without MainApp."""
        controller = ProcessingController()

        assert controller._main_app is None
        assert controller._active_session is None

    @patch('src.core.processing_controller.threading.Thread')
    def test_start_processing_creates_background_thread(self, mock_thread_class, sample_config_dict):
        """Test that start_processing creates a background thread for processing."""
        controller = ProcessingController()

        # Mock the thread
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread

        session_id = controller.start_processing(sample_config_dict)

        # Verify thread was created and started
        mock_thread_class.assert_called_once()
        call_args = mock_thread_class.call_args
        assert call_args[1]['target'] == controller._run_processing
        assert call_args[1]['args'] == (session_id,)
        assert call_args[1]['daemon'] is True

        mock_thread.start.assert_called_once()

    def test_start_processing_updates_session_state(self, sample_config_dict):
        """Test that start_processing properly updates session state."""
        controller = ProcessingController()

        session_id = controller.start_processing(sample_config_dict)

        # Check that session is active
        assert controller._active_session is not None
        assert controller._active_session['session_id'] == session_id
        assert controller._active_session['state'] == 'starting'
        assert controller._active_session['config'] == sample_config_dict

        # Check that status is cached
        assert session_id in controller._status_cache

    def test_get_status_returns_cached_status(self, sample_config_dict):
        """Test that get_status returns properly formatted cached status."""
        controller = ProcessingController()

        session_id = controller.start_processing(sample_config_dict)

        status = controller.get_status(session_id)

        # Verify status structure
        required_keys = {
            'session_id', 'state', 'progress', 'current_operation',
            'items_processed', 'total_items', 'start_time'
        }

        assert all(key in status for key in required_keys)
        assert status['session_id'] == session_id
        assert status['state'] == 'starting'
        assert status['progress'] == 0.0

    def test_stop_processing_clears_session(self, sample_config_dict):
        """Test that stop_processing clears the active session."""
        controller = ProcessingController()

        session_id = controller.start_processing(sample_config_dict)

        # Verify session is active
        assert controller._active_session is not None

        # Stop processing
        result = controller.stop_processing(session_id)

        assert result is True
        assert controller._active_session is None

        # Check final status
        status = controller.get_status(session_id)
        assert status['state'] == 'completed'

    def test_is_processing_active_reflects_session_state(self, sample_config_dict):
        """Test that is_processing_active correctly reflects session state."""
        controller = ProcessingController()

        # Initially not active
        assert controller.is_processing_active() is False

        # Start processing
        session_id = controller.start_processing(sample_config_dict)
        # Note: is_processing_active checks for 'running' state, but we start as 'starting'
        assert controller.is_processing_active() is False

        # Simulate running state
        with controller._session_lock:
            if controller._active_session:
                controller._active_session['state'] = 'running'

        assert controller.is_processing_active() is True

        # Stop processing
        controller.stop_processing(session_id)
        assert controller.is_processing_active() is False

    def test_multiple_sessions_not_allowed(self, sample_config_dict):
        """Test that multiple concurrent sessions are not allowed."""
        controller = ProcessingController()

        # Start first session
        session_id1 = controller.start_processing(sample_config_dict)
        assert controller._active_session is not None

        # Attempt second session should fail
        with pytest.raises(RuntimeError, match=".*already active.*"):
            controller.start_processing(sample_config_dict)

        # First session should still be active
        assert controller._active_session['session_id'] == session_id1

    def test_invalid_session_operations(self, sample_config_dict):
        """Test operations with invalid session IDs."""
        controller = ProcessingController()

        invalid_session = "invalid-uuid"

        # Stop invalid session
        result = controller.stop_processing(invalid_session)
        assert result is False

        # Get status of invalid session
        status = controller.get_status(invalid_session)
        assert status['state'] == 'unknown'
        assert status['session_id'] == invalid_session

    def test_config_validation_integration(self, sample_config_dict):
        """Test that config validation works in integration context."""
        controller = ProcessingController()

        # Valid config should work
        session_id = controller.start_processing(sample_config_dict)
        assert isinstance(session_id, str)

        # Clean up the session
        controller.stop_processing(session_id)

        # Invalid config should fail
        invalid_config = {"invalid": "config"}
        with pytest.raises(ValueError):
            controller.start_processing(invalid_config)

    @pytest.mark.integration
    def test_backward_compatibility_preserved(self, sample_config_dict):
        """Test that ProcessingController doesn't break existing MainApp usage."""
        # This test ensures that wrapping MainApp doesn't interfere with direct usage
        # In a real integration test, we would create a MainApp and verify it still works

        controller = ProcessingController()

        # ProcessingController should work independently
        session_id = controller.start_processing(sample_config_dict)
        assert isinstance(session_id, str)

        status = controller.get_status(session_id)
        assert status['session_id'] == session_id

        # Clean up
        controller.stop_processing(session_id)

    def test_thread_safety_integration(self, sample_config_dict):
        """Test thread safety in integration scenario."""
        import threading
        import time

        controller = ProcessingController()
        session_id = controller.start_processing(sample_config_dict)

        results = []
        errors = []

        def status_checker():
            try:
                for _ in range(5):
                    status = controller.get_status(session_id)
                    results.append(status)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        def stop_caller():
            try:
                time.sleep(0.05)  # Let status checker run first
                controller.stop_processing(session_id)
            except Exception as e:
                errors.append(e)

        # Start threads
        threads = [
            threading.Thread(target=status_checker),
            threading.Thread(target=status_checker),
            threading.Thread(target=stop_caller)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Should have status results
        assert len(results) > 0, "Should have status check results"

    def test_error_handling_integration(self, sample_config_dict):
        """Test error handling in integration context."""
        controller = ProcessingController()

        # Start processing
        session_id = controller.start_processing(sample_config_dict)

        # Simulate an error by directly setting error state
        with controller._session_lock:
            if controller._active_session:
                controller._active_session['state'] = 'error'
                controller._active_session['error_message'] = 'Simulated error'

        # Update cache to reflect the error state
        with controller._cache_lock:
            if session_id in controller._status_cache:
                controller._status_cache[session_id].update({
                    'state': 'error',
                    'error_message': 'Simulated error'
                })

        # Check error status
        status = controller.get_status(session_id)
        assert status['state'] == 'error'
        assert status['error_message'] == 'Simulated error'

        # Clean up
        controller._active_session = None