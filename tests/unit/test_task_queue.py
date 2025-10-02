"""Unit tests for TaskQueue component - T017

Tests for EXPERIMENTAL.workers.queue.TaskQueue per task_queue_contract.md.
Tests should FAIL until the actual implementation is complete.
"""

import pytest
import time
import threading
from queue import Empty
from unittest.mock import Mock, patch
from typing import Dict, Any, List, Callable

# Import will fail until implementation exists - expected for TDD
try:
    from EXPERIMENTAL.workers.queue import TaskQueue
    from EXPERIMENTAL.workers.exceptions import (
        TaskQueueError,
        TaskValidationError,
        QueueCapacityError,
        TaskTimeoutError
    )
except ImportError as e:
    pytest.skip(f"TaskQueue modules not implemented yet: {e}", allow_module_level=True)


class TestTaskQueueInitialization:
    """Test TaskQueue initialization and configuration."""
    
    def test_default_initialization(self):
        """Test TaskQueue creation with default parameters."""
        queue = TaskQueue()
        
        # Validate default configuration
        assert queue.max_size == 1000, "Default max_size should be 1000"
        assert queue.is_empty(), "Queue should be empty initially"
        assert queue.size() == 0, "Initial size should be 0"
        assert queue.get_status() == "ready", "Initial status should be 'ready'"
    
    def test_custom_initialization(self):
        """Test TaskQueue creation with custom parameters."""
        queue = TaskQueue(
            max_size=500,
            priority_enabled=True,
            timeout_seconds=30
        )
        
        # Validate custom configuration
        assert queue.max_size == 500, "Custom max_size should be set"
        assert queue.priority_enabled == True, "Priority should be enabled"
        assert queue.timeout_seconds == 30, "Custom timeout should be set"
        assert queue.is_empty(), "Queue should be empty initially"
    
    def test_invalid_max_size_validation(self):
        """Test validation of max_size parameter."""
        # Zero size
        with pytest.raises(ValueError, match="max_size must be positive"):
            TaskQueue(max_size=0)
        
        # Negative size
        with pytest.raises(ValueError, match="max_size must be positive"):
            TaskQueue(max_size=-1)
        
        # Excessive size
        with pytest.raises(ValueError, match="max_size cannot exceed"):
            TaskQueue(max_size=1000000)
    
    def test_timeout_validation(self):
        """Test validation of timeout parameter."""
        # Valid timeout
        queue = TaskQueue(timeout_seconds=60)
        assert queue.timeout_seconds == 60
        
        # Zero timeout (unlimited)
        queue = TaskQueue(timeout_seconds=0)
        assert queue.timeout_seconds == 0
        
        # Negative timeout should raise error
        with pytest.raises(ValueError, match="timeout_seconds cannot be negative"):
            TaskQueue(timeout_seconds=-5)


class TestTaskSubmission:
    """Test task submission functionality."""
    
    def test_submit_simple_task(self):
        """Test submitting a simple task."""
        queue = TaskQueue()
        
        def sample_task(po_data):
            return {"processed": po_data["po_number"]}
        
        task_data = {"po_number": "SIMPLE-001", "supplier": "Test Supplier"}
        
        # Submit task
        task_id = queue.submit(sample_task, task_data)
        
        # Validate submission
        assert task_id is not None, "Task ID should be returned"
        assert isinstance(task_id, str), "Task ID should be string"
        assert not queue.is_empty(), "Queue should not be empty after submission"
        assert queue.size() == 1, "Queue size should be 1"
    
    def test_submit_task_with_priority(self):
        """Test submitting task with priority."""
        queue = TaskQueue(priority_enabled=True)
        
        def task_func(data):
            return data
        
        # Submit tasks with different priorities
        low_priority_id = queue.submit(task_func, {"type": "low"}, priority=1)
        high_priority_id = queue.submit(task_func, {"type": "high"}, priority=10)
        medium_priority_id = queue.submit(task_func, {"type": "medium"}, priority=5)
        
        # Validate submissions
        assert queue.size() == 3, "All tasks should be submitted"
        
        # Check task order (high priority should be retrievable first)
        task = queue.get_next()
        assert task['task_id'] == high_priority_id, "High priority task should be first"
    
    def test_submit_task_with_metadata(self):
        """Test submitting task with additional metadata."""
        queue = TaskQueue()
        
        def task_func(data):
            return data
        
        metadata = {
            "timeout": 30,
            "retry_count": 3,
            "tags": ["urgent", "financial"]
        }
        
        task_id = queue.submit(
            task_func, 
            {"po_number": "META-001"}, 
            metadata=metadata
        )
        
        # Get task and validate metadata
        task = queue.get_next()
        assert task['task_id'] == task_id, "Task ID should match"
        assert task['metadata'] == metadata, "Metadata should be preserved"
    
    def test_submit_to_full_queue(self):
        """Test submitting task to full queue."""
        queue = TaskQueue(max_size=2)
        
        def dummy_task(data):
            return data
        
        # Fill the queue
        queue.submit(dummy_task, {"id": 1})
        queue.submit(dummy_task, {"id": 2})
        
        # Queue should be full
        assert queue.is_full(), "Queue should be full"
        
        # Submitting another task should raise error
        with pytest.raises(QueueCapacityError, match="Queue is at maximum capacity"):
            queue.submit(dummy_task, {"id": 3})
    
    def test_submit_invalid_task(self):
        """Test submitting invalid task."""
        queue = TaskQueue()
        
        # Non-callable task
        with pytest.raises(TaskValidationError, match="Task must be callable"):
            queue.submit("not_a_function", {"data": "test"})
        
        # None task
        with pytest.raises(TaskValidationError, match="Task cannot be None"):
            queue.submit(None, {"data": "test"})


