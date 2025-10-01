"""
Integration test for graceful shutdown with timeout handling.
Tests shutdown signal handling, task completion before shutdown, and cleanup.
"""

import pytest
import os
import sys
import tempfile
import shutil
import time
import asyncio
import signal
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src and EXPERIMENTAL directories to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../EXPERIMENTAL'))


class TestGracefulShutdown:
    """Integration tests for graceful shutdown handling and cleanup."""

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
                shutdown_timeout=30  # Shorter timeout for testing
            )
        except ImportError:
            pytest.skip("PoolConfig not yet implemented")

    @pytest.mark.asyncio
    async def test_graceful_shutdown_completes_current_tasks(self, pool_config):
        """Test that graceful shutdown completes current tasks before stopping."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit tasks
            po_numbers = ["PO111111", "PO222222"]
            for po in po_numbers:
                pool.submit_task(po)

            # Wait for processing to start
            timeout = 10
            start_time = time.time()
            processing_started = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['active_tasks'] > 0:
                    processing_started = True
                    break
                await asyncio.sleep(0.5)

            assert processing_started, "Tasks should start processing"

            # Initiate graceful shutdown
            await pool.shutdown()

            # Verify shutdown completed
            final_status = pool.get_status()
            assert final_status['pool_status'] == 'stopped', "Pool should be stopped after graceful shutdown"

            # Verify tasks were completed
            assert final_status['completed_tasks'] >= len(po_numbers), "All tasks should be completed before shutdown"

            # Verify no tasks remain active
            assert final_status['task_queue']['active_tasks'] == 0, "No tasks should remain active"
            assert final_status['task_queue']['pending_tasks'] == 0, "No tasks should remain pending"

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_shutdown_timeout_handling(self, pool_config):
        """Test shutdown timeout behavior when tasks don't complete in time."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            # Configure very short shutdown timeout
            test_config = pool_config
            test_config.shutdown_timeout = 5  # 5 seconds

            pool = PersistentWorkerPool(test_config)
            await pool.start()

            # Submit long-running tasks (simulated)
            po_numbers = ["PO333333", "PO444444", "PO555555"]
            for po in po_numbers:
                pool.submit_task(po)

            # Wait for processing to start
            timeout = 10
            start_time = time.time()
            processing_started = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['active_tasks'] > 0:
                    processing_started = True
                    break
                await asyncio.sleep(0.5)

            assert processing_started, "Tasks should start processing"

            # Initiate shutdown with short timeout
            shutdown_start = time.time()
            await pool.shutdown()
            shutdown_duration = time.time() - shutdown_start

            # Verify shutdown occurred (may have timed out gracefully)
            final_status = pool.get_status()
            assert final_status['pool_status'] == 'stopped', "Pool should be stopped"

            # Shutdown should respect timeout (approximately)
            assert shutdown_duration <= test_config.shutdown_timeout + 5, "Shutdown should respect timeout"

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_signal_based_shutdown(self, pool_config):
        """Test shutdown triggered by system signals."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit tasks
            pool.submit_task("PO666666")
            pool.submit_task("PO777777")

            # Wait for processing to start
            timeout = 10
            start_time = time.time()
            processing_started = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['active_tasks'] > 0:
                    processing_started = True
                    break
                await asyncio.sleep(0.5)

            assert processing_started, "Tasks should start processing"

            # Simulate signal-based shutdown
            # In real implementation, this would be handled by signal handlers
            await pool.shutdown()

            # Verify graceful shutdown occurred
            final_status = pool.get_status()
            assert final_status['pool_status'] == 'stopped', "Pool should be stopped via signal"

            # Tasks should be completed or properly handled
            total_accounted = final_status['completed_tasks'] + final_status['failed_tasks']
            assert total_accounted >= 2, "All tasks should be accounted for during signal shutdown"

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_shutdown_worker_cleanup(self, pool_config):
        """Test that workers are properly cleaned up during shutdown."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Verify workers are initially active
            initial_status = pool.get_status()
            assert len(initial_status['workers']) == pool_config.worker_count, "Workers should be started"

            for worker_id, worker_info in initial_status['workers'].items():
                assert worker_info['status'] in ['ready', 'idle'], f"Worker {worker_id} should be initially ready"

            # Submit and complete some tasks
            pool.submit_task("PO888888")

            # Wait for completion
            timeout = 30
            start_time = time.time()
            completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    completed = True
                    break
                await asyncio.sleep(0.5)

            assert completed, "Task should complete"

            # Shutdown and verify worker cleanup
            await pool.shutdown()

            final_status = pool.get_status()
            assert final_status['pool_status'] == 'stopped', "Pool should be stopped"

            # Verify all workers are terminated
            for worker_id, worker_info in final_status['workers'].items():
                assert worker_info['status'] in ['terminated', 'stopped'], f"Worker {worker_id} should be terminated"

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_shutdown_resource_cleanup(self, pool_config):
        """Test that resources are properly cleaned up during shutdown."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit tasks to create resources
            po_numbers = ["PO999001", "PO999002"]
            for po in po_numbers:
                pool.submit_task(po)

            # Wait for processing
            timeout = 30
            start_time = time.time()
            completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    completed = True
                    break
                await asyncio.sleep(0.5)

            assert completed, "Tasks should complete"

            # Shutdown and verify resource cleanup
            await pool.shutdown()

            # Verify pool is fully cleaned up
            final_status = pool.get_status()
            assert final_status['pool_status'] == 'stopped', "Pool should be stopped"

            # Verify task queue is empty
            assert final_status['task_queue']['pending_tasks'] == 0, "Task queue should be empty"
            assert final_status['task_queue']['active_tasks'] == 0, "No active tasks should remain"

            # Verify workers are cleaned up
            assert len(final_status['workers']) == pool_config.worker_count, "All workers should be accounted for"
            for worker_info in final_status['workers'].values():
                assert worker_info['status'] in ['terminated', 'stopped'], "Workers should be terminated"

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_shutdown_during_active_processing(self, pool_config):
        """Test shutdown initiated while tasks are actively processing."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit tasks
            po_numbers = ["PO101001", "PO101002", "PO101003"]
            for po in po_numbers:
                pool.submit_task(po)

            # Wait for active processing
            timeout = 10
            start_time = time.time()
            actively_processing = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['active_tasks'] > 0:
                    actively_processing = True
                    break
                await asyncio.sleep(0.5)

            assert actively_processing, "Tasks should be actively processing"

            # Initiate shutdown during active processing
            await pool.shutdown()

            # Verify shutdown handled active processing gracefully
            final_status = pool.get_status()
            assert final_status['pool_status'] == 'stopped', "Pool should shutdown gracefully during processing"

            # All tasks should be accounted for
            total_accounted = final_status['completed_tasks'] + final_status['failed_tasks']
            assert total_accounted >= len(po_numbers), "All tasks should be accounted for"

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_multiple_shutdown_calls(self, pool_config):
        """Test that multiple shutdown calls are handled gracefully."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit a task
            pool.submit_task("PO202020")

            # Call shutdown multiple times
            shutdown_tasks = []
            for i in range(3):
                shutdown_tasks.append(asyncio.create_task(pool.shutdown()))

            # Wait for all shutdown calls to complete
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

            # Verify final state
            final_status = pool.get_status()
            assert final_status['pool_status'] == 'stopped', "Pool should be stopped after multiple shutdown calls"

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])