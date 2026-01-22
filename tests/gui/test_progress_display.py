"""
Test Progress Display Component

Integration tests for the progress display UI component.
Tests the component's ability to display progress information correctly.
"""

import pytest
import tkinter as tk
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Import the components we're testing
from src.ui.data_model import ProgressData, StatusMessage, StatusType
from src.ui.feedback_manager import FeedbackManager
from src.utils.ui_helpers import ProgressFormatter


class TestProgressDisplayIntegration:
    """Integration tests for progress display component."""

    def setup_method(self):
        """Set up test environment."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window during tests
        self.feedback_manager = FeedbackManager()

    def teardown_method(self):
        """Clean up test environment."""
        if self.root:
            self.root.destroy()
        if self.feedback_manager:
            self.feedback_manager.shutdown()

    def test_progress_display_initialization(self):
        """Test that progress display initializes correctly."""
        from src.ui.components.progress_display import ProgressDisplay
        from src.ui.data_model import UIFeedbackConfig

        # Create config
        config = UIFeedbackConfig()

        # Should be able to import and create the component
        progress_display = ProgressDisplay(self.root, config)

        # Should have the expected attributes
        assert hasattr(progress_display, 'progress_bar')
        assert hasattr(progress_display, 'current_file_label')
        assert hasattr(progress_display, 'progress_text_label')

        # Should be properly initialized
        assert progress_display.progress_bar is not None
        assert progress_display.current_file_label is not None
        assert progress_display.progress_text_label is not None

    def test_progress_formatting(self):
        """Test progress formatting utilities."""
        # Test percentage formatting
        assert ProgressFormatter.format_percentage(75.5) == "75.5%"
        assert ProgressFormatter.format_percentage(100.0) == "100.0%"

        # Test file size formatting
        assert ProgressFormatter.format_file_size(1024) == "1.0 KB"
        assert ProgressFormatter.format_file_size(1048576) == "1.0 MB"
        assert ProgressFormatter.format_file_size(0) == "0 B"

        # Test time remaining formatting
        assert ProgressFormatter.format_time_remaining(30) == "30s remaining"
        assert ProgressFormatter.format_time_remaining(90) == "1m 30s remaining"
        assert ProgressFormatter.format_time_remaining(3660) == "1h 1m remaining"
        assert ProgressFormatter.format_time_remaining(None) == "Calculating..."

    def test_feedback_manager_progress_updates(self):
        """Test that feedback manager handles progress updates."""
        progress_data = ProgressData(
            total_files=5,
            completed_files=2,
            current_file="document.pdf",
            bytes_downloaded=512000,
            total_bytes=1024000
        )

        # Update progress
        self.feedback_manager.update_progress(progress_data)

        # Give it a moment to process
        import time
        time.sleep(0.1)

        # Check state
        state = self.feedback_manager.get_current_state()
        assert state['progress_data'].total_files == 5
        assert state['progress_data'].completed_files == 2
        assert state['progress_data'].progress_percentage == 40.0

    def test_progress_display_with_mock_component(self):
        """Test progress display behavior with a mock component."""
        # Create mock progress display component
        mock_display = Mock()
        mock_display.update_progress = Mock()

        # Register mock as callback
        self.feedback_manager.register_callback('progress_update', mock_display.update_progress)

        # Send progress update
        progress_data = ProgressData(
            total_files=3,
            completed_files=1,
            current_file="test.pdf"
        )
        self.feedback_manager.update_progress(progress_data)

        # Give it time to process
        import time
        time.sleep(0.2)

        # Verify callback was called
        mock_display.update_progress.assert_called()

    def test_progress_display_error_handling(self):
        """Test progress display handles errors gracefully."""
        # Test with invalid progress data
        invalid_progress = ProgressData(
            total_files=0,  # This should not cause division by zero
            completed_files=0
        )

        assert invalid_progress.progress_percentage == 0.0

        # Test with negative values
        negative_progress = ProgressData(
            total_files=-1,
            completed_files=0
        )

        assert negative_progress.progress_percentage == 0.0

    def test_progress_display_performance(self):
        """Test that progress updates don't cause performance issues."""
        import time

        start_time = time.time()

        # Send multiple rapid progress updates
        for i in range(10):
            progress_data = ProgressData(
                total_files=10,
                completed_files=i,
                current_file=f"file_{i}.pdf"
            )
            self.feedback_manager.update_progress(progress_data)

        # Give time to process
        time.sleep(0.5)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time (less than 1 second for 10 updates)
        assert duration < 1.0

        # Check final state
        state = self.feedback_manager.get_current_state()
        assert state['progress_data'].completed_files == 9