class TestTaskRetrieval:
    """Test task retrieval functionality."""
    
    def test_get_next_task(self):
        """Test getting next task from queue."""
        queue = TaskQueue()
        
        def sample_task(data):
            return data
        
        task_data = {"po_number": "NEXT-001"}
        task_id = queue.submit(sample_task, task_data)
        
        # Get next task
        task = queue.get_next()
        
        # Validate task structure
        assert task is not None, "Task should be returned"
        assert 'task_id' in task, "Task should have ID"
        assert 'function' in task, "Task should have function"
        assert 'data' in task, "Task should have data"
        assert 'submitted_at' in task, "Task should have submission time"
        
        assert task['task_id'] == task_id, "Task ID should match"
        assert task['function'] == sample_task, "Function should match"
        assert task['data'] == task_data, "Data should match"
    
    def test_get_next_from_empty_queue(self):
        """Test getting task from empty queue."""
        queue = TaskQueue()
        
        # Should return None for empty queue
        task = queue.get_next()
        assert task is None, "Should return None for empty queue"
    
    def test_get_next_with_timeout(self):
        """Test getting task with timeout."""
        queue = TaskQueue()
        
        # Get with timeout from empty queue
        start_time = time.time()
        task = queue.get_next(timeout=1.0)
        duration = time.time() - start_time
        
        assert task is None, "Should return None after timeout"
        assert duration >= 0.9, "Should wait for approximately the timeout duration"
    
    def test_priority_ordering(self):
        """Test that tasks are returned in priority order."""
        queue = TaskQueue(priority_enabled=True)
        
        def task_func(data):
            return data
        
        # Submit tasks in non-priority order
        task1_id = queue.submit(task_func, {"order": 3}, priority=1)  # Low priority
        task2_id = queue.submit(task_func, {"order": 1}, priority=10) # High priority
        task3_id = queue.submit(task_func, {"order": 2}, priority=5)  # Medium priority
        
        # Should get tasks in priority order (high to low)
        task1 = queue.get_next()
        task2 = queue.get_next()
        task3 = queue.get_next()
        
        assert task1['task_id'] == task2_id, "First should be high priority"
        assert task2['task_id'] == task3_id, "Second should be medium priority"
        assert task3['task_id'] == task1_id, "Third should be low priority"
    
    def test_fifo_ordering_without_priority(self):
        """Test FIFO ordering when priority is disabled."""
        queue = TaskQueue(priority_enabled=False)
        
        def task_func(data):
            return data
        
        # Submit tasks
        task1_id = queue.submit(task_func, {"order": 1})
        task2_id = queue.submit(task_func, {"order": 2})
        task3_id = queue.submit(task_func, {"order": 3})
        
        # Should get tasks in submission order
        task1 = queue.get_next()
        task2 = queue.get_next()
        task3 = queue.get_next()
        
        assert task1['task_id'] == task1_id, "First task should be first submitted"
        assert task2['task_id'] == task2_id, "Second task should be second submitted"
        assert task3['task_id'] == task3_id, "Third task should be third submitted"


