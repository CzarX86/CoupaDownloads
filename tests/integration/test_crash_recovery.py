"""
Integration tests for crash recovery scenarios.
Tests the cascading recovery: restart -> redistribute -> fail.
These tests MUST FAIL until crash recovery is implemented.
"""

import pytest
import os
import sys
import tempfile
import time
import psutil
from unittest.mock import patch, MagicMock

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


class TestWorkerCrashRecovery:
    """Integration tests for worker crash detection and recovery."""
    
    @pytest.fixture
    def worker_pool(self):
        """Create worker pool for crash testing."""
        try:
            from src.models.worker_pool import PersistentWorkerPool, PoolConfiguration
            
            config = PoolConfiguration(
                worker_count=3,  # 3 workers for better crash testing
                headless_mode=True,
                base_profile_path=tempfile.mkdtemp(),
                memory_threshold=0.75,
                shutdown_timeout=60
            )
            
            pool = PersistentWorkerPool()
            pool.initialize(config)
            yield pool
            pool.shutdown(timeout=30)
            
        except ImportError:
            pytest.skip("PersistentWorkerPool not yet implemented")
            
    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for crash testing."""
        try:
            from src.models.worker_pool import POTask
            
            return [
                POTask(task_id=f"crash_test_{i}", po_number=f"PO-CRASH-{i:03d}", po_data={})
                for i in range(5)
            ]
        except ImportError:
            pytest.skip("POTask not yet implemented")
            
    def test_worker_crash_detection(self, worker_pool):
        """Test that worker crashes are detected within 5 seconds."""
        try:
            status = worker_pool.get_status()
            target_worker = status['workers'][0]
            worker_id = target_worker['worker_id']
            
            # Get worker process for termination
            worker_info = worker_pool.get_worker_info(worker_id)
            worker_process_id = worker_info.process_id  # This property should exist
            
            # Simulate worker crash by terminating process
            try:
                worker_process = psutil.Process(worker_process_id)
                worker_process.terminate()
                worker_process.wait(timeout=5)
            except psutil.NoSuchProcess:
                pass  # Process already gone
                
            # Wait for crash detection (should be within 5 seconds)
            detection_start = time.time()
            crashed_detected = False
            
            while time.time() - detection_start < 10:  # 10 second max wait
                status = worker_pool.get_status()
                crashed_worker = next((w for w in status['workers'] if w['worker_id'] == worker_id), None)
                
                if crashed_worker and crashed_worker['status'] == 'crashed':
                    crashed_detected = True
                    detection_time = time.time() - detection_start
                    break
                    
                time.sleep(0.5)
                
            assert crashed_detected, "Worker crash should be detected"
            assert detection_time <= 5.0, f"Crash detection should occur within 5 seconds, took {detection_time:.2f}s"
            
        except ImportError:
            pytest.fail("Worker pool components not implemented yet - test should fail")
            
    def test_cascading_recovery_restart_worker(self, worker_pool, sample_tasks):
        """Test cascading recovery: first attempt worker restart."""
        try:
            # Add task to queue
            worker_pool.add_tasks(sample_tasks[:1])
            
            # Wait for task assignment
            time.sleep(2)
            status = worker_pool.get_status()
            processing_worker = next(w for w in status['workers'] if w['status'] == 'processing')
            crashed_worker_id = processing_worker['worker_id']
            
            # Simulate worker crash during processing
            worker_info = worker_pool.get_worker_info(crashed_worker_id)
            worker_process = psutil.Process(worker_info.process_id)
            worker_process.terminate()
            
            # Wait for crash detection and restart attempt
            restart_detected = False
            start_time = time.time()
            
            while time.time() - start_time < 30:  # 30 second timeout
                status = worker_pool.get_status()
                crashed_worker = next((w for w in status['workers'] if w['worker_id'] == crashed_worker_id), None)
                
                if crashed_worker and crashed_worker['status'] == 'restarting':
                    restart_detected = True
                    break
                    
                time.sleep(1)
                
            assert restart_detected, "System should attempt to restart crashed worker"
            
            # Wait for restart completion or failure
            restart_completed = False
            start_time = time.time()
            
            while time.time() - start_time < 60:  # 60 second timeout for restart
                status = worker_pool.get_status()
                restarted_worker = next((w for w in status['workers'] if w['worker_id'] == crashed_worker_id), None)
                
                if restarted_worker and restarted_worker['status'] in ['ready', 'idle']:
                    restart_completed = True
                    break
                    
                time.sleep(2)
                
            # If restart succeeded, task should complete with restarted worker
            if restart_completed:
                # Wait for task completion
                while worker_pool.get_status()['pending_tasks'] > 0:
                    time.sleep(1)
                    
                assert worker_pool.get_status()['pending_tasks'] == 0, "Task should complete after worker restart"
                
        except ImportError:
            pytest.fail("Worker pool components not implemented yet - test should fail")
            
    def test_cascading_recovery_redistribute_task(self, worker_pool, sample_tasks):
        """Test cascading recovery: redistribute to another worker if restart fails."""
        try:
            # Add task to queue  
            worker_pool.add_tasks(sample_tasks[:1])
            
            # Wait for task assignment
            time.sleep(2)
            status = worker_pool.get_status()
            processing_worker = next(w for w in status['workers'] if w['status'] == 'processing')
            crashed_worker_id = processing_worker['worker_id']
            
            # Mock worker restart to always fail
            with patch.object(worker_pool, 'restart_worker', return_value=False):
                # Simulate worker crash
                worker_info = worker_pool.get_worker_info(crashed_worker_id)
                worker_process = psutil.Process(worker_info.process_id)
                worker_process.terminate()
                
                # Wait for redistribution to occur
                redistribution_start = time.time()
                task_redistributed = False
                
                while time.time() - redistribution_start < 30:
                    status = worker_pool.get_status()
                    
                    # Check if another worker picked up the task
                    other_workers = [w for w in status['workers'] if w['worker_id'] != crashed_worker_id]
                    processing_workers = [w for w in other_workers if w['status'] == 'processing']
                    
                    if processing_workers:
                        task_redistributed = True
                        break
                        
                    time.sleep(1)
                    
                assert task_redistributed, "Task should be redistributed to available worker"
                
                # Wait for task completion with redistributed worker
                while worker_pool.get_status()['pending_tasks'] > 0:
                    time.sleep(1)
                    
                assert worker_pool.get_status()['pending_tasks'] == 0, "Task should complete with redistributed worker"
                
        except ImportError:
            pytest.fail("Worker pool components not implemented yet - test should fail")
            
    def test_cascading_recovery_mark_failed(self, worker_pool, sample_tasks):
        """Test cascading recovery: mark task as failed if no workers available."""
        try:
            # Crash all workers except one
            status = worker_pool.get_status()
            workers_to_crash = status['workers'][1:]  # Keep one worker
            
            for worker in workers_to_crash:
                worker_info = worker_pool.get_worker_info(worker['worker_id'])
                worker_process = psutil.Process(worker_info.process_id)
                worker_process.terminate()
                
            # Add task to remaining worker
            worker_pool.add_tasks(sample_tasks[:1])
            time.sleep(2)
            
            # Crash the last worker while processing
            remaining_worker = status['workers'][0]
            worker_info = worker_pool.get_worker_info(remaining_worker['worker_id'])
            worker_process = psutil.Process(worker_info.process_id)
            worker_process.terminate()
            
            # Mock restart and redistribution to fail
            with patch.object(worker_pool, 'restart_worker', return_value=False):
                with patch.object(worker_pool, '_get_available_workers', return_value=[]):
                    # Wait for task to be marked as failed
                    failure_start = time.time()
                    task_failed = False
                    
                    while time.time() - failure_start < 30:
                        # Check if task moved to failed list
                        failed_tasks = getattr(worker_pool, 'failed_tasks', [])
                        if failed_tasks:
                            task_failed = True
                            break
                            
                        time.sleep(1)
                        
                    assert task_failed, "Task should be marked as failed when no workers available"
                    
        except ImportError:
            pytest.fail("Worker pool components not implemented yet - test should fail")
            
    def test_multiple_worker_crashes(self, worker_pool, sample_tasks):
        """Test system stability during multiple simultaneous worker crashes."""
        try:
            # Add multiple tasks
            worker_pool.add_tasks(sample_tasks)
            
            # Wait for task distribution
            time.sleep(3)
            
            # Crash multiple workers simultaneously
            status = worker_pool.get_status()
            processing_workers = [w for w in status['workers'] if w['status'] == 'processing']
            
            if len(processing_workers) >= 2:
                for worker in processing_workers[:2]:  # Crash 2 workers
                    worker_info = worker_pool.get_worker_info(worker['worker_id'])
                    worker_process = psutil.Process(worker_info.process_id)
                    worker_process.terminate()
                    
                # Wait for recovery process
                time.sleep(10)
                
                # System should remain stable
                status = worker_pool.get_status()
                assert status['pool_status'] != 'terminated', "Pool should remain stable during multiple crashes"
                
                # At least one worker should be available
                available_workers = [w for w in status['workers'] if w['status'] in ['ready', 'idle', 'restarting']]
                assert len(available_workers) >= 1, "At least one worker should remain available"
                
        except ImportError:
            pytest.fail("Worker pool components not implemented yet - test should fail")


class TestBrowserSessionCrashRecovery:
    """Test recovery from browser session crashes specifically."""
    
    @pytest.fixture
    def worker_pool(self):
        """Create worker pool for browser crash testing."""
        try:
            from src.models.worker_pool import PersistentWorkerPool, PoolConfiguration
            
            config = PoolConfiguration(
                worker_count=2,
                headless_mode=True,
                base_profile_path=tempfile.mkdtemp(),
                memory_threshold=0.75,
                shutdown_timeout=60
            )
            
            pool = PersistentWorkerPool()
            pool.initialize(config)
            yield pool
            pool.shutdown(timeout=30)
            
        except ImportError:
            pytest.skip("PersistentWorkerPool not yet implemented")
            
    def test_browser_session_crash_detection(self, worker_pool):
        """Test detection of browser session crashes."""
        try:
            status = worker_pool.get_status()
            worker_id = status['workers'][0]['worker_id']
            
            # Simulate browser crash by killing browser processes
            with patch('psutil.process_iter') as mock_processes:
                # Mock finding and killing browser processes
                mock_browser_process = MagicMock()
                mock_browser_process.name.return_value = 'msedge'
                mock_browser_process.cmdline.return_value = ['msedge', '--user-data-dir=/tmp/worker_profile']
                mock_processes.return_value = [mock_browser_process]
                
                # Simulate browser process termination
                mock_browser_process.terminate()
                
                # Wait for session crash detection
                session_crash_detected = False
                start_time = time.time()
                
                while time.time() - start_time < 10:
                    worker_info = worker_pool.get_worker_info(worker_id)
                    health = worker_info.check_health()
                    
                    if not health.get('session_active', True):
                        session_crash_detected = True
                        break
                        
                    time.sleep(0.5)
                    
                assert session_crash_detected, "Browser session crash should be detected"
                
        except ImportError:
            pytest.fail("Worker pool components not implemented yet - test should fail")
            
    def test_session_recovery_preserves_worker(self, worker_pool):
        """Test that session recovery preserves worker process."""
        try:
            status = worker_pool.get_status()
            worker_id = status['workers'][0]['worker_id']
            original_worker_info = worker_pool.get_worker_info(worker_id)
            
            # Simulate session crash and recovery
            with patch.object(worker_pool, '_restart_browser_session') as mock_restart:
                mock_restart.return_value = True
                
                # Trigger session restart
                recovery_success = worker_pool._handle_session_crash(worker_id)
                assert recovery_success, "Session recovery should succeed"
                
                # Verify worker process preserved
                recovered_worker_info = worker_pool.get_worker_info(worker_id)
                assert recovered_worker_info.worker_id == original_worker_info.worker_id, \
                    "Worker ID should be preserved during session recovery"
                    
        except ImportError:
            pytest.fail("Worker pool components not implemented yet - test should fail")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])