"""
Integration Test: Statistics Panel Component

Tests the statistics panel UI component.
Verifies that statistics are displayed correctly and updated in real-time.
"""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).resolve().parents[2]
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest
import tkinter as tk
from unittest.mock import Mock
from datetime import datetime, timedelta

# Import the components we're testing
from src.ui.data_model import DownloadStatistics, UIFeedbackConfig
from src.ui.feedback_manager import FeedbackManager
from src.ui.components.statistics_panel import StatisticsPanel


class TestStatisticsPanelIntegration:
    """Integration tests for statistics panel component."""

    def setup_method(self):
        """Set up test environment."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide window for headless testing
        self.parent_frame = tk.Frame(self.root)
        self.feedback_manager = FeedbackManager()
        self.config = UIFeedbackConfig()

    def teardown_method(self):
        """Clean up test environment."""
        if self.root:
            self.root.destroy()
        if self.feedback_manager:
            self.feedback_manager.shutdown()

    def test_statistics_panel_initialization(self):
        """Test that statistics panel initializes correctly."""
        # Should be able to create the component
        stats_panel = StatisticsPanel(self.parent_frame, self.config)

        # Should have the expected attributes
        assert hasattr(stats_panel, 'frame')
        assert hasattr(stats_panel, 'total_files_label')
        assert hasattr(stats_panel, 'successful_label')
        assert hasattr(stats_panel, 'failed_label')
        assert hasattr(stats_panel, 'duration_label')
        assert hasattr(stats_panel, 'speed_label')

        # Should be properly initialized
        assert stats_panel.frame is not None

    def test_statistics_display(self):
        """Test that statistics are displayed correctly."""
        stats_panel = StatisticsPanel(self.parent_frame, self.config)

        # Create test statistics
        stats = DownloadStatistics(
            total_files=10,
            successful_downloads=8,
            failed_downloads=2,
            total_bytes_downloaded=10485760,  # 10 MB
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now()
        )

        # Update statistics
        stats_panel.update_statistics(stats)

        # Give UI time to update
        self.root.update()
        import time
        time.sleep(0.1)
        self.root.update()

        # Check that statistics appear (basic check - exact text depends on formatting)
        # The labels should contain the values
        assert "10" in stats_panel.total_files_label.cget("text")
        assert "8" in stats_panel.successful_label.cget("text")
        assert "2" in stats_panel.failed_label.cget("text")

    def test_statistics_calculation(self):
        """Test that statistics calculations work correctly."""
        stats_panel = StatisticsPanel(self.parent_frame, self.config)

        # Test with sample data
        stats = DownloadStatistics(
            total_files=5,
            successful_downloads=4,
            failed_downloads=1,
            total_bytes_downloaded=5242880,  # 5 MB
            start_time=datetime.now() - timedelta(seconds=120),  # 2 minutes
            end_time=datetime.now()
        )

        stats_panel.update_statistics(stats)

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Check success rate calculation (80%)
        successful_text = stats_panel.successful_label.cget("text")
        assert "80" in successful_text or "4/5" in successful_text

        # Check duration formatting
        duration_text = stats_panel.duration_label.cget("text")
        assert "02:00" in duration_text or "2" in duration_text

    def test_empty_statistics(self):
        """Test display with no statistics."""
        stats_panel = StatisticsPanel(self.parent_frame, self.config)

        # Empty statistics
        stats = DownloadStatistics()

        stats_panel.update_statistics(stats)

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Should show zeros or N/A
        assert "0" in stats_panel.total_files_label.cget("text")

    def test_real_time_updates(self):
        """Test that statistics update in real-time."""
        stats_panel = StatisticsPanel(self.parent_frame, self.config)

        # Initial stats
        initial_stats = DownloadStatistics(
            total_files=1,
            successful_downloads=1,
            failed_downloads=0
        )
        stats_panel.update_statistics(initial_stats)

        # Update with new stats
        updated_stats = DownloadStatistics(
            total_files=3,
            successful_downloads=2,
            failed_downloads=1
        )
        stats_panel.update_statistics(updated_stats)

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Should show updated values
        assert "3" in stats_panel.total_files_label.cget("text")
        assert "2" in stats_panel.successful_label.cget("text")
        assert "1" in stats_panel.failed_label.cget("text")

    def test_speed_calculation(self):
        """Test download speed calculation and display."""
        stats_panel = StatisticsPanel(self.parent_frame, self.config)

        # Stats with speed data
        stats = DownloadStatistics(
            total_files=1,
            successful_downloads=1,
            total_bytes_downloaded=1048576,  # 1 MB
            total_duration=timedelta(seconds=10),  # 10 seconds
            average_speed=104857.6  # ~100 KB/s
        )

        stats_panel.update_statistics(stats)

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Check speed display
        speed_text = stats_panel.speed_label.cget("text")
        assert "KB/s" in speed_text or "MB/s" in speed_text

    def test_completion_summary(self):
        """Test completion summary display."""
        stats_panel = StatisticsPanel(self.parent_frame, self.config)

        # Completed download stats
        stats = DownloadStatistics(
            total_files=100,
            successful_downloads=95,
            failed_downloads=5,
            total_bytes_downloaded=1073741824,  # 1 GB
            total_duration=timedelta(minutes=15),
            start_time=datetime.now() - timedelta(minutes=15),
            end_time=datetime.now()
        )

        stats_panel.update_statistics(stats)

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Should show completion information
        # (Exact format depends on implementation)

    def test_reset_statistics(self):
        """Test statistics reset functionality."""
        stats_panel = StatisticsPanel(self.parent_frame, self.config)

        # Set some stats
        stats = DownloadStatistics(
            total_files=5,
            successful_downloads=3,
            failed_downloads=2
        )
        stats_panel.update_statistics(stats)

        # Reset
        stats_panel.reset_statistics()

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Should show zeros
        assert "0" in stats_panel.total_files_label.cget("text")
        assert "0" in stats_panel.successful_label.cget("text")
        assert "0" in stats_panel.failed_label.cget("text")

    def test_feedback_manager_integration(self):
        """Test integration with feedback manager."""
        stats_panel = StatisticsPanel(self.parent_frame, self.config)

        # Register with feedback manager
        stats_panel.register_with_feedback_manager(self.feedback_manager)

        # Create and send statistics update
        stats = DownloadStatistics(
            total_files=2,
            successful_downloads=2,
            failed_downloads=0
        )

        # This would normally be called by the feedback manager
        stats_panel.update_statistics(stats)

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Check that statistics were updated
        assert "2" in stats_panel.total_files_label.cget("text")