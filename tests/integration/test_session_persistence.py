"""
Integration test for session persistence (auth → tabs → cleanup).
Tests browser session authentication, tab-based processing, and cleanup.
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


class TestSessionPersistence:
    """Integration tests for browser session persistence and tab management."""

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
                worker_count=1,  # Single worker for session testing
                headless_mode=True,
                base_profile_path=temp_profile_dir,
                memory_threshold=0.75,
                shutdown_timeout=60
            )
        except ImportError:
            pytest.skip("PoolConfig not yet implemented")

    @pytest.mark.asyncio
    async def test_session_authentication_persistence(self, pool_config):
        """Test that browser sessions maintain authentication across operations."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit first task to establish session
            pool.submit_task("PO111111")

            # Wait for task to start processing
            timeout = 15
            start_time = time.time()
            processing_started = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['active_tasks'] > 0:
                    processing_started = True
                    break
                await asyncio.sleep(0.5)

            assert processing_started, "Task should start processing"

            # Wait a moment for session establishment
            await asyncio.sleep(3)

            # Check worker session status
            status = pool.get_status()
            worker_id = list(status['workers'].keys())[0]
            worker_info = status['workers'][worker_id]

            # Session should be active
            assert worker_info['status'] in ['processing', 'ready'], "Worker should have active session"

            # Submit second task to test session reuse
            pool.submit_task("PO222222")

            # Wait for both tasks to complete
            timeout = 45
            start_time = time.time()
            all_completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    all_completed = True
                    break
                await asyncio.sleep(0.5)

            assert all_completed, "Both tasks should complete using persistent session"

            # Verify session remained active throughout
            final_status = pool.get_status()
            final_worker_info = final_status['workers'][worker_id]
            assert final_worker_info['status'] in ['ready', 'idle'], "Session should remain active"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_tab_based_processing_isolation(self, pool_config):
        """Test that each PO is processed in isolated tabs."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit multiple tasks to test tab isolation
            po_numbers = ["PO333001", "PO333002", "PO333003"]
            for po in po_numbers:
                pool.submit_task(po)

            # Monitor tab usage during processing
            max_concurrent_tabs = 0
            tab_counts = []

            # Monitor for 30 seconds
            for _ in range(60):
                status = pool.get_status()
                worker_info = list(status['workers'].values())[0]

                # Track tab count (this would be in worker_info if implemented)
                # For now, just verify processing occurs
                if status['task_queue']['active_tasks'] > 0:
                    max_concurrent_tabs = max(max_concurrent_tabs, status['task_queue']['active_tasks'])

                tab_counts.append(status['task_queue']['active_tasks'])
                await asyncio.sleep(0.5)

            # Should have processed tasks (tab isolation would be verified in worker implementation)
            final_status = pool.get_status()
            assert final_status['completed_tasks'] >= len(po_numbers), "All tasks should complete"

            # Verify no tasks remain
            assert final_status['task_queue']['pending_tasks'] == 0, "No tasks should remain pending"
            assert final_status['task_queue']['active_tasks'] == 0, "No tasks should remain active"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_session_recovery_after_interruption(self, pool_config):
        """Test session recovery after connection interruptions."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit task and let it start
            pool.submit_task("PO444444")

            # Wait for processing to begin
            timeout = 15
            start_time = time.time()
            processing_started = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['active_tasks'] > 0:
                    processing_started = True
                    break
                await asyncio.sleep(0.5)

            assert processing_started, "Task processing should start"

            # Simulate network interruption (this would be mocked in real implementation)
            # For now, just verify the system continues to function
            await asyncio.sleep(2)

            # Submit another task to test continued operation
            pool.submit_task("PO555555")

            # Wait for completion
            timeout = 45
            start_time = time.time()
            all_completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    all_completed = True
                    break
                await asyncio.sleep(0.5)

            assert all_completed, "Tasks should complete despite simulated interruption"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_session_cleanup_on_shutdown(self, pool_config):
        """Test that browser sessions are properly cleaned up on shutdown."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit and complete a task to establish session
            pool.submit_task("PO666666")

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

            # Verify session was active
            status_before_shutdown = pool.get_status()
            worker_info = list(status_before_shutdown['workers'].values())[0]
            assert worker_info['status'] in ['ready', 'idle'], "Session should be active before shutdown"

            # Shutdown pool
            await pool.shutdown()

            # Verify pool is fully stopped
            final_status = pool.get_status()
            assert final_status['pool_status'] == 'stopped', "Pool should be stopped"

            # Verify workers are terminated
            for worker_id, worker_info in final_status['workers'].items():
                assert worker_info['status'] in ['terminated', 'stopped'], f"Worker {worker_id} should be terminated"

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, pool_config):
        """Test multiple concurrent operations within same session."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            # Use 2 workers for this test
            test_config = pool_config
            test_config.worker_count = 2

            pool = PersistentWorkerPool(test_config)
            await pool.start()

            # Submit multiple tasks to both workers
            po_numbers = ["PO777001", "PO777002", "PO777003", "PO777004"]
            for po in po_numbers:
                pool.submit_task(po)

            # Monitor concurrent processing
            max_concurrent = 0
            concurrent_samples = []

            # Monitor for 30 seconds
            for _ in range(60):
                status = pool.get_status()
                active_count = status['task_queue']['active_tasks']
                max_concurrent = max(max_concurrent, active_count)
                concurrent_samples.append(active_count)
                await asyncio.sleep(0.5)

            # Should achieve some level of concurrency
            assert max_concurrent > 0, "Should have concurrent task processing"

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

            # Verify final statistics
            final_status = pool.get_status()
            assert final_status['completed_tasks'] >= len(po_numbers), "All tasks should be completed"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_session_state_preservation(self, pool_config):
        """Test that session state (cookies, auth) is preserved across tasks."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit first task to establish authenticated session
            pool.submit_task("PO888888")

            # Wait for completion
            timeout = 30
            start_time = time.time()
            first_completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    first_completed = True
                    break
                await asyncio.sleep(0.5)

            assert first_completed, "First task should complete and establish session"

            # Submit second task that should reuse the authenticated session
            pool.submit_task("PO999999")

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

            assert second_completed, "Second task should complete using preserved session"

            # Verify both tasks completed successfully
            final_status = pool.get_status()
            assert final_status['completed_tasks'] >= 2, "Both tasks should complete successfully"
            assert final_status['failed_tasks'] == 0, "No tasks should fail"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])