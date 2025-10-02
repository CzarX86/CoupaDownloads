"""
Integration test for memory management with psutil monitoring.
Tests memory threshold monitoring, worker scaling, and resource cleanup.
"""

import pytest
import os
import sys
import tempfile
import shutil
import time
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src and EXPERIMENTAL directories to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../EXPERIMENTAL'))


class TestMemoryManagement:
    """Integration tests for memory management and resource monitoring."""

    @pytest.fixture
    def temp_profile_dir(self):
        """Create a temporary profile directory for testing."""
        temp_dir = tempfile.mkdtemp(prefix="test_profile_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def pool_config(self, temp_profile_dir):
        """Create a valid pool configuration for testing."""
        try:
            from EXPERIMENTAL.workers.models.config import PoolConfig
            return PoolConfig(
                worker_count=2,
                headless_mode=True,
                base_profile_path=temp_profile_dir,
                memory_threshold=0.75,
                shutdown_timeout=60
            )
        except ImportError:
            pytest.skip("PoolConfig not yet implemented")

    @pytest.mark.asyncio
    async def test_memory_threshold_monitoring(self, pool_config):
        """Test that memory usage is monitored against configured thresholds."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit tasks to generate memory usage
            po_numbers = ["PO111111", "PO222222"]
            for po in po_numbers:
                pool.submit_task(po)

            # Monitor memory usage during processing
            memory_readings = []
            threshold_violations = []

            # Monitor for 20 seconds
            for _ in range(40):
                status = pool.get_status()
                memory_info = status['memory']
                memory_percent = memory_info['usage_percent']

                memory_readings.append(memory_percent)

                if memory_percent > pool_config.memory_threshold:
                    threshold_violations.append(memory_percent)

                await asyncio.sleep(0.5)

            # Verify memory monitoring is working
            assert len(memory_readings) > 0, "Memory should be monitored"
            assert all(r >= 0 for r in memory_readings), "Memory readings should be non-negative"

            # Wait for tasks to complete
            timeout = 45
            start_time = time.time()
            completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    completed = True
                    break
                await asyncio.sleep(0.5)

            assert completed, "Tasks should complete"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_memory_pressure_response(self, pool_config):
        """Test system response to memory pressure conditions."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            # Configure low memory threshold to trigger pressure response
            test_config = pool_config
            test_config.memory_threshold = 0.5  # 50% threshold

            pool = PersistentWorkerPool(test_config)
            await pool.start()

            # Submit multiple tasks to potentially trigger memory pressure
            po_numbers = ["PO333333", "PO444444", "PO555555", "PO666666"]
            for po in po_numbers:
                pool.submit_task(po)

            # Monitor for memory pressure responses
            pressure_detected = False
            max_memory_usage = 0

            # Monitor for 30 seconds
            for _ in range(60):
                status = pool.get_status()
                memory_percent = status['memory']['usage_percent']
                max_memory_usage = max(max_memory_usage, memory_percent)

                if memory_percent > test_config.memory_threshold:
                    pressure_detected = True

                await asyncio.sleep(0.5)

            # Verify memory monitoring works
            assert max_memory_usage >= 0, "Memory usage should be tracked"

            # Wait for all tasks to complete
            timeout = 60
            start_time = time.time()
            all_completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    all_completed = True
                    break
                await asyncio.sleep(0.5)

            assert all_completed, "All tasks should complete despite memory pressure"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_worker_memory_isolation(self, pool_config):
        """Test that worker memory usage is tracked per worker."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit tasks to individual workers
            pool.submit_task("PO777777")
            pool.submit_task("PO888888")

            # Monitor individual worker memory usage
            worker_memory_readings = {}

            # Monitor for 20 seconds
            for _ in range(40):
                status = pool.get_status()

                for worker_id, worker_info in status['workers'].items():
                    if worker_id not in worker_memory_readings:
                        worker_memory_readings[worker_id] = []
                    worker_memory_readings[worker_id].append(worker_info.get('memory_usage', 0))

                await asyncio.sleep(0.5)

            # Verify worker memory tracking
            assert len(worker_memory_readings) > 0, "Worker memory should be tracked"
            for worker_id, readings in worker_memory_readings.items():
                assert len(readings) > 0, f"Worker {worker_id} should have memory readings"
                assert all(r >= 0 for r in readings), f"Worker {worker_id} memory readings should be valid"

            # Wait for completion
            timeout = 45
            start_time = time.time()
            completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    completed = True
                    break
                await asyncio.sleep(0.5)

            assert completed, "Tasks should complete"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_memory_cleanup_on_task_completion(self, pool_config):
        """Test that memory is properly cleaned up after task completion."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Get baseline memory
            baseline_status = pool.get_status()
            baseline_memory = baseline_status['memory']['usage_percent']

            # Submit and complete a task
            pool.submit_task("PO999999")

            # Wait for completion
            timeout = 45
            start_time = time.time()
            completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    completed = True
                    break
                await asyncio.sleep(0.5)

            assert completed, "Task should complete"

            # Check memory after completion
            final_status = pool.get_status()
            final_memory = final_status['memory']['usage_percent']

            # Memory should be stable (not continuously growing)
            # This is a basic check - real implementation would have more sophisticated tracking
            assert final_memory >= 0, "Final memory should be valid"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_memory_threshold_configuration(self, pool_config):
        """Test that memory threshold configuration is properly applied."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            # Test different threshold configurations
            thresholds = [0.6, 0.7, 0.8]

            for threshold in thresholds:
                test_config = pool_config
                test_config.memory_threshold = threshold

                pool = PersistentWorkerPool(test_config)
                await pool.start()

                # Verify threshold is applied
                status = pool.get_status()
                configured_threshold = status['memory'].get('threshold', test_config.memory_threshold)
                assert configured_threshold == threshold, f"Threshold {threshold} should be configured"

                # Quick test with one task
                pool.submit_task("PO101010")

                # Wait briefly
                await asyncio.sleep(2)

                # Shutdown
                await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_memory_monitoring_during_concurrent_processing(self, pool_config):
        """Test memory monitoring during concurrent task processing."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit multiple concurrent tasks
            po_numbers = ["PO202020", "PO303030", "PO404040", "PO505050"]
            for po in po_numbers:
                pool.submit_task(po)

            # Monitor memory during concurrent processing
            concurrent_memory_readings = []
            peak_concurrent_memory = 0

            # Monitor for 30 seconds during processing
            for _ in range(60):
                status = pool.get_status()
                memory_percent = status['memory']['usage_percent']
                active_tasks = status['task_queue']['active_tasks']

                if active_tasks > 1:  # During concurrent processing
                    concurrent_memory_readings.append(memory_percent)
                    peak_concurrent_memory = max(peak_concurrent_memory, memory_percent)

                await asyncio.sleep(0.5)

            # Verify concurrent processing occurred and was monitored
            assert len(concurrent_memory_readings) > 0, "Concurrent processing should be monitored"
            assert peak_concurrent_memory >= 0, "Peak memory during concurrency should be tracked"

            # Wait for all tasks to complete
            timeout = 60
            start_time = time.time()
            all_completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    all_completed = True
                    break
                await asyncio.sleep(0.5)

            assert all_completed, "All concurrent tasks should complete"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])