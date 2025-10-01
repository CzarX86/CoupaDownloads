"""
Performance benchmarking for worker pool system.

Tests memory usage validation and performance metrics to ensure
the worker pool meets the <30% memory overhead requirement.
"""

import pytest
import os
import sys
import tempfile
import shutil
import time
import psutil
import threading
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the src and EXPERIMENTAL directories to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../EXPERIMENTAL'))


class TestPoolPerformance:
    """Performance tests for worker pool memory and efficiency metrics."""

    @pytest.fixture
    def temp_profile_dir(self):
        """Create a temporary profile directory for testing."""
        temp_dir = tempfile.mkdtemp(prefix="perf_profile_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def pool_config(self, temp_profile_dir):
        """Create a performance-optimized pool configuration."""
        try:
            from EXPERIMENTAL.workers.models.config import PoolConfig
            return PoolConfig(
                worker_count=2,  # Minimal workers for performance testing
                headless_mode=True,
                base_profile_path=temp_profile_dir,
                memory_threshold=0.75,
                shutdown_timeout=30  # Faster shutdown for testing
            )
        except ImportError:
            pytest.skip("PoolConfig not yet implemented")

    @patch('EXPERIMENTAL.workers.worker_process.webdriver.Edge')
    @patch('EXPERIMENTAL.workers.browser_session.BrowserSession.authenticate', return_value=True)
    @patch('EXPERIMENTAL.workers.worker_process.BrowserSession')
    def test_memory_overhead_under_30_percent(self, mock_browser_session, mock_authenticate, mock_edge_driver, pool_config):
        """Test that worker pool memory overhead is under 30%."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool
            from EXPERIMENTAL.workers.memory_monitor import MemoryMonitor
        except ImportError:
            pytest.skip("Worker pool components not yet implemented")

        # Configure mocks
        mock_driver_instance = MagicMock()
        mock_edge_driver.return_value = mock_driver_instance
        mock_browser_session_instance = MagicMock()
        mock_browser_session.return_value = mock_browser_session_instance
        mock_browser_session_instance.driver = mock_driver_instance
        mock_browser_session_instance.main_window_handle = "window-1"

        # Get baseline memory usage
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / (1024 * 1024)  # MB

        pool = None
        monitor = None

        try:
            # Start memory monitor
            monitor = MemoryMonitor(memory_threshold=0.75)
            monitor.start_monitoring()

            # Create and start worker pool
            pool = PersistentWorkerPool(pool_config)

            # Start pool asynchronously
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(pool.start())

                # Wait for pool to stabilize
                time.sleep(2)

                # Measure memory usage with pool running
                pool_memory = process.memory_info().rss / (1024 * 1024)  # MB
                memory_overhead = pool_memory - baseline_memory
                memory_overhead_percent = (memory_overhead / baseline_memory) * 100

                print(".1f")
                print(".1f")
                print(".1f")

                # Assert memory overhead is under 30%
                assert memory_overhead_percent < 30.0, (
                    f"Memory overhead {memory_overhead_percent:.1f}% exceeds 30% limit "
                    f"(baseline: {baseline_memory:.1f}MB, with pool: {pool_memory:.1f}MB)"
                )

            finally:
                # Cleanup
                if pool:
                    try:
                        loop.run_until_complete(pool.shutdown())
                    except Exception:
                        pass
                loop.close()

        finally:
            if monitor:
                monitor.stop_monitoring()

    @patch('EXPERIMENTAL.workers.worker_process.webdriver.Edge')
    @patch('EXPERIMENTAL.workers.browser_session.BrowserSession.authenticate', return_value=True)
    @patch('EXPERIMENTAL.workers.worker_process.BrowserSession')
    def test_worker_startup_time_under_30_seconds(self, mock_browser_session, mock_authenticate, mock_edge_driver, pool_config):
        """Test that worker pool startup time is under 30 seconds."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool
        except ImportError:
            pytest.skip("PersistentWorkerPool not yet implemented")

        # Configure mocks
        mock_driver_instance = MagicMock()
        mock_edge_driver.return_value = mock_driver_instance
        mock_browser_session_instance = MagicMock()
        mock_browser_session.return_value = mock_browser_session_instance
        mock_browser_session_instance.driver = mock_driver_instance
        mock_browser_session_instance.main_window_handle = "window-1"

        pool = PersistentWorkerPool(pool_config)

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            start_time = time.time()
            loop.run_until_complete(pool.start())
            startup_time = time.time() - start_time

            print(".1f")

            # Assert startup time is under 30 seconds
            assert startup_time < 30.0, f"Startup time {startup_time:.1f}s exceeds 30s limit"

        finally:
            try:
                loop.run_until_complete(pool.shutdown())
            except Exception:
                pass
            loop.close()

    @patch('EXPERIMENTAL.workers.worker_process.webdriver.Edge')
    @patch('EXPERIMENTAL.workers.browser_session.BrowserSession.authenticate', return_value=True)
    @patch('EXPERIMENTAL.workers.worker_process.BrowserSession')
    def test_task_processing_throughput(self, mock_browser_session, mock_authenticate, mock_edge_driver, pool_config):
        """Test task processing throughput and efficiency."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool
            from EXPERIMENTAL.workers.models.po_task import POTask
        except ImportError:
            pytest.skip("Worker pool components not yet implemented")

        # Configure mocks
        mock_driver_instance = MagicMock()
        mock_edge_driver.return_value = mock_driver_instance
        mock_browser_session_instance = MagicMock()
        mock_browser_session.return_value = mock_browser_session_instance
        mock_browser_session_instance.driver = mock_driver_instance
        mock_browser_session_instance.main_window_handle = "window-1"

        # Create mock tasks for throughput testing
        mock_tasks = []
        for i in range(10):  # Small batch for performance testing
            task = POTask(
                po_number=f"PO{i:03d}",
                metadata={'test_task': True, 'sequence': i}
            )
            mock_tasks.append(task)

        pool = None
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            pool = PersistentWorkerPool(pool_config)
            loop.run_until_complete(pool.start())

            # Submit tasks and measure throughput
            start_time = time.time()

            # Mock the task submission since we don't have real browser processing
            submitted_count = 0
            for task in mock_tasks:
                try:
                    # Just test submission overhead, not actual processing
                    handle = pool.submit_task(task)
                    submitted_count += 1
                except Exception as e:
                    print(f"Task submission failed: {e}")
                    break

            submission_time = time.time() - start_time
            throughput = submitted_count / submission_time if submission_time > 0 else 0

            print(f"Submitted {submitted_count} tasks in {submission_time:.2f}s")
            print(f"Submission throughput: {throughput:.2f} tasks/second")

            # Basic throughput assertion (should be reasonable)
            assert throughput > 1.0, f"Submission throughput {throughput:.2f} tasks/s too low"

        finally:
            if pool:
                try:
                    loop.run_until_complete(pool.shutdown())
                except Exception:
                    pass
            loop.close()

    def test_memory_monitor_accuracy(self):
        """Test memory monitor accuracy and responsiveness."""
        try:
            from EXPERIMENTAL.workers.memory_monitor import MemoryMonitor
        except ImportError:
            pytest.skip("MemoryMonitor not yet implemented")

        monitor = MemoryMonitor(memory_threshold=0.75)

        # Test memory info retrieval
        info = monitor.get_memory_info()

        required_keys = [
            'usage_percent', 'total_gb', 'available_gb',
            'process_usage_mb', 'is_pressure'
        ]

        for key in required_keys:
            assert key in info, f"Missing required memory info key: {key}"
            assert info[key] is not None, f"Memory info key {key} is None"

        # Test memory pressure detection
        # This is a basic test - in real scenarios we'd allocate memory to test thresholds
        is_pressure = monitor.is_memory_pressure()
        assert isinstance(is_pressure, bool), "is_memory_pressure should return boolean"

        print(f"Memory usage: {info['usage_percent']:.1f}%")
        print(f"Process usage: {info['process_usage_mb']:.1f}MB")

    @patch('psutil.virtual_memory')
    def test_memory_threshold_handling(self, mock_memory):
        """Test memory threshold detection and callbacks."""
        try:
            from EXPERIMENTAL.workers.memory_monitor import MemoryMonitor
        except ImportError:
            pytest.skip("MemoryMonitor not yet implemented")

        # Mock high memory usage to test threshold
        mock_memory.return_value.percent = 85
        mock_memory.return_value.total = 8 * 1024**3  # 8GB

        monitor = MemoryMonitor(memory_threshold=0.75)  # 75%

        # Test pressure detection
        assert monitor.is_memory_pressure(), "Should detect memory pressure at 85% usage"

        # Test callback registration
        callback_called = []

        def test_callback(memory_info):
            callback_called.append(memory_info)

        monitor.register_callback(test_callback, threshold_ratio=0.80)  # 80%

        # Force memory check
        info = monitor.force_memory_check()

        # Callback should be triggered for 85% > 80% threshold
        assert len(callback_called) > 0, "Memory threshold callback should be triggered"

        print(f"Memory pressure detected: {monitor.is_memory_pressure()}")
        print(f"Callback triggered: {len(callback_called)} times")

    @patch('EXPERIMENTAL.workers.worker_process.webdriver.Edge')
    @patch('EXPERIMENTAL.workers.browser_session.BrowserSession.authenticate', return_value=True)
    @patch('EXPERIMENTAL.workers.worker_process.BrowserSession')
    def test_pool_status_reporting_performance(self, mock_browser_session, mock_authenticate, mock_edge_driver, pool_config):
        """Test that pool status reporting is fast and doesn't impact performance."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool
        except ImportError:
            pytest.skip("PersistentWorkerPool not yet implemented")

        # Configure mocks
        mock_driver_instance = MagicMock()
        mock_edge_driver.return_value = mock_driver_instance
        mock_browser_session_instance = MagicMock()
        mock_browser_session.return_value = mock_browser_session_instance
        mock_browser_session_instance.driver = mock_driver_instance
        mock_browser_session_instance.main_window_handle = "window-1"

        pool = PersistentWorkerPool(pool_config)

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(pool.start())

            # Test status reporting performance
            status_times = []
            status = None

            for _ in range(10):
                start_time = time.time()
                status = pool.get_status()
                end_time = time.time()
                status_times.append(end_time - start_time)

            avg_status_time = sum(status_times) / len(status_times)
            max_status_time = max(status_times)

            print(".4f")
            print(".4f")

            # Status reporting should be fast (< 0.1 seconds)
            assert avg_status_time < 0.1, f"Average status time {avg_status_time:.4f}s too slow"
            assert max_status_time < 0.5, f"Max status time {max_status_time:.4f}s too slow"

            # Verify status contains expected fields
            required_fields = ['pool_status', 'worker_count', 'completed_tasks', 'failed_tasks']
            for field in required_fields:
                assert field in status, f"Missing status field: {field}"

        finally:
            try:
                loop.run_until_complete(pool.shutdown())
            except Exception:
                pass
            loop.close()

    @patch('EXPERIMENTAL.workers.worker_process.webdriver.Edge')
    @patch('EXPERIMENTAL.workers.browser_session.BrowserSession.authenticate', return_value=True)
    @patch('EXPERIMENTAL.workers.worker_process.BrowserSession')
    def test_concurrent_status_access(self, mock_browser_session, mock_authenticate, mock_edge_driver, pool_config):
        """Test that status reporting works correctly under concurrent access."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool
        except ImportError:
            pytest.skip("PersistentWorkerPool not yet implemented")

        # Configure mocks
        mock_driver_instance = MagicMock()
        mock_edge_driver.return_value = mock_driver_instance
        mock_browser_session_instance = MagicMock()
        mock_browser_session.return_value = mock_browser_session_instance
        mock_browser_session_instance.driver = mock_driver_instance
        mock_browser_session_instance.main_window_handle = "window-1"

        pool = PersistentWorkerPool(pool_config)

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(pool.start())

            # Test concurrent status access
            results = []
            errors = []

            def status_worker(worker_id):
                """Worker function to test concurrent status access."""
                try:
                    for _ in range(5):
                        status = pool.get_status()
                        results.append((worker_id, status['pool_status']))
                        time.sleep(0.01)  # Small delay
                except Exception as e:
                    errors.append((worker_id, str(e)))

            # Start multiple threads accessing status concurrently
            threads = []
            for i in range(3):
                thread = threading.Thread(target=status_worker, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Verify no errors occurred
            assert len(errors) == 0, f"Concurrent status access errors: {errors}"

            # Verify all status calls succeeded
            assert len(results) == 15, f"Expected 15 status results, got {len(results)}"

            print(f"Concurrent status access: {len(results)} successful calls, {len(errors)} errors")

        finally:
            try:
                loop.run_until_complete(pool.shutdown())
            except Exception:
                pass
            loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])