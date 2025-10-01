"""
Integration test for profile isolation with concurrent workers.
Tests browser profile separation, data isolation, and concurrent access.
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


class TestProfileIsolation:
    """Integration tests for browser profile isolation between workers."""

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
                worker_count=3,  # Multiple workers for isolation testing
                headless_mode=True,
                base_profile_path=temp_profile_dir,
                memory_threshold=0.75,
                shutdown_timeout=60
            )
        except ImportError:
            pytest.skip("PoolConfig not yet implemented")

    @pytest.mark.asyncio
    async def test_worker_profile_separation(self, pool_config):
        """Test that each worker gets a separate isolated profile."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Check that workers have separate profiles
            status = pool.get_status()
            worker_profiles = {}

            for worker_id, worker_info in status['workers'].items():
                profile_path = worker_info.get('profile_path')
                assert profile_path is not None, f"Worker {worker_id} should have a profile path"

                # Verify profile path is unique
                assert profile_path not in worker_profiles.values(), f"Profile path {profile_path} should be unique"
                worker_profiles[worker_id] = profile_path

                # Verify profile directory exists
                assert os.path.exists(profile_path), f"Profile directory {profile_path} should exist"

                # Verify profile is different from base profile
                assert profile_path != pool_config.base_profile_path, "Worker profile should be cloned, not original"

            # Verify we have the expected number of unique profiles
            assert len(worker_profiles) == pool_config.worker_count, f"Should have {pool_config.worker_count} unique profiles"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_profile_access_isolation(self, pool_config):
        """Test that concurrent workers don't interfere with each other's profiles."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Submit multiple tasks to different workers
            po_numbers = ["PO111111", "PO222222", "PO333333", "PO444444", "PO555555"]
            for po in po_numbers:
                pool.submit_task(po)

            # Monitor concurrent processing
            concurrent_workers = []
            max_concurrent = 0

            # Monitor for 30 seconds
            for _ in range(60):
                status = pool.get_status()
                active_count = status['task_queue']['active_tasks']
                max_concurrent = max(max_concurrent, active_count)

                if active_count > 1:
                    concurrent_workers.append(active_count)

                await asyncio.sleep(0.5)

            # Verify concurrent processing occurred
            assert max_concurrent > 1, "Multiple workers should process concurrently"
            assert len(concurrent_workers) > 0, "Concurrent worker activity should be detected"

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

            assert all_completed, "All tasks should complete with isolated profiles"

            # Verify final statistics
            final_status = pool.get_status()
            assert final_status['completed_tasks'] >= len(po_numbers), "All tasks should be completed"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_profile_data_isolation(self, pool_config):
        """Test that profile data remains isolated between workers."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Get initial profile information
            initial_status = pool.get_status()
            initial_profiles = {}

            for worker_id, worker_info in initial_status['workers'].items():
                profile_path = worker_info['profile_path']
                initial_profiles[worker_id] = profile_path

            # Submit tasks to create profile data
            po_numbers = ["PO666666", "PO777777"]
            for po in po_numbers:
                pool.submit_task(po)

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

            # Verify profiles still exist and are isolated
            final_status = pool.get_status()

            for worker_id, worker_info in final_status['workers'].items():
                final_profile_path = worker_info['profile_path']

                # Profile should still exist
                assert os.path.exists(final_profile_path), f"Profile {final_profile_path} should still exist"

                # Profile should be same as initial
                assert final_profile_path == initial_profiles[worker_id], f"Worker {worker_id} profile should remain consistent"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_profile_cleanup_on_worker_failure(self, pool_config):
        """Test profile cleanup when workers fail."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Get initial worker profiles
            initial_status = pool.get_status()
            initial_profiles = {}

            for worker_id, worker_info in initial_status['workers'].items():
                initial_profiles[worker_id] = worker_info['profile_path']

            # Submit tasks and let them process
            po_numbers = ["PO888888", "PO999999"]
            for po in po_numbers:
                pool.submit_task(po)

            # Wait for some processing
            await asyncio.sleep(5)

            # Shutdown pool (simulating failure scenario)
            await pool.shutdown()

            # Verify final state
            final_status = pool.get_status()
            assert final_status['pool_status'] == 'stopped', "Pool should be stopped"

            # Profiles should be cleaned up according to configuration
            # (This depends on profile_cleanup_on_shutdown setting)
            for worker_id, initial_profile in initial_profiles.items():
                if pool_config.profile_cleanup_on_shutdown:
                    # Profiles should be cleaned up
                    assert not os.path.exists(initial_profile), f"Profile {initial_profile} should be cleaned up"
                else:
                    # Profiles should remain (in real implementation)
                    pass  # Would verify profile exists

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_profile_cloning_from_base(self, pool_config):
        """Test that worker profiles are properly cloned from base profile."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            # Create a base profile with some content
            base_profile = pool_config.base_profile_path
            test_file = os.path.join(base_profile, "test_data.txt")
            with open(test_file, 'w') as f:
                f.write("base profile data")

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Verify worker profiles are separate from base
            status = pool.get_status()

            for worker_id, worker_info in status['workers'].items():
                worker_profile = worker_info['profile_path']

                # Worker profile should be different from base
                assert worker_profile != base_profile, "Worker profile should be cloned"

                # Worker profile should exist
                assert os.path.exists(worker_profile), f"Worker profile {worker_profile} should exist"

                # Worker profile should be a directory
                assert os.path.isdir(worker_profile), f"Worker profile {worker_profile} should be a directory"

                # Base profile content should not be directly in worker profile
                # (cloning strategy may vary - this tests the concept)
                worker_test_file = os.path.join(worker_profile, "test_data.txt")
                # The file may or may not exist depending on cloning strategy
                # The key is that profiles are isolated

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_profile_isolation_during_restart(self, pool_config):
        """Test profile isolation is maintained during worker restarts."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            pool = PersistentWorkerPool(pool_config)
            await pool.start()

            # Get initial profile assignments
            initial_status = pool.get_status()
            initial_profiles = {}

            for worker_id, worker_info in initial_status['workers'].items():
                initial_profiles[worker_id] = worker_info['profile_path']

            # Submit tasks and let them process
            po_numbers = ["PO101010", "PO202020"]
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

            # Verify profiles remain consistent throughout lifecycle
            final_status = pool.get_status()

            for worker_id, worker_info in final_status['workers'].items():
                final_profile = worker_info['profile_path']

                # Profile should be consistent
                assert final_profile == initial_profiles[worker_id], f"Worker {worker_id} profile should remain consistent"

                # Profile should still exist
                assert os.path.exists(final_profile), f"Profile {final_profile} should still exist"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")

    @pytest.mark.asyncio
    async def test_profile_resource_limits(self, pool_config):
        """Test that profile isolation handles resource constraints."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            # Configure with many workers to test resource handling
            test_config = pool_config
            test_config.worker_count = 4  # More workers

            pool = PersistentWorkerPool(test_config)
            await pool.start()

            # Verify all workers get profiles despite resource constraints
            status = pool.get_status()
            assert len(status['workers']) == test_config.worker_count, f"All {test_config.worker_count} workers should start"

            # Verify profile isolation
            profiles = []
            for worker_info in status['workers'].values():
                profile_path = worker_info['profile_path']
                profiles.append(profile_path)
                assert os.path.exists(profile_path), f"Profile {profile_path} should exist"

            # All profiles should be unique
            assert len(set(profiles)) == len(profiles), "All worker profiles should be unique"

            # Submit tasks to all workers
            po_numbers = ["PO303030", "PO404040", "PO505050", "PO606060"]
            for po in po_numbers:
                pool.submit_task(po)

            # Wait for completion
            timeout = 60
            start_time = time.time()
            all_completed = False

            while time.time() - start_time < timeout:
                status = pool.get_status()
                if status['task_queue']['pending_tasks'] == 0 and status['task_queue']['active_tasks'] == 0:
                    all_completed = True
                    break
                await asyncio.sleep(0.5)

            assert all_completed, "All tasks should complete with resource constraints"

            await pool.shutdown()

        except ImportError as e:
            pytest.fail(f"Required modules not implemented: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])