"""Unit tests for WorkerPool component - T015

Tests for EXPERIMENTAL.workers.pool.WorkerPool per worker_pool_contract.md.
Tests should FAIL until the actual implementation is complete.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from typing import List, Dict, Any

# Import will fail until implementation exists - expected for TDD
try:
    from EXPERIMENTAL.workers.pool import WorkerPool
    from EXPERIMENTAL.workers.exceptions import (
        WorkerPoolError,
        WorkerCreationError,
        WorkerTimeoutError,
        ProfileConflictError
    )
except ImportError as e:
    pytest.skip(f"WorkerPool modules not implemented yet: {e}", allow_module_level=True)


class TestWorkerPoolInitialization:
    """Test WorkerPool initialization and configuration."""
    
    def test_default_initialization(self):
        """Test WorkerPool creation with default parameters."""
        pool = WorkerPool()
        
        # Validate default configuration
        assert pool.max_workers == 2, "Default max_workers should be 2"
        assert pool.is_active() == False, "Pool should not be active initially"
        assert pool.get_worker_count() == 0, "Initial worker count should be 0"
        assert pool.get_status() == "initialized", "Initial status should be 'initialized'"
    
    def test_custom_initialization(self):
        """Test WorkerPool creation with custom parameters."""
        pool = WorkerPool(max_workers=4, profile_prefix="test_")
        
        # Validate custom configuration
        assert pool.max_workers == 4, "Custom max_workers should be respected"
        assert pool.profile_prefix == "test_", "Custom profile_prefix should be set"
        assert pool.is_active() == False, "Pool should not be active initially"
        assert pool.get_worker_count() == 0, "Initial worker count should be 0"
    
    def test_invalid_max_workers_validation(self):
        """Test validation of max_workers parameter."""
        # Test zero workers
        with pytest.raises(ValueError, match="max_workers must be positive"):
            WorkerPool(max_workers=0)
        
        # Test negative workers
        with pytest.raises(ValueError, match="max_workers must be positive"):
            WorkerPool(max_workers=-1)
        
        # Test excessive workers
        with pytest.raises(ValueError, match="max_workers cannot exceed"):
            WorkerPool(max_workers=100)
    
    def test_profile_prefix_validation(self):
        """Test validation of profile_prefix parameter."""
        # Valid prefix
        pool = WorkerPool(profile_prefix="valid_prefix_")
        assert pool.profile_prefix == "valid_prefix_"
        
        # Empty prefix should use default
        pool = WorkerPool(profile_prefix="")
        assert pool.profile_prefix == "coupa_worker_"
        
        # Invalid characters should raise error
        with pytest.raises(ValueError, match="Invalid characters in profile_prefix"):
            WorkerPool(profile_prefix="invalid/prefix")


class TestWorkerPoolLifecycle:
    """Test WorkerPool lifecycle management."""
    
    def test_start_pool_success(self):
        """Test successful pool startup."""
        pool = WorkerPool(max_workers=2)
        
        # Start the pool
        pool.start()
        
        # Validate pool state after start
        assert pool.is_active() == True, "Pool should be active after start"
        assert pool.get_status() == "running", "Status should be 'running' after start"
        assert pool.get_worker_count() == 2, "Worker count should match max_workers"
        
        # Cleanup
        pool.stop()
    
    def test_start_already_active_pool(self):
        """Test starting an already active pool."""
        pool = WorkerPool(max_workers=2)
        pool.start()
        
        # Starting again should be idempotent
        pool.start()
        assert pool.is_active() == True, "Pool should remain active"
        assert pool.get_worker_count() == 2, "Worker count should remain unchanged"
        
        pool.stop()
    
    def test_stop_pool_success(self):
        """Test successful pool shutdown."""
        pool = WorkerPool(max_workers=2)
        pool.start()
        
        # Stop the pool
        pool.stop()
        
        # Validate pool state after stop
        assert pool.is_active() == False, "Pool should not be active after stop"
        assert pool.get_status() == "stopped", "Status should be 'stopped' after stop"
        assert pool.get_worker_count() == 0, "Worker count should be 0 after stop"
    
    def test_stop_inactive_pool(self):
        """Test stopping an inactive pool."""
        pool = WorkerPool(max_workers=2)
        
        # Stopping inactive pool should be safe
        pool.stop()
        assert pool.is_active() == False, "Pool should remain inactive"
        assert pool.get_worker_count() == 0, "Worker count should remain 0"
    
    def test_pool_context_manager(self):
        """Test WorkerPool as context manager."""
        with WorkerPool(max_workers=2) as pool:
            assert pool.is_active() == True, "Pool should be active in context"
            assert pool.get_worker_count() == 2, "Workers should be created"
        
        # Pool should be stopped after context
        assert pool.is_active() == False, "Pool should be stopped after context"
        assert pool.get_worker_count() == 0, "Workers should be cleaned up"


class TestWorkerManagement:
    """Test worker creation and management."""
    
    def test_worker_creation_success(self):
        """Test successful worker creation."""
        pool = WorkerPool(max_workers=3)
        pool.start()
        
        # Validate workers are created
        assert pool.get_worker_count() == 3, "All workers should be created"
        
        # Check worker details
        workers = pool.get_worker_details()
        assert len(workers) == 3, "Worker details should match count"
        
        for worker in workers:
            assert 'worker_id' in worker, "Worker should have ID"
            assert 'profile_path' in worker, "Worker should have profile path"
            assert 'status' in worker, "Worker should have status"
            assert worker['status'] == 'ready', "Worker should be ready"
        
        pool.stop()
    
    def test_worker_profile_isolation(self):
        """Test that workers have isolated profiles."""
        pool = WorkerPool(max_workers=2, profile_prefix="isolation_test_")
        pool.start()
        
        workers = pool.get_worker_details()
        profile_paths = [w['profile_path'] for w in workers]
        
        # All profile paths should be different
        assert len(set(profile_paths)) == len(profile_paths), "Profile paths should be unique"
        
        # All should contain the prefix
        for path in profile_paths:
            assert "isolation_test_" in path, "Profile path should contain prefix"
        
        pool.stop()
    
    def test_worker_failure_handling(self):
        """Test handling of worker creation failures."""
        pool = WorkerPool(max_workers=2)
        
        # Mock worker creation to fail
        with patch('EXPERIMENTAL.workers.pool.WorkerPool._create_worker') as mock_create:
            mock_create.side_effect = WorkerCreationError("Mocked worker creation failure")
            
            # Starting should handle worker creation failures
            pool.start()
            
            # Pool should still be active but with reduced workers
            assert pool.is_active() == True, "Pool should be active despite failures"
            assert pool.get_worker_count() < 2, "Worker count should be reduced"
            
            pool.stop()
    
    def test_dynamic_worker_scaling(self):
        """Test dynamic scaling of worker count."""
        pool = WorkerPool(max_workers=4)
        pool.start()
        
        # Initial state
        assert pool.get_worker_count() == 4, "Should start with max workers"
        
        # Scale down
        pool.resize(2)
        assert pool.get_worker_count() == 2, "Should scale down to 2 workers"
        
        # Scale up
        pool.resize(3)
        assert pool.get_worker_count() == 3, "Should scale up to 3 workers"
        
        # Cannot scale beyond max
        with pytest.raises(ValueError, match="Cannot resize beyond max_workers"):
            pool.resize(5)
        
        pool.stop()


class TestTaskExecution:
    """Test task execution and distribution."""
    
    def test_submit_task_success(self):
        """Test successful task submission."""
        pool = WorkerPool(max_workers=2)
        pool.start()
        
        # Submit a simple task
        def sample_task(po_data):
            return {"success": True, "po": po_data["po_number"]}
        
        po_data = {"po_number": "TASK-001", "supplier": "Test Supplier"}
        future = pool.submit_task(sample_task, po_data)
        
        # Validate future object
        assert future is not None, "Should return a future object"
        assert hasattr(future, 'result'), "Future should have result method"
        assert hasattr(future, 'done'), "Future should have done method"
        
        pool.stop()
    
    def test_submit_multiple_tasks(self):
        """Test submitting multiple tasks concurrently."""
        pool = WorkerPool(max_workers=2)
        pool.start()
        
        def process_po(po_data):
            time.sleep(0.1)  # Simulate work
            return {"processed": po_data["po_number"]}
        
        # Submit multiple tasks
        tasks = []
        for i in range(4):
            po_data = {"po_number": f"MULTI-{i:03d}", "supplier": f"Supplier {i}"}
            future = pool.submit_task(process_po, po_data)
            tasks.append(future)
        
        # Validate all tasks were submitted
        assert len(tasks) == 4, "All tasks should be submitted"
        
        # Wait for completion and check results
        results = []
        for future in tasks:
            result = future.result(timeout=5.0)
            results.append(result)
        
        assert len(results) == 4, "All tasks should complete"
        
        pool.stop()
    
    def test_task_timeout_handling(self):
        """Test handling of task timeouts."""
        pool = WorkerPool(max_workers=1)
        pool.start()
        
        def slow_task(po_data):
            time.sleep(10)  # Task that takes too long
            return {"processed": po_data["po_number"]}
        
        po_data = {"po_number": "TIMEOUT-001", "supplier": "Slow Supplier"}
        future = pool.submit_task(slow_task, po_data)
        
        # Should timeout
        with pytest.raises(WorkerTimeoutError):
            future.result(timeout=1.0)
        
        pool.stop()
    
    def test_task_exception_handling(self):
        """Test handling of task exceptions."""
        pool = WorkerPool(max_workers=1)
        pool.start()
        
        def failing_task(po_data):
            raise Exception("Task processing failed")
        
        po_data = {"po_number": "FAIL-001", "supplier": "Failing Supplier"}
        future = pool.submit_task(failing_task, po_data)
        
        # Should capture the exception
        with pytest.raises(Exception, match="Task processing failed"):
            future.result()
        
        pool.stop()


class TestPerformanceAndMonitoring:
    """Test performance characteristics and monitoring."""
    
    def test_get_status_information(self):
        """Test getting detailed status information."""
        pool = WorkerPool(max_workers=2)
        pool.start()
        
        status = pool.get_status()
        assert status == "running", "Status should be 'running'"
        
        # Check detailed status
        details = pool.get_detailed_status()
        assert 'status' in details, "Should include basic status"
        assert 'worker_count' in details, "Should include worker count"
        assert 'active_tasks' in details, "Should include active task count"
        assert 'completed_tasks' in details, "Should include completed task count"
        assert 'failed_tasks' in details, "Should include failed task count"
        
        pool.stop()
    
    def test_performance_metrics_collection(self):
        """Test collection of performance metrics."""
        pool = WorkerPool(max_workers=2)
        pool.start()
        
        # Submit some tasks to generate metrics
        def quick_task(po_data):
            return {"result": "success"}
        
        for i in range(5):
            po_data = {"po_number": f"METRIC-{i:03d}"}
            future = pool.submit_task(quick_task, po_data)
            future.result()  # Wait for completion
        
        # Get performance metrics
        metrics = pool.get_performance_metrics()
        
        assert 'total_tasks' in metrics, "Should track total tasks"
        assert 'completed_tasks' in metrics, "Should track completed tasks"
        assert 'average_task_time' in metrics, "Should track average task time"
        assert 'throughput' in metrics, "Should track throughput"
        
        assert metrics['total_tasks'] >= 5, "Should count submitted tasks"
        assert metrics['completed_tasks'] >= 5, "Should count completed tasks"
        
        pool.stop()
    
    def test_resource_usage_monitoring(self):
        """Test monitoring of resource usage."""
        pool = WorkerPool(max_workers=2)
        pool.start()
        
        # Get resource usage
        resources = pool.get_resource_usage()
        
        assert 'memory_usage' in resources, "Should track memory usage"
        assert 'cpu_usage' in resources, "Should track CPU usage"
        assert 'profile_disk_usage' in resources, "Should track profile disk usage"
        
        # Values should be reasonable
        assert resources['memory_usage'] >= 0, "Memory usage should be non-negative"
        assert resources['cpu_usage'] >= 0, "CPU usage should be non-negative"
        assert resources['profile_disk_usage'] >= 0, "Disk usage should be non-negative"
        
        pool.stop()


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_pool_error_propagation(self):
        """Test that pool errors are properly propagated."""
        pool = WorkerPool(max_workers=2)
        
        # Test error when submitting to inactive pool
        def sample_task(po_data):
            return po_data
        
        with pytest.raises(WorkerPoolError, match="Cannot submit task to inactive pool"):
            pool.submit_task(sample_task, {"po_number": "ERROR-001"})
    
    def test_profile_conflict_handling(self):
        """Test handling of profile conflicts."""
        pool = WorkerPool(max_workers=2, profile_prefix="conflict_test_")
        
        # Mock profile conflict
        with patch('EXPERIMENTAL.workers.pool.WorkerPool._create_worker') as mock_create:
            mock_create.side_effect = ProfileConflictError("Profile already in use")
            
            # Should handle conflict gracefully
            with pytest.raises(WorkerPoolError, match="Failed to create workers"):
                pool.start()
    
    def test_cleanup_on_failure(self):
        """Test that cleanup happens properly on failures."""
        pool = WorkerPool(max_workers=2)
        
        # Mock partial failure during start
        with patch('EXPERIMENTAL.workers.pool.WorkerPool._create_worker') as mock_create:
            # First worker succeeds, second fails
            mock_create.side_effect = [Mock(), WorkerCreationError("Second worker failed")]
            
            pool.start()
            
            # Should clean up properly
            pool.stop()
            assert pool.get_worker_count() == 0, "All workers should be cleaned up"
    
    def test_concurrent_operation_safety(self):
        """Test safety of concurrent operations."""
        pool = WorkerPool(max_workers=2)
        pool.start()
        
        # Test concurrent start/stop operations
        def start_stop_worker():
            pool.start()
            time.sleep(0.1)
            pool.stop()
        
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=start_stop_worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Pool should be in a consistent state
        assert pool.get_worker_count() == 0, "Pool should be properly stopped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])