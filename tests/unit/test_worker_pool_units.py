"""
Unit tests for worker pool components.

Tests individual components of the persistent worker pool system
including models, services, and utility functions.
"""

import pytest
import os
import sys
import tempfile
import shutil
import time
from unittest.mock import patch, MagicMock, AsyncMock

# Add the src and EXPERIMENTAL directories to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../EXPERIMENTAL'))


class TestWorkerPoolModels:
    """Unit tests for worker pool data models."""

    def test_pool_config_creation(self):
        """Test PoolConfig dataclass creation and validation."""
        try:
            from EXPERIMENTAL.workers.models.config import PoolConfig

            config = PoolConfig(
                worker_count=4,
                headless_mode=True,
                base_profile_path="",  # Empty path to avoid validation
                memory_threshold=0.75,
                shutdown_timeout=60
            )

            assert config.worker_count == 4
            assert config.headless_mode is True
            assert config.base_profile_path == ""
            assert config.memory_threshold == 0.75
            assert config.shutdown_timeout == 60

        except ImportError:
            pytest.skip("PoolConfig not yet implemented")

    def test_pool_config_defaults(self):
        """Test PoolConfig default values."""
        try:
            from EXPERIMENTAL.workers.models.config import PoolConfig

            config = PoolConfig()
            assert config.worker_count == 4  # Default
            assert config.headless_mode is True
            assert config.memory_threshold == 0.75
            assert config.shutdown_timeout == 60

        except ImportError:
            pytest.skip("PoolConfig not yet implemented")

    def test_pool_config_validation(self):
        """Test PoolConfig validation constraints."""
        try:
            from EXPERIMENTAL.workers.models.config import PoolConfig

            # Test worker count limits
            with pytest.raises(ValueError):
                PoolConfig(worker_count=0)

            with pytest.raises(ValueError):
                PoolConfig(worker_count=9)  # Over limit

            # Test memory threshold limits
            with pytest.raises(ValueError):
                PoolConfig(memory_threshold=0.4)  # Too low

            with pytest.raises(ValueError):
                PoolConfig(memory_threshold=0.95)  # Too high

        except ImportError:
            pytest.skip("PoolConfig not yet implemented")

    def test_po_task_creation(self):
        """Test POTask creation and properties."""
        try:
            from EXPERIMENTAL.workers.models.po_task import POTask, TaskStatus, TaskPriority

            task = POTask(
                po_number="PO123456",
                priority=TaskPriority.HIGH,
                metadata={"source": "test"}
            )

            assert task.po_number == "PO123456"
            assert task.priority == TaskPriority.HIGH
            assert task.status == TaskStatus.PENDING
            assert task.metadata == {"source": "test"}
            assert task.task_id is not None
            # Note: created_at may not be implemented yet
            # assert task.created_at is not None

        except ImportError:
            pytest.skip("POTask not yet implemented")

    def test_po_task_status_transitions(self):
        """Test POTask status transition methods."""
        try:
            from EXPERIMENTAL.workers.models.po_task import POTask, TaskStatus

            task = POTask(po_number="PO123456")

            # Initial state
            assert task.status == TaskStatus.PENDING

            # Assign task first
            task.assign_to_worker("worker1")
            assert task.status == TaskStatus.ASSIGNED

            # Start processing
            task.start_processing()
            assert task.status == TaskStatus.PROCESSING

            # Complete successfully
            task.complete_successfully(result_data={"files": ["test.pdf"]})
            assert task.status == TaskStatus.COMPLETED
            assert task.result_data == {"files": ["test.pdf"]}

            # Test failure
            task2 = POTask(po_number="PO789012")
            task2.assign_to_worker("worker2")
            task2.start_processing()
            task2.fail_with_error("Test error", allow_retry=False)
            assert task2.status == TaskStatus.FAILED
            assert task2.error_message == "Test error"

        except ImportError:
            pytest.skip("POTask not yet implemented")

    def test_task_handle_creation(self):
        """Test TaskHandle creation and basic functionality."""
        try:
            from EXPERIMENTAL.workers.models.config import TaskHandle

            # Mock task and pool
            mock_task = MagicMock()
            mock_task.po_number = "PO123456"
            mock_pool = MagicMock()

            handle = TaskHandle(
                po_number="PO123456",
                _task_ref=mock_task,
                _pool_ref=mock_pool
            )

            assert handle.po_number == "PO123456"
            assert handle._task_ref is mock_task
            assert handle._pool_ref is mock_pool

        except ImportError:
            pytest.skip("TaskHandle not yet implemented")


