"""
Contract tests for PersistentWorkerPoolInterface.
Tests the interface contract without implementation.
These tests MUST FAIL until the interface is implemented.
"""

import pytest
import sys
import os
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Add the project root to the path to import our contracts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import the interface contract from the specs
spec_path = os.path.join(os.path.dirname(__file__), '../../specs/005-persistent-worker-pool/contracts')
sys.path.insert(0, spec_path)

from worker_pool_interface import (
    PersistentWorkerPoolInterface,
    WorkerInterface,
    PoolConfiguration,
    POTask,
    ProcessingResult,
    WorkerInfo,
    PoolStatus,
    WorkerStatus,
    PoolError,
    ProfileCorruptionError,
    InsufficientResourcesError,
    PoolNotReadyError,
    WorkerNotFoundError,
    SessionTimeoutError
)


class TestPersistentWorkerPoolInterface:
    """Contract tests for PersistentWorkerPool interface compliance."""
    
    def test_pool_configuration_dataclass_structure(self):
        """Test that PoolConfiguration has required fields and types."""
        config = PoolConfiguration(
            worker_count=4,
            headless_mode=True,
            base_profile_path="/path/to/profile",
            memory_threshold=0.75,
            shutdown_timeout=60
        )
        
        assert config.worker_count == 4
        assert config.headless_mode is True
        assert config.base_profile_path == "/path/to/profile"
        assert config.memory_threshold == 0.75
        assert config.shutdown_timeout == 60
        
    def test_po_task_dataclass_structure(self):
        """Test that POTask has required fields and defaults."""
        task = POTask(
            task_id="test_001",
            po_number="PO-12345",
            po_data={"vendor": "TestCorp"}
        )
        
        assert task.task_id == "test_001"
        assert task.po_number == "PO-12345"
        assert task.po_data == {"vendor": "TestCorp"}
        assert task.priority == 0  # default
        assert task.retry_count == 0  # default
        
    def test_processing_result_dataclass_structure(self):
        """Test that ProcessingResult has required fields and defaults."""
        result = ProcessingResult(
            task_id="test_001",
            po_number="PO-12345",
            success=True,
            worker_id="worker_001",
            processing_time=15.5
        )
        
        assert result.task_id == "test_001"
        assert result.po_number == "PO-12345"
        assert result.success is True
        assert result.worker_id == "worker_001"
        assert result.processing_time == 15.5
        assert result.error_message is None  # default
        assert result.downloaded_files is None  # default
        
    def test_worker_info_dataclass_structure(self):
        """Test that WorkerInfo has required fields."""
        info = WorkerInfo(
            worker_id="worker_001",
            status=WorkerStatus.READY,
            memory_usage=1024*1024*500,  # 500MB
            processed_count=10,
            current_task="PO-12345",
            profile_path="/tmp/worker_001_profile"
        )
        
        assert info.worker_id == "worker_001"
        assert info.status == WorkerStatus.READY
        assert info.memory_usage == 1024*1024*500
        assert info.processed_count == 10
        assert info.current_task == "PO-12345"
        assert info.profile_path == "/tmp/worker_001_profile"
        
    def test_pool_status_enum_values(self):
        """Test that PoolStatus enum has expected values."""
        assert PoolStatus.INITIALIZING.value == "initializing"
        assert PoolStatus.READY.value == "ready"
        assert PoolStatus.PROCESSING.value == "processing"
        assert PoolStatus.SHUTTING_DOWN.value == "shutting_down"
        assert PoolStatus.TERMINATED.value == "terminated"
        
    def test_worker_status_enum_values(self):
        """Test that WorkerStatus enum has expected values."""
        assert WorkerStatus.STARTING.value == "starting"
        assert WorkerStatus.READY.value == "ready"
        assert WorkerStatus.PROCESSING.value == "processing"
        assert WorkerStatus.IDLE.value == "idle"
        assert WorkerStatus.CRASHED.value == "crashed"
        assert WorkerStatus.RESTARTING.value == "restarting"
        assert WorkerStatus.TERMINATING.value == "terminating"
        assert WorkerStatus.TERMINATED.value == "terminated"
        
    def test_exception_hierarchy(self):
        """Test that custom exceptions inherit from PoolError."""
        assert issubclass(ProfileCorruptionError, PoolError)
        assert issubclass(InsufficientResourcesError, PoolError)
        assert issubclass(PoolNotReadyError, PoolError)
        assert issubclass(WorkerNotFoundError, PoolError)
        assert issubclass(SessionTimeoutError, PoolError)
        assert issubclass(PoolError, Exception)


