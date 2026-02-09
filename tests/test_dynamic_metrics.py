
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from src.integration.progress_tracker import ProgressTracker

class TestDynamicMetrics:
    def test_dynamic_throughput_short_runtime(self):
        """Test calculating throughput for runtime < 5 minutes (should use 10s window)."""
        tracker = ProgressTracker()
        tracker.start_time = datetime.now()
        
        # Simulate now
        now = datetime.now()
        
        # Add some completions in the last 10 seconds
        # We need to mock completed_in_last_window
        # 3 completions: 2s ago, 5s ago, 8s ago
        tracker.completed_in_last_window = [
            now - timedelta(seconds=8),
            now - timedelta(seconds=5),
            now - timedelta(seconds=2)
        ]
        
        # This one is older than 10s (e.g. 15s ago), should be ignored by dynamic calc
        tracker.completed_in_last_window.insert(0, now - timedelta(seconds=15))
        
        # Manually calculating expected rate:
        # Window is 10s. 3 completions in window.
        # Rate = 3 / 10 = 0.3 tasks/sec
        
        with patch('src.integration.progress_tracker.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            # calculate dynamic throughput
            rate = tracker._calculate_dynamic_throughput()
            
            # 3 completions in 10 seconds = 0.3/sec
            assert rate == pytest.approx(0.3)

    def test_dynamic_throughput_long_runtime(self):
        """Test calculating throughput for runtime > 5 minutes (should use 5min window)."""
        tracker = ProgressTracker()
        # Start time was 10 minutes ago
        tracker.start_time = datetime.now() - timedelta(minutes=10)
        
        now = datetime.now()
        
        # Add completions spread over last 5 minutes
        # We'll add 30 completions uniform-ish
        tracker.completed_in_last_window = []
        for i in range(30):
            # 1 completion every 10 seconds for the last 5 mins (300 get us back to 300s)
            tracker.completed_in_last_window.append(now - timedelta(seconds=i*10))
            
        # Add one older than 5 mins (e.g. 6 mins ago)
        tracker.completed_in_last_window.append(now - timedelta(minutes=6))
        
        # Sort them just to be safe (though logic doesn't strictly require sorted)
        tracker.completed_in_last_window.sort()
        
        # Expected:
        # Window start = now - 5mins
        # Completions in window = 30 (0 to 290s ago)
        # Duration = 300s
        # Rate = 30 / 300 = 0.1 tasks/sec
        
        with patch('src.integration.progress_tracker.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            
            rate = tracker._calculate_dynamic_throughput()
            
            assert rate == pytest.approx(0.1)

    def test_get_performance_metrics_includes_dynamic_rate(self):
        """Ensure get_performance_metrics includes the dynamic rate key."""
        tracker = ProgressTracker()
        metrics = tracker.get_performance_metrics()
        
        assert 'throughput' in metrics
        assert 'dynamic_rate_per_minute' in metrics['throughput']
