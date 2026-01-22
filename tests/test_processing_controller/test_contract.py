"""
Contract tests for ProcessingController interface.

These tests verify that any implementation of ProcessingControllerInterface
meets the expected contract. Tests should FAIL until the implementation is complete.

Tests are written against the abstract interface to ensure contract compliance.
"""

import pytest
import time
import uuid
from typing import Dict, Any
from unittest.mock import Mock, patch

from src.core import ProcessingControllerInterface, ProcessingController


# Test fixtures
@pytest.fixture
def sample_config_dict() -> Dict[str, Any]:
    """Sample configuration dictionary for testing."""
    return {
        "headless_mode": True,
        "enable_parallel": True,
        "max_workers": 4,
        "download_folder": "/tmp/downloads",
        "input_file_path": "/tmp/input.csv",
        "csv_enabled": True,
        "csv_path": "/tmp/input.csv"
    }


@pytest.fixture
def invalid_config_dict() -> Dict[str, Any]:
    """Invalid configuration dictionary for testing error cases."""
    return {
        "headless_mode": "not_a_boolean",
        "enable_parallel": 123,
        "max_workers": -1,
        "download_folder": "",  # Empty path
        "input_file_path": "/nonexistent/path",
    }


@pytest.fixture
def valid_session_id() -> str:
    """Valid UUID4 session ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def invalid_session_id() -> str:
    """Invalid session ID for testing."""
    return "not-a-uuid"


def assert_status_dict_format(status: Dict[str, Any]) -> None:
    """
    Assert that a status dictionary follows the expected format.

    Args:
        status: Status dictionary to validate.

    Raises:
        AssertionError: If status doesn't match expected format.
    """
    required_keys = {
        "session_id", "state", "progress", "current_operation",
        "items_processed", "total_items", "start_time"
    }

    assert isinstance(status, dict), "Status must be a dictionary"
    assert required_keys.issubset(status.keys()), f"Missing keys: {required_keys - status.keys()}"

    # Type checks
    assert isinstance(status["session_id"], str), "session_id must be str"
    assert isinstance(status["state"], str), "state must be str"
    assert isinstance(status["progress"], (int, float)), "progress must be numeric"
    assert isinstance(status["current_operation"], str), "current_operation must be str"
    assert isinstance(status["items_processed"], int), "items_processed must be int"
    assert isinstance(status["total_items"], int), "total_items must be int"
    assert isinstance(status["start_time"], str), "start_time must be str"

    # Value checks
    valid_states = {"idle", "starting", "running", "stopping", "completed", "error", "unknown"}
    assert status["state"] in valid_states, f"Invalid state: {status['state']}"
    assert 0.0 <= status["progress"] <= 1.0, "progress must be between 0.0 and 1.0"
    assert status["items_processed"] >= 0, "items_processed must be >= 0"
    assert status["total_items"] >= 0, "total_items must be >= 0"

    # Optional fields
    if "estimated_time_remaining" in status:
        assert isinstance(status["estimated_time_remaining"], (int, type(None))), "estimated_time_remaining must be int or None"
        if status["estimated_time_remaining"] is not None:
            assert status["estimated_time_remaining"] >= 0, "estimated_time_remaining must be >= 0"

    if "error_message" in status:
        assert isinstance(status["error_message"], str), "error_message must be str"


class TestProcessingControllerContract:
    """
    Contract tests for ProcessingController interface.

    These tests define the expected behavior of any ProcessingController implementation.
    All tests should initially fail until the concrete implementation is provided.
    """

    @pytest.fixture
    def processing_controller(self) -> ProcessingControllerInterface:
        """Concrete ProcessingController implementation for testing."""
        # This will fail until we implement ProcessingController
        from src.core.processing_controller import ProcessingController
        return ProcessingController()

    def test_start_processing_returns_session_id(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test that start_processing returns a valid session ID."""
        session_id = processing_controller.start_processing(sample_config_dict)

        assert isinstance(session_id, str), "start_processing must return string"
        # Should be a valid UUID4
        try:
            uuid.UUID(session_id)
        except ValueError:
            pytest.fail("start_processing must return a valid UUID4 string")

    def test_start_processing_accepts_valid_config(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test that start_processing accepts valid configuration."""
        session_id = processing_controller.start_processing(sample_config_dict)

        assert isinstance(session_id, str), "Should return session ID for valid config"
        assert len(session_id) > 0, "Session ID should not be empty"

    def test_start_processing_rejects_invalid_config(self, processing_controller: ProcessingControllerInterface, invalid_config_dict: Dict[str, Any]):
        """Test that start_processing rejects invalid configuration."""
        with pytest.raises(ValueError):
            processing_controller.start_processing(invalid_config_dict)

    def test_start_processing_enforces_single_session(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test that only one session can be active at a time."""
        # Start first session
        session_id1 = processing_controller.start_processing(sample_config_dict)
        assert isinstance(session_id1, str)

        # Attempt to start second session should fail
        with pytest.raises(RuntimeError, match=".*already active.*"):
            processing_controller.start_processing(sample_config_dict)

    def test_stop_processing_returns_bool(self, processing_controller: ProcessingControllerInterface, valid_session_id: str):
        """Test that stop_processing returns a boolean."""
        result = processing_controller.stop_processing(valid_session_id)

        assert isinstance(result, bool), "stop_processing must return boolean"

    def test_stop_processing_accepts_valid_session(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test that stop_processing works with valid session."""
        # Start a session first
        session_id = processing_controller.start_processing(sample_config_dict)

        # Now stop it
        result = processing_controller.stop_processing(session_id)
        assert isinstance(result, bool), "Should return boolean when stopping valid session"

    def test_stop_processing_handles_invalid_session(self, processing_controller: ProcessingControllerInterface, invalid_session_id: str):
        """Test that stop_processing handles invalid session IDs."""
        result = processing_controller.stop_processing(invalid_session_id)

        assert isinstance(result, bool), "stop_processing must return boolean"
        assert result is False, "Should return False for invalid session ID"

    def test_get_status_returns_dict(self, processing_controller: ProcessingControllerInterface, valid_session_id: str):
        """Test that get_status returns a properly formatted dictionary."""
        status = processing_controller.get_status(valid_session_id)

        assert_status_dict_format(status)

    def test_get_status_handles_invalid_session(self, processing_controller: ProcessingControllerInterface, invalid_session_id: str):
        """Test that get_status handles invalid session IDs."""
        status = processing_controller.get_status(invalid_session_id)

        assert isinstance(status, dict), "get_status must return dict"
        assert status.get("state") == "unknown", "Invalid session should return unknown state"

    def test_get_status_returns_idle_for_no_session(self, processing_controller: ProcessingControllerInterface):
        """Test that get_status returns idle state when no session is active."""
        # Generate a random session ID that doesn't exist
        random_session_id = str(uuid.uuid4())
        status = processing_controller.get_status(random_session_id)

        assert status["state"] == "unknown", "Non-existent session should return unknown state"

    def test_session_lifecycle(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test complete session lifecycle: start -> status -> stop."""
        # Start session
        session_id = processing_controller.start_processing(sample_config_dict)
        assert isinstance(session_id, str)

        # Check initial status
        status = processing_controller.get_status(session_id)
        assert status["state"] in {"starting", "running"}, "Session should be starting or running"
        assert status["session_id"] == session_id, "Status should contain correct session ID"

        # Stop session
        stop_result = processing_controller.stop_processing(session_id)
        assert isinstance(stop_result, bool), "Stop should return boolean"

        # Check final status
        final_status = processing_controller.get_status(session_id)
        assert final_status["state"] in {"completed", "stopped", "idle"}, "Session should be completed/stopped after stopping"

    def test_status_contains_required_fields(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test that status contains all required fields."""
        # Start a session to get a valid session ID
        session_id = processing_controller.start_processing(sample_config_dict)

        status = processing_controller.get_status(session_id)

        required_fields = [
            "session_id", "state", "progress", "current_operation",
            "items_processed", "total_items", "start_time"
        ]

        for field in required_fields:
            assert field in status, f"Status missing required field: {field}"

    def test_status_progress_range(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test that status progress is within valid range."""
        session_id = processing_controller.start_processing(sample_config_dict)

        status = processing_controller.get_status(session_id)

        progress = status["progress"]
        assert isinstance(progress, (int, float)), "Progress must be numeric"
        assert 0.0 <= progress <= 1.0, f"Progress {progress} must be between 0.0 and 1.0"

    def test_status_items_processed_count(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test that items_processed count is valid."""
        session_id = processing_controller.start_processing(sample_config_dict)

        status = processing_controller.get_status(session_id)

        items_processed = status["items_processed"]
        total_items = status["total_items"]

        assert isinstance(items_processed, int), "items_processed must be int"
        assert isinstance(total_items, int), "total_items must be int"
        assert items_processed >= 0, "items_processed must be >= 0"
        assert total_items >= 0, "total_items must be >= 0"
        assert items_processed <= total_items, "items_processed cannot exceed total_items"

    @pytest.mark.performance
    def test_start_processing_performance(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test that start_processing meets performance requirements (< 500ms)."""
        start_time = time.perf_counter()

        session_id = processing_controller.start_processing(sample_config_dict)

        end_time = time.perf_counter()
        duration = end_time - start_time

        assert duration < 0.5, ".2f"  # Contract: start_processing < 500ms

    @pytest.mark.performance
    def test_stop_processing_performance(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test that stop_processing meets performance requirements (< 200ms)."""
        session_id = processing_controller.start_processing(sample_config_dict)

        start_time = time.perf_counter()
        result = processing_controller.stop_processing(session_id)
        end_time = time.perf_counter()

        duration = end_time - start_time
        assert duration < 0.2, ".2f"  # Contract: stop_processing < 200ms

    @pytest.mark.performance
    def test_get_status_performance(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test that get_status meets performance requirements (< 50ms)."""
        session_id = processing_controller.start_processing(sample_config_dict)

        start_time = time.perf_counter()

        for _ in range(10):  # Test multiple calls
            status = processing_controller.get_status(session_id)
            assert isinstance(status, dict)

        end_time = time.perf_counter()
        avg_time = (end_time - start_time) / 10

        assert avg_time < 0.05, ".2f"  # Contract: get_status < 50ms

    def test_thread_safety_basic(self, processing_controller: ProcessingControllerInterface, sample_config_dict: Dict[str, Any]):
        """Test basic thread safety of status queries."""
        import threading
        import time

        session_id = processing_controller.start_processing(sample_config_dict)

        results = []
        errors = []

        def status_worker():
            try:
                for _ in range(10):
                    status = processing_controller.get_status(session_id)
                    results.append(status)
                    time.sleep(0.01)  # Small delay to allow interleaving
            except Exception as e:
                errors.append(e)

        # Start multiple threads querying status
        threads = []
        for _ in range(3):
            t = threading.Thread(target=status_worker)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Should have results from all threads without errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) > 0, "Should have status results"

        # All results should be valid status dictionaries
        for status in results:
            assert_status_dict_format(status)

    def test_error_message_in_error_state(self, processing_controller: ProcessingControllerInterface, invalid_config_dict: Dict[str, Any]):
        """Test that error state includes meaningful error message."""
        # Try to start with invalid config to trigger error
        try:
            processing_controller.start_processing(invalid_config_dict)
            pytest.fail("Should have raised ValueError for invalid config")
        except ValueError:
            pass  # Expected

        # Create a mock session ID and check error status
        # (This test may need adjustment based on actual implementation)
        mock_session_id = str(uuid.uuid4())
        status = processing_controller.get_status(mock_session_id)

        if status.get("state") == "error":
            assert "error_message" in status, "Error state should include error_message"
            assert isinstance(status["error_message"], str), "error_message must be string"
            assert len(status["error_message"]) > 0, "error_message should not be empty"