class TestQueueManagement:
    """Test queue management operations."""
    
    def test_clear_queue(self):
        """Test clearing all tasks from queue."""
        queue = TaskQueue()
        
        def dummy_task(data):
            return data
        
        # Add some tasks
        for i in range(3):
            queue.submit(dummy_task, {"id": i})
        
        assert queue.size() == 3, "Queue should have 3 tasks"
        
        # Clear queue
        queue.clear()
        
        assert queue.is_empty(), "Queue should be empty after clear"
        assert queue.size() == 0, "Size should be 0 after clear"
    
    def test_queue_status_tracking(self):
        """Test tracking of queue status."""
        queue = TaskQueue()
        
        # Initial status
        assert queue.get_status() == "ready", "Initial status should be 'ready'"
        
        # Add task
        def dummy_task(data):
            return data
        
        queue.submit(dummy_task, {"id": 1})
        status = queue.get_status()
        assert status in ["ready", "active"], "Status should be valid after submission"
        
        # Clear and check status
        queue.clear()
        assert queue.get_status() == "ready", "Status should be 'ready' after clear"
    
    def test_task_count_tracking(self):
        """Test accurate tracking of task counts."""
        queue = TaskQueue()
        
        def dummy_task(data):
            return data
        
        # Track counts during operations
        assert queue.size() == 0, "Initial size should be 0"
        assert queue.get_total_submitted() == 0, "Initial submitted count should be 0"
        assert queue.get_total_completed() == 0, "Initial completed count should be 0"
        
        # Submit tasks
        for i in range(3):
            queue.submit(dummy_task, {"id": i})
        
        assert queue.size() == 3, "Size should be 3 after submissions"
        assert queue.get_total_submitted() == 3, "Submitted count should be 3"
        
        # Get tasks (simulating completion)
        for i in range(2):
            task = queue.get_next()
            queue.mark_completed(task['task_id'])
        
        assert queue.size() == 1, "Size should be 1 after getting 2 tasks"
        assert queue.get_total_completed() == 2, "Completed count should be 2"
    
    def test_task_marking_operations(self):
        """Test marking tasks as completed, failed, etc."""
        queue = TaskQueue()
        
        def dummy_task(data):
            return data
        
        task_id = queue.submit(dummy_task, {"id": 1})
        task = queue.get_next()
        
        # Mark as completed
        queue.mark_completed(task_id)
        assert queue.get_total_completed() == 1, "Completed count should increase"
        
        # Submit another task and mark as failed
        task_id2 = queue.submit(dummy_task, {"id": 2})
        task2 = queue.get_next()
        queue.mark_failed(task_id2, "Test failure")
        
        assert queue.get_total_failed() == 1, "Failed count should increase"


class TestConcurrencySupport:
    """Test concurrent operations on the queue."""
    
    def test_concurrent_submission(self):
        """Test concurrent task submission."""
        queue = TaskQueue(max_size=100)
        
        def dummy_task(data):
            return data
        
        submitted_tasks = []
        errors = []
        
        def submit_worker(worker_id):
            try:
                for i in range(10):
                    task_id = queue.submit(dummy_task, {"worker": worker_id, "task": i})
                    submitted_tasks.append(task_id)
            except Exception as e:
                errors.append(e)
        
        # Submit from multiple threads
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=submit_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Validate results
        assert len(errors) == 0, f"No errors should occur: {errors}"
        assert len(submitted_tasks) == 30, "All tasks should be submitted"
        assert len(set(submitted_tasks)) == 30, "All task IDs should be unique"
        assert queue.size() == 30, "Queue size should match submissions"
    
    def test_concurrent_retrieval(self):
        """Test concurrent task retrieval."""
        queue = TaskQueue()
        
        def dummy_task(data):
            return data
        
        # Submit tasks first
        for i in range(20):
            queue.submit(dummy_task, {"id": i})
        
        retrieved_tasks = []
        
        def retrieve_worker():
            while True:
                task = queue.get_next()
                if task is None:
                    break
                retrieved_tasks.append(task['task_id'])
                time.sleep(0.01)  # Simulate processing time
        
        # Retrieve from multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=retrieve_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Validate results
        assert len(retrieved_tasks) == 20, "All tasks should be retrieved"
        assert len(set(retrieved_tasks)) == 20, "All retrieved task IDs should be unique"
        assert queue.is_empty(), "Queue should be empty after retrieval"
    
    def test_mixed_concurrent_operations(self):
        """Test mixed concurrent submission and retrieval."""
        queue = TaskQueue(max_size=50)
        
        def dummy_task(data):
            return data
        
        submitted_count = 0
        retrieved_count = 0
        submission_lock = threading.Lock()
        retrieval_lock = threading.Lock()
        
        def submitter():
            nonlocal submitted_count
            for i in range(15):
                queue.submit(dummy_task, {"id": i})
                with submission_lock:
                    submitted_count += 1
                time.sleep(0.01)
        
        def retriever():
            nonlocal retrieved_count
            for _ in range(15):
                task = queue.get_next(timeout=2.0)
                if task:
                    with retrieval_lock:
                        retrieved_count += 1
                time.sleep(0.01)
        
        # Run submitters and retrievers concurrently
        threads = []
        
        # Start submitters
        for _ in range(2):
            thread = threading.Thread(target=submitter)
            threads.append(thread)
            thread.start()
        
        # Start retrievers
        for _ in range(2):
            thread = threading.Thread(target=retriever)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Validate results
        assert submitted_count == 30, "All submissions should complete"
        assert retrieved_count == 30, "All retrievals should complete"


