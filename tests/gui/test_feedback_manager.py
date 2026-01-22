"""
Test Feedback Manager Contract

Contract tests for the feedback manager to ensure it meets the interface requirements.
Tests the contract defined in contracts/feedback-manager-contract.md.
"""

import sys
from pathlib import Path

# Set up path before any imports
project_root = Path(__file__).resolve().parents[2]
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest
import threading
import time
from unittest.mock import Mock


class TestFeedbackManagerContract:
    """Contract tests for FeedbackManager."""

    def setup_method(self):
        """Set up test environment."""
        # Imports moved to individual test methods to avoid module-level import issues
        self.feedback_manager = None
        self.config = None

    def teardown_method(self):
        """Clean up test environment."""
        if self.feedback_manager:
            self.feedback_manager.shutdown()
            self.feedback_manager = None

    def test_initialization_contract(self):
        """Test that feedback manager can be initialized with config."""
        from src.ui.data_model import UIFeedbackConfig
        from src.ui.feedback_manager import FeedbackManager
        
        self.feedback_manager = FeedbackManager()
        self.config = UIFeedbackConfig(enable_progress_bars=True, max_error_history=5)

        # When
        self.feedback_manager.initialize(self.config)

        # Then - should not raise exception
        assert True  # If we get here, initialization succeeded

    def test_operation_lifecycle_contract(self):
        """Test complete operation lifecycle."""
        from src.ui.feedback_manager import FeedbackManager
        from src.ui.data_model import UIFeedbackConfig

        self.feedback_manager = FeedbackManager()
        self.config = UIFeedbackConfig()
        self.feedback_manager.initialize(self.config)

        # When - start operation
        self.feedback_manager.start_operation("test_operation")

        # Then - operation should be marked as active
        time.sleep(0.1)  # Allow message processing
        state = self.feedback_manager.get_current_state()
        assert state['is_active'] == True        # When - complete operation
        self.feedback_manager.complete_operation(success=True)

        # Then - operation should be marked as inactive
        time.sleep(0.1)  # Allow message processing
        state = self.feedback_manager.get_current_state()
        assert state['is_active'] == False

    def test_progress_update_contract(self):
        """Test progress data updates."""
        from src.ui.data_model import ProgressData
        from src.ui.feedback_manager import FeedbackManager
        from src.ui.data_model import UIFeedbackConfig
        
        # Given
        self.feedback_manager = FeedbackManager()
        self.config = UIFeedbackConfig()
        self.feedback_manager.initialize(self.config)
        progress_data = ProgressData(
            total_files=10,
            completed_files=3,
            current_file="test.pdf"
        )

        # When
        self.feedback_manager.update_progress(progress_data)

        # Then - progress should be stored
        time.sleep(0.1)  # Allow processing
        state = self.feedback_manager.get_current_state()
        assert state['progress_data'].total_files == 10
        assert state['progress_data'].completed_files == 3
        assert state['progress_data'].progress_percentage == 30.0

    def test_status_message_contract(self):
        """Test status message updates."""
        from src.ui.data_model import StatusMessage, StatusType
        from src.ui.feedback_manager import FeedbackManager
        from src.ui.data_model import UIFeedbackConfig

        # Given
        self.feedback_manager = FeedbackManager()
        self.config = UIFeedbackConfig()
        self.feedback_manager.initialize(self.config)
        status = StatusMessage(
            message_type=StatusType.INFO,
            title="Test Status",
            message="This is a test status message"
        )

        # When
        self.feedback_manager.update_status(status)

        # Then - status should be stored
        time.sleep(0.1)  # Allow processing
        state = self.feedback_manager.get_current_state()
        assert state['current_status'].title == "Test Status"
        assert state['current_status'].message == "This is a test status message"

    def test_error_reporting_contract(self):
        """Test error reporting functionality."""
        from src.ui.data_model import ErrorInfo, ErrorType
        
        # Given
        self.feedback_manager.initialize(self.config)
        error = ErrorInfo(
            error_type=ErrorType.NETWORK_ERROR,
            user_message="Network connection failed",
            technical_details="Connection timeout after 30 seconds"
        )

        # When
        self.feedback_manager.report_error(error)

        # Then - error should be stored in history
        time.sleep(0.1)  # Allow processing
        state = self.feedback_manager.get_current_state()
        assert len(state['error_history']) > 0
        assert state['error_history'][0].user_message == "Network connection failed"

    def test_statistics_update_contract(self):
        """Test statistics updates."""
        from src.ui.data_model import DownloadStatistics
        
        # Given
        self.feedback_manager.initialize(self.config)
        stats = DownloadStatistics(
            total_files=5,
            successful_downloads=4,
            failed_downloads=1,
            total_bytes_downloaded=1024000
        )

        # When
        self.feedback_manager.update_statistics(stats)

        # Then - statistics should be stored
        time.sleep(0.1)  # Allow processing
        state = self.feedback_manager.get_current_state()
        assert state['statistics'].total_files == 5
        assert state['statistics'].success_rate == 80.0

    def test_callback_registration_contract(self):
        """Test callback registration and notification."""
        from src.ui.data_model import ProgressData
        
        # Given
        self.feedback_manager.initialize(self.config)
        mock_callback = Mock()
        event_type = "progress_update"

        # When - register callback
        self.feedback_manager.register_callback(event_type, mock_callback)

        # And send update
        progress_data = ProgressData(total_files=1, completed_files=1)
        self.feedback_manager.update_progress(progress_data)

        # Then - callback should be called
        time.sleep(0.2)  # Allow async processing
        mock_callback.assert_called()

    def test_callback_unregistration_contract(self):
        """Test callback unregistration."""
        from src.ui.data_model import ProgressData
        
        # Given
        self.feedback_manager.initialize(self.config)
        mock_callback = Mock()
        event_type = "progress_update"

        # When - register then unregister callback
        self.feedback_manager.register_callback(event_type, mock_callback)
        self.feedback_manager.unregister_callback(event_type, mock_callback)

        # And send update
        progress_data = ProgressData(total_files=1, completed_files=1)
        self.feedback_manager.update_progress(progress_data)

        # Then - callback should not be called
        time.sleep(0.2)  # Allow async processing
        mock_callback.assert_not_called()

    def test_state_snapshot_contract(self):
        """Test that state snapshots are provided correctly."""
        # Given
        self.feedback_manager.initialize(self.config)

        # When
        state = self.feedback_manager.get_current_state()

        # Then - state should contain expected keys
        required_keys = ['progress_data', 'current_status', 'statistics', 'error_history', 'is_active', 'last_update']
        for key in required_keys:
            assert key in state

    def test_thread_safety_contract(self):
        """Test that operations are thread-safe."""
        from src.ui.data_model import ProgressData, StatusMessage, StatusType, ErrorInfo, ErrorType
        
        # Given
        self.feedback_manager.initialize(self.config)

        # When - perform operations from multiple threads
        results = []

        def worker_thread(thread_id):
            try:
                # Each thread performs different operations
                if thread_id == 0:
                    self.feedback_manager.update_progress(ProgressData(total_files=1, completed_files=1))
                elif thread_id == 1:
                    status = StatusMessage(StatusType.INFO, "Thread status", "From thread")
                    self.feedback_manager.update_status(status)
                elif thread_id == 2:
                    error = ErrorInfo(ErrorType.UNKNOWN_ERROR, "Thread error", "From thread")
                    self.feedback_manager.report_error(error)

                results.append(f"Thread {thread_id}: success")
            except Exception as e:
                results.append(f"Thread {thread_id}: error - {e}")

        # Start multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker_thread, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Then - all operations should succeed
        assert len(results) == 3
        for result in results:
            assert "success" in result

    def test_shutdown_contract(self):
        """Test proper shutdown behavior."""
        # Given
        self.feedback_manager.initialize(self.config)

        # When
        self.feedback_manager.shutdown()

        # Then - should not raise exceptions and should clean up
        assert True  # If we get here, shutdown succeeded

        # Further operations should not cause issues
        try:
            self.feedback_manager.get_current_state()
        except Exception:
            # It's OK if shutdown prevents further operations
            pass

    def test_metrics_calculation_contract(self):
        """Test that feedback manager correctly calculates metrics."""
        from src.ui.data_model import UIFeedbackConfig, DownloadStatistics, ProgressData
        from src.ui.feedback_manager import FeedbackManager
        from datetime import datetime, timedelta
        
        self.feedback_manager = FeedbackManager()
        self.config = UIFeedbackConfig()
        self.feedback_manager.initialize(self.config)

        # Test progress metrics
        progress = ProgressData(
            total_files=10,
            completed_files=7,
            total_bytes=10485760,  # 10 MB
            bytes_downloaded=7340032,  # 7 MB
            start_time=datetime.now() - timedelta(minutes=2)
        )

        self.feedback_manager.update_progress(progress)

        # Test statistics metrics
        stats = DownloadStatistics(
            total_files=10,
            successful_downloads=8,
            failed_downloads=2,
            total_bytes_downloaded=8388608,  # 8 MB
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now()
        )

        self.feedback_manager.update_statistics(stats)

        # Get current state
        state = self.feedback_manager.get_current_state()

        # Contract: Should contain calculated metrics
        assert 'progress' in state
        assert 'statistics' in state

        # Progress calculations
        progress_data = state['progress']
        assert progress_data['progress_percentage'] == 70.0  # 7/10
        assert progress_data['current_file_progress'] == 70.0  # 7MB/10MB

        # Statistics calculations
        stats_data = state['statistics']
        assert stats_data['success_rate'] == 80.0  # 8/10
        assert stats_data['total_duration'] is not None
        assert isinstance(stats_data['total_duration'], timedelta)