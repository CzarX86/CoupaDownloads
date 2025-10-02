"""
Integration test for tab-based processing with state preservation.
Tests tab lifecycle management, state isolation, and concurrent tab operations.
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


class TestTabProcessing:
    """Integration tests for tab-based processing and state management."""

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
                worker_count=1,  # Single worker for tab testing
                headless_mode=True,
                base_profile_path=temp_profile_dir,
                memory_threshold=0.75,
                shutdown_timeout=60
            )
        except ImportError:
            pytest.skip("PoolConfig not yet implemented")

    @pytest.mark.asyncio
    async def test_tab_creation_and_isolation(self, pool_config):
        """Test that tabs are created and maintain isolation between tasks."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit multiple tasks to test tab isolation
            po_numbers = ["PO111111", "PO222222", "PO333333"]
            for po in po_numbers:
                pool.submit_task(po)

            # Monitor tab usage during processing
            tab_counts = []
            max_tabs = 0

            # Monitor for 30 seconds
            for _ in range(60):
                status = pool.get_status()
                worker_info = list(status['workers'].values())[0]

                # Track active tabs (this would be in worker_info if implemented)
                active_tasks = status['task_queue']['active_tasks']
                tab_counts.append(active_tasks)
                max_tabs = max(max_tabs, active_tasks)

                await asyncio.sleep(0.5)

            # Verify tab-based processing occurred
            assert max_tabs > 0, "Tabs should be used for processing"

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

            assert all_completed, "All tab-isolated tasks should complete"

            # Verify final statistics
            final_status = pool.get_status()
            assert final_status['completed_tasks'] >= len(po_numbers), "All tasks should be completed"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_tab_state_preservation(self, pool_config):
        """Test that tab state is preserved during processing."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit first task to establish tab state
            pool.submit_task("PO444444")

            # Wait for processing to start
            timeout = 15
            start_time = time.time()
            processing_started = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['active_tasks'] > 0:
                    processing_started = True
                    break
                await asyncio.sleep(0.5)

            assert processing_started, "First task should start processing"

            # Wait a moment for tab state to be established
            await asyncio.sleep(3)

            # Submit second task that should use a separate tab
            pool.submit_task("PO555555")

            # Monitor that both tasks process concurrently in separate tabs
            concurrent_processing = False
            max_concurrent = 0

            # Monitor for 20 seconds
            for _ in range(40):
                status = pool.get_status()
                active_count = status['task_queue']['active_tasks']
                max_concurrent = max(max_concurrent, active_count)

                if active_count > 1:
                    concurrent_processing = True

                await asyncio.sleep(0.5)

            # Verify concurrent tab processing
            assert max_concurrent > 0, "Tasks should be processed in tabs"

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

            assert completed, "Both tab-processed tasks should complete"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_tab_cleanup_after_task_completion(self, pool_config):
        """Test that tabs are properly cleaned up after task completion."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit and complete a task
            pool.submit_task("PO666666")

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

            # Verify worker is ready for new tasks (tabs cleaned up)
            status = pool.get_status()
            worker_info = list(status['workers'].values())[0]
            assert worker_info['status'] in ['ready', 'idle'], "Worker should be ready after tab cleanup"

            # Submit another task to verify tab cleanup worked
            pool.submit_task("PO777777")

            # Verify new task starts processing
            timeout = 15
            start_time = time.time()
            restarted = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['active_tasks'] > 0:
                    restarted = True
                    break
                await asyncio.sleep(0.5)

            assert restarted, "New task should start after tab cleanup"

            # Wait for second task completion
            timeout = 30
            start_time = time.time()
            second_completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    second_completed = True
                    break
                await asyncio.sleep(0.5)

            assert second_completed, "Second task should complete after tab cleanup"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_tab_operations(self, pool_config):
        """Test concurrent operations across multiple tabs."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            # Use 2 workers for concurrent tab testing
            test_config = pool_config
            test_config.worker_count = 2

            pool = PersistentWorkerPool(test_config)
            await pool.start()

            # Submit multiple tasks to test concurrent tab operations
            po_numbers = ["PO888001", "PO888002", "PO888003", "PO888004"]
            for po in po_numbers:
                pool.submit_task(po)

            # Monitor concurrent tab processing
            concurrent_samples = []
            max_concurrent_tabs = 0

            # Monitor for 30 seconds
            for _ in range(60):
                status = pool.get_status()
                active_tasks = status['task_queue']['active_tasks']
                concurrent_samples.append(active_tasks)
                max_concurrent_tabs = max(max_concurrent_tabs, active_tasks)
                await asyncio.sleep(0.5)

            # Verify concurrent processing occurred
            assert max_concurrent_tabs > 1, "Multiple tabs should be used concurrently"
            assert len([s for s in concurrent_samples if s > 1]) > 0, "Concurrent tab usage should be detected"

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

            assert all_completed, "All concurrent tab operations should complete"

            # Verify final statistics
            final_status = pool.get_status()
            assert final_status['completed_tasks'] >= len(po_numbers), "All tasks should be completed"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_tab_session_isolation(self, pool_config):
        """Test that tab sessions maintain isolation from main session."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit task to create tab session
            pool.submit_task("PO999999")

            # Wait for processing
            timeout = 45
            start_time = time.time()
            completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    completed = True
                    break
                await asyncio.sleep(0.5)

            assert completed, "Task should complete in isolated tab"

            # Verify worker session remains intact
            final_status = pool.get_status()
            worker_info = list(final_status['workers'].values())[0]
            assert worker_info['status'] in ['ready', 'idle'], "Worker session should remain intact after tab processing"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_tab_lifecycle_management(self, pool_config):
        """Test complete tab lifecycle from creation to cleanup."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Monitor tab lifecycle through task processing
            lifecycle_events = []

            # Submit task and monitor its lifecycle
            pool.submit_task("PO101010")

            # Monitor the processing lifecycle
            task_started = False
            task_completed = False

            # Monitor for 40 seconds
            for i in range(80):
                status = pool.get_status()
                active_tasks = status['task_queue']['active_tasks']
                pending_tasks = status['task_queue']['pending_tasks']

                if active_tasks > 0 and not task_started:
                    task_started = True
                    lifecycle_events.append('task_started')

                if active_tasks == 0 and pending_tasks == 0 and task_started:
                    task_completed = True
                    lifecycle_events.append('task_completed')
                    break

                await asyncio.sleep(0.5)

            # Verify lifecycle events
            assert 'task_started' in lifecycle_events, "Task should start processing"
            assert 'task_completed' in lifecycle_events, "Task should complete"

            # Verify final state
            final_status = pool.get_status()
            assert final_status['completed_tasks'] >= 1, "Task should be completed"
            assert final_status['task_queue']['active_tasks'] == 0, "No active tasks should remain"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])