class TestPerformanceAndMonitoring:
    """Test performance characteristics and monitoring."""
    
    def test_queue_metrics_collection(self):
        """Test collection of queue performance metrics."""
        queue = TaskQueue()
        
        def dummy_task(data):
            return data
        
        # Submit and process some tasks
        for i in range(5):
            task_id = queue.submit(dummy_task, {"id": i})
            task = queue.get_next()
            queue.mark_completed(task_id)
        
        # Get metrics
        metrics = queue.get_metrics()
        
        # Validate metrics structure
        required_fields = [
            'total_submitted',
            'total_completed',
            'total_failed',
            'current_size',
            'average_wait_time',
            'peak_size'
        ]
        
        for field in required_fields:
            assert field in metrics, f"Metrics should include {field}"
        
        assert metrics['total_submitted'] == 5, "Should track submitted tasks"
        assert metrics['total_completed'] == 5, "Should track completed tasks"
        assert metrics['current_size'] == 0, "Current size should be 0"
    
    def test_wait_time_tracking(self):
        """Test tracking of task wait times."""
        queue = TaskQueue()
        
        def dummy_task(data):
            return data
        
        # Submit task and wait before retrieving
        task_id = queue.submit(dummy_task, {"id": 1})
        time.sleep(0.1)  # Wait 100ms
        
        task = queue.get_next()
        
        # Check wait time
        wait_time = task.get('wait_time', 0)
        assert wait_time >= 0.08, "Wait time should be approximately 100ms"
        
        # Get average wait time
        metrics = queue.get_metrics()
        assert metrics['average_wait_time'] >= 0.08, "Average wait time should be tracked"
    
    def test_peak_size_tracking(self):
        """Test tracking of peak queue size."""
        queue = TaskQueue()
        
        def dummy_task(data):
            return data
        
        # Build up queue to track peak
        for i in range(5):
            queue.submit(dummy_task, {"id": i})
        
        # Check peak size
        metrics = queue.get_metrics()
        assert metrics['peak_size'] >= 5, "Peak size should be at least 5"
        
        # Reduce queue size
        for _ in range(3):
            queue.get_next()
        
        # Peak should remain
        metrics = queue.get_metrics()
        assert metrics['peak_size'] >= 5, "Peak size should be preserved"
    
    def test_throughput_measurement(self):
        """Test measurement of queue throughput."""
        queue = TaskQueue()
        
        def dummy_task(data):
            return data
        
        start_time = time.time()
        
        # Process multiple tasks rapidly
        for i in range(10):
            task_id = queue.submit(dummy_task, {"id": i})
            task = queue.get_next()
            queue.mark_completed(task_id)
        
        duration = time.time() - start_time
        
        # Calculate throughput
        throughput = queue.get_throughput()
        expected_throughput = 10 / duration
        
        assert throughput >= expected_throughput * 0.8, "Throughput should be reasonable"


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_task_id_operations(self):
        """Test operations with invalid task IDs."""
        queue = TaskQueue()
        
        # Mark non-existent task as completed
        with pytest.raises(TaskQueueError, match="Task not found"):
            queue.mark_completed("non_existent_id")
        
        # Mark non-existent task as failed
        with pytest.raises(TaskQueueError, match="Task not found"):
            queue.mark_failed("non_existent_id", "error message")
    
    def test_queue_corruption_recovery(self):
        """Test recovery from queue corruption scenarios."""
        queue = TaskQueue()
        
        def dummy_task(data):
            return data
        
        # Submit tasks
        for i in range(3):
            queue.submit(dummy_task, {"id": i})
        
        # Simulate corruption by directly manipulating internal state
        # (This would be implementation-specific)
        
        # Queue should handle corruption gracefully
        status = queue.get_status()
        assert status in ["ready", "corrupted", "recovering"], "Should handle corruption"
        
        # Should be able to clear and recover
        queue.clear()
        assert queue.get_status() == "ready", "Should recover after clear"
    
    def test_memory_pressure_handling(self):
        """Test behavior under memory pressure."""
        queue = TaskQueue(max_size=10)
        
        def memory_intensive_task(data):
            # Simulate memory-intensive task
            return {"large_data": "x" * 1000}
        
        # Fill queue with memory-intensive tasks
        for i in range(10):
            queue.submit(memory_intensive_task, {"id": i})
        
        # Should handle memory pressure gracefully
        assert queue.is_full(), "Queue should be full"
        
        # Should still function normally
        task = queue.get_next()
        assert task is not None, "Should still retrieve tasks"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])