class TestPersistentWorkerPoolInterfaceContract:
    """Tests that will FAIL until PersistentWorkerPool implementation exists."""
    
    def test_worker_pool_interface_is_abstract(self):
        """Test that interface methods are abstract and raise NotImplementedError."""
        pool = PersistentWorkerPoolInterface()
        
        config = PoolConfiguration(
            worker_count=2,
            headless_mode=True,
            base_profile_path="/test/profile",
            memory_threshold=0.75,
            shutdown_timeout=60
        )
        
        # These should all fail with NotImplementedError until implemented
        with pytest.raises((NotImplementedError, TypeError)):
            pool.initialize(config)
            
        with pytest.raises((NotImplementedError, TypeError)):
            pool.add_tasks([])
            
        with pytest.raises((NotImplementedError, TypeError)):
            pool.get_status()
            
        with pytest.raises((NotImplementedError, TypeError)):
            pool.get_worker_info("worker_001")
            
        with pytest.raises((NotImplementedError, TypeError)):
            pool.restart_worker("worker_001")
            
        with pytest.raises((NotImplementedError, TypeError)):
            pool.shutdown()
            
        with pytest.raises((NotImplementedError, TypeError)):
            pool.force_shutdown()
            
    def test_worker_interface_is_abstract(self):
        """Test that WorkerInterface methods are abstract."""
        worker = WorkerInterface()
        
        # These should all fail until implemented
        with pytest.raises((NotImplementedError, TypeError)):
            worker.start("worker_001", "/tmp/profile", True)
            
        with pytest.raises((NotImplementedError, TypeError)):
            task = POTask("test", "PO-123", {})
            worker.process_task(task)
            
        with pytest.raises((NotImplementedError, TypeError)):
            worker.check_health()
            
        with pytest.raises((NotImplementedError, TypeError)):
            worker.stop()


class TestContractRequirements:
    """Test contract requirements that implementation must satisfy."""
    
    def test_configuration_validation_requirements(self):
        """Test that configuration enforces business rules."""
        # Worker count must be 1-8
        with pytest.raises(ValueError):
            PoolConfiguration(
                worker_count=0,  # Invalid: below minimum
                headless_mode=True,
                base_profile_path="/test",
                memory_threshold=0.75,
                shutdown_timeout=60
            )
            
        with pytest.raises(ValueError):
            PoolConfiguration(
                worker_count=9,  # Invalid: above maximum
                headless_mode=True,
                base_profile_path="/test",
                memory_threshold=0.75,
                shutdown_timeout=60
            )
            
        # Memory threshold must be 0.5-0.9 (50%-90%)
        with pytest.raises(ValueError):
            PoolConfiguration(
                worker_count=2,
                headless_mode=True,
                base_profile_path="/test",
                memory_threshold=0.4,  # Invalid: below 50%
                shutdown_timeout=60
            )
            
        with pytest.raises(ValueError):
            PoolConfiguration(
                worker_count=2,
                headless_mode=True,
                base_profile_path="/test",
                memory_threshold=0.95,  # Invalid: above 90%
                shutdown_timeout=60
            )
            
    def test_method_signature_compliance(self):
        """Test that interface methods have correct signatures."""
        import inspect
        
        # Check PersistentWorkerPoolInterface methods
        pool_methods = inspect.getmembers(PersistentWorkerPoolInterface, predicate=inspect.isfunction)
        method_names = [name for name, _ in pool_methods]
        
        required_methods = [
            'initialize', 'add_tasks', 'get_status', 'get_worker_info',
            'restart_worker', 'shutdown', 'force_shutdown'
        ]
        
        for method in required_methods:
            assert method in method_names, f"Missing required method: {method}"
            
        # Check WorkerInterface methods
        worker_methods = inspect.getmembers(WorkerInterface, predicate=inspect.isfunction)
        worker_method_names = [name for name, _ in worker_methods]
        
        required_worker_methods = ['start', 'process_task', 'check_health', 'stop']
        
        for method in required_worker_methods:
            assert method in worker_method_names, f"Missing required worker method: {method}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])