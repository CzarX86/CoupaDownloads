"""
Tests for core interface types and contracts.

This module tests the shared types and abstract base classes to ensure
they provide the expected contracts for the three core interfaces.
"""

import pytest
from src.core.types import (
    ProcessingStatus,
    StatusEventType,
    ProcessingProgress,
    ConfigurationData,
    StatusUpdate,
    ConfigurationManagerInterface,
    ProcessingControllerInterface,
    StatusManagerInterface,
    InterfaceError,
    ConfigurationError,
    ProcessingError,
    StatusError,
)


class TestEnums:
    """Test enumeration types."""

    def test_processing_status_values(self):
        """Test ProcessingStatus enum has expected values."""
        expected_values = {"idle", "running", "paused", "completed", "failed", "stopped"}
        actual_values = {status.value for status in ProcessingStatus}
        assert actual_values == expected_values

    def test_status_event_type_values(self):
        """Test StatusEventType enum has expected values."""
        expected_values = {
            "processing_started", "processing_completed", "processing_failed",
            "progress_update", "status_changed"
        }
        actual_values = {event.value for event in StatusEventType}
        assert actual_values == expected_values


class TestDataClasses:
    """Test data class structures."""

    def test_processing_progress_creation(self):
        """Test ProcessingProgress can be created with valid data."""
        progress = ProcessingProgress(
            session_id="test-session-123",
            status=ProcessingStatus.RUNNING,
            total_tasks=10,
            completed_tasks=5,
            failed_tasks=1,
            active_tasks=2,
            elapsed_time=45.5,
            estimated_remaining=30.0,
            processing_mode="parallel",
            worker_details={"worker1": "active"}
        )

        assert progress.session_id == "test-session-123"
        assert progress.status == ProcessingStatus.RUNNING
        assert progress.total_tasks == 10
        assert progress.completed_tasks == 5
        assert progress.failed_tasks == 1
        assert progress.active_tasks == 2
        assert progress.elapsed_time == 45.5
        assert progress.estimated_remaining == 30.0
        assert progress.processing_mode == "parallel"
        assert progress.worker_details == {"worker1": "active"}

    def test_configuration_data_creation(self):
        """Test ConfigurationData can be created with valid data."""
        config = ConfigurationData(
            headless_mode=True,
            enable_parallel=False,
            max_workers=2,
            download_folder="/tmp/downloads",
            input_file_path="/tmp/input.csv",
            csv_enabled=True,
            csv_path="/tmp/input.csv"
        )

        assert config.headless_mode is True
        assert config.enable_parallel is False
        assert config.max_workers == 2
        assert config.download_folder == "/tmp/downloads"
        assert config.input_file_path == "/tmp/input.csv"
        assert config.csv_enabled is True
        assert config.csv_path == "/tmp/input.csv"

    def test_status_update_creation(self):
        """Test StatusUpdate can be created with valid data."""
        update = StatusUpdate(
            event_type=StatusEventType.PROGRESS_UPDATE,
            session_id="session-456",
            timestamp=1234567890.0,
            data={"progress": 75}
        )

        assert update.event_type == StatusEventType.PROGRESS_UPDATE
        assert update.session_id == "session-456"
        assert update.timestamp == 1234567890.0
        assert update.data == {"progress": 75}


class TestAbstractInterfaces:
    """Test that abstract interfaces cannot be instantiated directly."""

    def test_configuration_manager_abstract(self):
        """Test ConfigurationManagerInterface is abstract."""
        with pytest.raises(TypeError, match="abstract"):
            ConfigurationManagerInterface()

    def test_processing_controller_abstract(self):
        """Test ProcessingControllerInterface is abstract."""
        with pytest.raises(TypeError, match="abstract"):
            ProcessingControllerInterface()

    def test_status_manager_abstract(self):
        """Test StatusManagerInterface is abstract."""
        with pytest.raises(TypeError, match="abstract"):
            StatusManagerInterface()


class TestExceptions:
    """Test custom exception types."""

    def test_interface_error_hierarchy(self):
        """Test exception hierarchy."""
        assert issubclass(ConfigurationError, InterfaceError)
        assert issubclass(ProcessingError, InterfaceError)
        assert issubclass(StatusError, InterfaceError)

    def test_exception_creation(self):
        """Test exceptions can be created with messages."""
        error = InterfaceError("Test error")
        assert str(error) == "Test error"

        config_error = ConfigurationError("Config problem")
        assert str(config_error) == "Config problem"
        assert isinstance(config_error, InterfaceError)

        processing_error = ProcessingError("Processing failed")
        assert str(processing_error) == "Processing failed"
        assert isinstance(processing_error, InterfaceError)

        status_error = StatusError("Status error")
        assert str(status_error) == "Status error"
        assert isinstance(status_error, InterfaceError)