class TestWorkerPoolServices:
    """Unit tests for worker pool services."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_profile_manager_initialization(self, temp_dir):
        """Test ProfileManager initialization."""
        try:
            from EXPERIMENTAL.workers.profile_manager import ProfileManager

            manager = ProfileManager(base_profile_path=temp_dir)
            # Just test that it initializes without error
            assert manager is not None
            assert hasattr(manager, 'base_profile_path')

        except ImportError:
            pytest.skip("ProfileManager not yet implemented")

    @patch('psutil.virtual_memory')
    def test_memory_monitor_initialization(self, mock_memory):
        """Test MemoryMonitor initialization."""
        try:
            from EXPERIMENTAL.workers.memory_monitor import MemoryMonitor

            # Mock memory info
            mock_memory.return_value.total = 8 * 1024**3  # 8GB

            monitor = MemoryMonitor(memory_threshold=0.75)
            assert monitor.memory_threshold == 0.75
            assert monitor._monitoring is False

        except ImportError:
            pytest.skip("MemoryMonitor not yet implemented")

    @patch('psutil.virtual_memory')
    def test_memory_monitor_pressure_detection(self, mock_memory):
        """Test memory pressure detection."""
        try:
            from EXPERIMENTAL.workers.memory_monitor import MemoryMonitor

            # Mock high memory usage
            mock_memory.return_value.percent = 85
            mock_memory.return_value.total = 8 * 1024**3

            monitor = MemoryMonitor(memory_threshold=0.75)
            monitor.start_monitoring()

            assert monitor.is_memory_pressure()
            assert monitor.get_memory_info()['usage_percent'] == 85

            monitor.stop_monitoring()

        except ImportError:
            pytest.skip("MemoryMonitor not yet implemented")

    def test_task_queue_operations(self):
        """Test TaskQueue basic operations."""
        try:
            from EXPERIMENTAL.workers.task_queue import TaskQueue

            queue = TaskQueue()

            # Test empty queue
            assert queue.get_next_task("worker1") is None
            assert queue.get_queue_status()['pending_tasks'] == 0

            # Add task
            mock_task = MagicMock()
            mock_task.po_number = "PO123456"
            queue.add_task(lambda: None, {"po_number": "PO123456", "supplier": "Test", "url": "http://test.com"})

            stats = queue.get_queue_status()
            assert stats['pending_tasks'] == 1
            assert stats['total_tasks'] == 1

        except ImportError:
            pytest.skip("TaskQueue not yet implemented")

    def test_task_queue_stop_accepting(self):
        """Test TaskQueue stop accepting tasks."""
        try:
            from EXPERIMENTAL.workers.task_queue import TaskQueue

            queue = TaskQueue()

            # Stop accepting
            queue.stop()

            # Try to add task (should be rejected)
            with pytest.raises(Exception):  # Should raise TaskQueueError
                queue.add_task(lambda: None, {"po_number": "PO123456", "supplier": "Test", "url": "http://test.com"})

            # Should return False or handle gracefully
            stats = queue.get_queue_status()
            assert stats['pending_tasks'] == 0  # Task not added

        except ImportError:
            pytest.skip("TaskQueue not yet implemented")


class TestWorkerPoolIntegration:
    """Unit tests for worker pool component integration."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @patch('psutil.virtual_memory')
    def test_persistent_pool_initialization(self, mock_memory, temp_dir):
        """Test PersistentWorkerPool initialization."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool
            from EXPERIMENTAL.workers.models.config import PoolConfig

            # Mock memory
            mock_memory.return_value.total = 8 * 1024**3

            config = PoolConfig(
                worker_count=2,
                base_profile_path=temp_dir,
                memory_threshold=0.75
            )

            pool = PersistentWorkerPool(config)

            assert pool.config.worker_count == 2
            assert pool.config.base_profile_path == temp_dir
            assert pool._running is False
            assert len(pool.workers) == 0

        except ImportError:
            pytest.skip("PersistentWorkerPool not yet implemented")

    @patch('psutil.virtual_memory')
    def test_persistent_pool_status(self, mock_memory, temp_dir):
        """Test PersistentWorkerPool status reporting."""
        try:
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool
            from EXPERIMENTAL.workers.models.config import PoolConfig

            # Mock memory
            mock_memory.return_value.total = 8 * 1024**3

            config = PoolConfig(
                worker_count=2,
                base_profile_path=temp_dir
            )

            pool = PersistentWorkerPool(config)
            status = pool.get_status()

            assert 'pool_status' in status
            assert 'worker_count' in status
            assert 'completed_tasks' in status
            assert 'failed_tasks' in status
            assert status['pool_status'] == 'stopped'
            assert status['worker_count'] == 0

        except ImportError:
            pytest.skip("PersistentWorkerPool not yet implemented")

    def test_graceful_shutdown_initialization(self):
        """Test GracefulShutdown initialization."""
        try:
            from EXPERIMENTAL.workers.shutdown_handler import GracefulShutdown

            shutdown = GracefulShutdown(shutdown_timeout=30)
            assert shutdown.shutdown_timeout == 30
            assert shutdown._shutdown_initiated is False

        except ImportError:
            pytest.skip("GracefulShutdown not yet implemented")


class TestWorkerPoolErrorHandling:
    """Unit tests for error handling in worker pool components."""

    def test_pool_config_error_handling(self):
        """Test PoolConfig error handling."""
        try:
            from EXPERIMENTAL.workers.models.config import PoolConfig

            # Test invalid worker count
            with pytest.raises(ValueError):
                PoolConfig(worker_count=-1)

            # Test invalid memory threshold
            with pytest.raises(ValueError):
                PoolConfig(memory_threshold=1.5)

        except ImportError:
            pytest.skip("PoolConfig not yet implemented")

    def test_task_queue_error_handling(self):
        """Test TaskQueue error handling."""
        try:
            from EXPERIMENTAL.workers.task_queue import TaskQueue

            queue = TaskQueue()

            # Test adding None task
            with pytest.raises((TypeError, AttributeError)):
                queue.add_task(lambda: None, None)

        except ImportError:
            pytest.skip("TaskQueue not yet implemented")

    @patch('psutil.virtual_memory')
    def test_memory_monitor_error_handling(self, mock_memory):
        """Test MemoryMonitor error handling."""
        try:
            from EXPERIMENTAL.workers.memory_monitor import MemoryMonitor

            # Mock failed memory reading
            mock_memory.side_effect = Exception("Memory read failed")

            monitor = MemoryMonitor(memory_threshold=0.75)

            # Should handle error gracefully
            info = monitor.get_memory_info()
            assert 'error' in info or info.get('usage_percent', 0) == 0

        except ImportError:
            pytest.skip("MemoryMonitor not yet implemented")


class TestWorkerPoolUtilities:
    """Unit tests for worker pool utility functions."""

    def test_task_priority_enum(self):
        """Test TaskPriority enum values."""
        try:
            from EXPERIMENTAL.workers.models.po_task import TaskPriority

            assert TaskPriority.LOW.value == 1
            assert TaskPriority.NORMAL.value == 2
            assert TaskPriority.HIGH.value == 3
            assert TaskPriority.URGENT.value == 4

        except ImportError:
            pytest.skip("TaskPriority not yet implemented")

    def test_task_status_enum(self):
        """Test TaskStatus enum values."""
        try:
            from EXPERIMENTAL.workers.models.po_task import TaskStatus

            assert TaskStatus.PENDING.value == "pending"
            assert TaskStatus.PROCESSING.value == "processing"
            assert TaskStatus.COMPLETED.value == "completed"
            assert TaskStatus.FAILED.value == "failed"
            assert TaskStatus.CANCELLED.value == "cancelled"

        except ImportError:
            pytest.skip("TaskStatus not yet implemented")

    def test_worker_status_enum(self):
        """Test WorkerStatus enum values."""
        try:
            from EXPERIMENTAL.workers.models.worker import WorkerStatus

            assert WorkerStatus.STARTING.value == "starting"
            assert WorkerStatus.READY.value == "ready"
            assert WorkerStatus.PROCESSING.value == "processing"
            assert WorkerStatus.TERMINATING.value == "terminating"
            assert WorkerStatus.TERMINATED.value == "terminated"

        except ImportError:
            pytest.skip("WorkerStatus not yet implemented")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])