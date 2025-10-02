"""Unit tests for ProcessingSession component - T018

Tests for EXPERIMENTAL.workers.session.ProcessingSession per processing_session_contract.md.
Tests should FAIL until the actual implementation is complete.
"""

import pytest
import time
import tempfile
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import will fail until implementation exists - expected for TDD
try:
    from EXPERIMENTAL.workers.session import ProcessingSession
    from EXPERIMENTAL.workers.exceptions import (
        ProcessingSessionError,
        SessionConfigurationError,
        SessionStateError,
        WorkerAllocationError
    )
    from EXPERIMENTAL.corelib.config import HeadlessConfiguration
except ImportError as e:
    pytest.skip(f"ProcessingSession modules not implemented yet: {e}", allow_module_level=True)


class TestProcessingSessionInitialization:
    """Test ProcessingSession initialization and configuration."""
    
    def test_default_initialization(self):
        """Test ProcessingSession creation with default parameters."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(headless_config=config)
        
        # Validate default configuration
        assert session.mode == "sequential", "Default mode should be sequential"
        assert session.max_workers == 1, "Default max_workers should be 1 for sequential"
        assert session.is_active() == False, "Session should not be active initially"
        assert session.get_status() == "initialized", "Initial status should be 'initialized'"
    
    def test_sequential_mode_initialization(self):
        """Test initialization in sequential mode."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(
            headless_config=config,
            mode="sequential"
        )
        
        # Validate sequential configuration
        assert session.mode == "sequential", "Mode should be sequential"
        assert session.max_workers == 1, "Sequential mode should use 1 worker"
        assert not hasattr(session, 'worker_pool') or session.worker_pool is None, \
               "Sequential mode should not use worker pool"
    
    def test_parallel_mode_initialization(self):
        """Test initialization in parallel mode."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(
            headless_config=config,
            mode="parallel",
            max_workers=4
        )
        
        # Validate parallel configuration
        assert session.mode == "parallel", "Mode should be parallel"
        assert session.max_workers == 4, "Should use specified worker count"
        assert hasattr(session, 'worker_pool'), "Parallel mode should have worker pool"
    
    def test_invalid_mode_validation(self):
        """Test validation of processing mode."""
        config = HeadlessConfiguration(headless=True)
        
        # Invalid mode
        with pytest.raises(ValueError, match="Invalid processing mode"):
            ProcessingSession(headless_config=config, mode="invalid_mode")
        
        # None mode
        with pytest.raises(ValueError, match="Processing mode cannot be None"):
            ProcessingSession(headless_config=config, mode=None)
    
    def test_max_workers_validation(self):
        """Test validation of max_workers parameter."""
        config = HeadlessConfiguration(headless=True)
        
        # Zero workers in parallel mode
        with pytest.raises(ValueError, match="max_workers must be positive"):
            ProcessingSession(
                headless_config=config,
                mode="parallel",
                max_workers=0
            )
        
        # Negative workers
        with pytest.raises(ValueError, match="max_workers must be positive"):
            ProcessingSession(
                headless_config=config,
                mode="parallel",
                max_workers=-1
            )
        
        # Excessive workers
        with pytest.raises(ValueError, match="max_workers cannot exceed"):
            ProcessingSession(
                headless_config=config,
                mode="parallel",
                max_workers=100
            )
    
    def test_headless_config_validation(self):
        """Test validation of headless configuration."""
        # None config
        with pytest.raises(ValueError, match="headless_config cannot be None"):
            ProcessingSession(headless_config=None)
        
        # Invalid config type
        with pytest.raises(TypeError, match="headless_config must be HeadlessConfiguration"):
            ProcessingSession(headless_config="invalid_config")


class TestSessionLifecycle:
    """Test session lifecycle management."""
    
    def test_start_sequential_session(self):
        """Test starting session in sequential mode."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(headless_config=config, mode="sequential")
        
        # Start session
        session.start()
        
        # Validate session state
        assert session.is_active() == True, "Session should be active after start"
        assert session.get_status() == "running", "Status should be 'running'"
        
        # Cleanup
        session.stop()
    
    def test_start_parallel_session(self):
        """Test starting session in parallel mode."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(
            headless_config=config,
            mode="parallel",
            max_workers=2
        )
        
        # Start session
        session.start()
        
        # Validate session state
        assert session.is_active() == True, "Session should be active after start"
        assert session.get_status() == "running", "Status should be 'running'"
        assert session.get_worker_count() == 2, "Should have 2 workers"
        
        # Cleanup
        session.stop()
    
    def test_stop_session(self):
        """Test stopping an active session."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(
            headless_config=config,
            mode="parallel",
            max_workers=2
        )
        
        session.start()
        
        # Stop session
        session.stop()
        
        # Validate session state
        assert session.is_active() == False, "Session should not be active after stop"
        assert session.get_status() == "stopped", "Status should be 'stopped'"
        assert session.get_worker_count() == 0, "Worker count should be 0"
    
    def test_session_context_manager(self):
        """Test ProcessingSession as context manager."""
        config = HeadlessConfiguration(headless=True)
        
        with ProcessingSession(headless_config=config, mode="parallel", max_workers=2) as session:
            assert session.is_active() == True, "Session should be active in context"
            assert session.get_worker_count() == 2, "Workers should be available"
        
        # Session should be stopped after context
        assert session.is_active() == False, "Session should be stopped after context"
        assert session.get_worker_count() == 0, "Workers should be cleaned up"
    
    def test_restart_session(self):
        """Test restarting a stopped session."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(headless_config=config, mode="parallel", max_workers=2)
        
        # Start, stop, and restart
        session.start()
        session.stop()
        session.start()
        
        # Should be active again
        assert session.is_active() == True, "Session should be active after restart"
        assert session.get_worker_count() == 2, "Workers should be recreated"
        
        session.stop()


class TestDataProcessing:
    """Test data processing functionality."""
    
    def test_process_po_entries_sequential(self):
        """Test processing PO entries in sequential mode."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(headless_config=config, mode="sequential")
        
        po_list = [
            {
                "po_number": "SEQ-001",
                "supplier": "Sequential Supplier A",
                "url": "https://example.com/seq1",
                "amount": 1000.00
            },
            {
                "po_number": "SEQ-002",
                "supplier": "Sequential Supplier B",
                "url": "https://example.com/seq2",
                "amount": 2000.00
            }
        ]
        
        session.start()
        
        # Process PO entries
        success_count, failed_count = session.process_po_entries(
            po_list,
            hierarchy_cols=[],
            has_hierarchy_data=False
        )
        
        # Validate processing results
        assert success_count + failed_count == 2, "All POs should be processed"
        assert success_count >= 0, "Success count should be non-negative"
        assert failed_count >= 0, "Failed count should be non-negative"
        
        session.stop()
    
    def test_process_po_entries_parallel(self):
        """Test processing PO entries in parallel mode."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(
            headless_config=config,
            mode="parallel",
            max_workers=2
        )
        
        po_list = [
            {
                "po_number": f"PAR-{i:03d}",
                "supplier": f"Parallel Supplier {i}",
                "url": f"https://example.com/par{i}",
                "amount": 1000.00 + i
            }
            for i in range(4)
        ]
        
        session.start()
        
        # Process PO entries
        success_count, failed_count = session.process_po_entries(
            po_list,
            hierarchy_cols=[],
            has_hierarchy_data=False
        )
        
        # Validate processing results
        assert success_count + failed_count == 4, "All POs should be processed"
        assert success_count >= 0, "Success count should be non-negative"
        assert failed_count >= 0, "Failed count should be non-negative"
        
        session.stop()
    
    def test_process_with_hierarchy_data(self):
        """Test processing PO entries with hierarchy data."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(headless_config=config, mode="sequential")
        
        po_list = [
            {
                "po_number": "HIER-001",
                "supplier": "Hierarchy Supplier A",
                "url": "https://example.com/hier1",
                "amount": 1000.00,
                "category": "Category A",
                "department": "Finance"
            },
            {
                "po_number": "HIER-002",
                "supplier": "Hierarchy Supplier B",
                "url": "https://example.com/hier2",
                "amount": 2000.00,
                "category": "Category B",
                "department": "IT"
            }
        ]
        
        hierarchy_cols = ["category", "department"]
        
        session.start()
        
        # Process with hierarchy
        success_count, failed_count = session.process_po_entries(
            po_list,
            hierarchy_cols=hierarchy_cols,
            has_hierarchy_data=True
        )
        
        # Validate processing
        assert success_count + failed_count == 2, "All hierarchy POs should be processed"
        
        session.stop()
    
    def test_process_inactive_session(self):
        """Test processing with inactive session."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(headless_config=config, mode="sequential")
        
        po_list = [{"po_number": "INACTIVE-001", "supplier": "Test"}]
        
        # Try to process without starting session
        with pytest.raises(SessionStateError, match="Session must be active"):
            session.process_po_entries(po_list, [], False)


class TestProgressTracking:
    """Test progress tracking functionality."""
    
    def test_progress_tracking_sequential(self):
        """Test progress tracking in sequential mode."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(headless_config=config, mode="sequential")
        
        po_list = [
            {"po_number": f"PROG-{i:03d}", "supplier": f"Supplier {i}"}
            for i in range(5)
        ]
        
        session.start()
        
        # Mock processing to track progress
        progress_updates = []
        
        def progress_callback(progress):
            progress_updates.append(progress)
        
        # Process with progress tracking
        session.set_progress_callback(progress_callback)
        session.process_po_entries(po_list, [], False)
        
        # Validate progress tracking
        assert len(progress_updates) > 0, "Progress updates should be generated"
        
        # Check progress structure
        final_progress = progress_updates[-1]
        assert 'completed' in final_progress, "Progress should include completed count"
        assert 'total' in final_progress, "Progress should include total count"
        assert 'percentage' in final_progress, "Progress should include percentage"
        
        assert final_progress['total'] == 5, "Total should match PO count"
        assert final_progress['completed'] <= 5, "Completed should not exceed total"
        
        session.stop()
    
    def test_progress_tracking_parallel(self):
        """Test progress tracking in parallel mode."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(
            headless_config=config,
            mode="parallel",
            max_workers=2
        )
        
        po_list = [
            {"po_number": f"PARPROG-{i:03d}", "supplier": f"Parallel Supplier {i}"}
            for i in range(6)
        ]
        
        session.start()
        
        # Track progress
        progress_updates = []
        
        def progress_callback(progress):
            progress_updates.append(progress.copy())
        
        session.set_progress_callback(progress_callback)
        session.process_po_entries(po_list, [], False)
        
        # Validate parallel progress tracking
        assert len(progress_updates) > 0, "Progress updates should be generated"
        
        final_progress = progress_updates[-1]
        assert final_progress['total'] == 6, "Total should match PO count"
        assert final_progress['completed'] <= 6, "Completed should not exceed total"
        
        session.stop()
    
    def test_real_time_statistics(self):
        """Test real-time processing statistics."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(
            headless_config=config,
            mode="parallel",
            max_workers=2
        )
        
        session.start()
        
        # Get initial statistics
        initial_stats = session.get_statistics()
        
        assert 'total_processed' in initial_stats, "Should include total processed"
        assert 'success_count' in initial_stats, "Should include success count"
        assert 'failed_count' in initial_stats, "Should include failed count"
        assert 'processing_rate' in initial_stats, "Should include processing rate"
        assert 'estimated_completion' in initial_stats, "Should include ETA"
        
        # Initial values should be zero
        assert initial_stats['total_processed'] == 0, "Initial processed should be 0"
        assert initial_stats['success_count'] == 0, "Initial success should be 0"
        assert initial_stats['failed_count'] == 0, "Initial failed should be 0"
        
        session.stop()
    
    def test_time_estimation(self):
        """Test time estimation functionality."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(headless_config=config, mode="sequential")
        
        po_list = [
            {"po_number": f"TIME-{i:03d}", "supplier": f"Time Supplier {i}"}
            for i in range(3)
        ]
        
        session.start()
        
        # Start processing and check time estimates
        start_time = time.time()
        
        # Mock partial processing to get estimates
        session._start_processing(po_list, [], False)
        
        # Get time estimates
        estimates = session.get_time_estimates()
        
        assert 'elapsed_time' in estimates, "Should include elapsed time"
        assert 'estimated_remaining' in estimates, "Should include remaining time"
        assert 'estimated_total' in estimates, "Should include total time estimate"
        
        assert estimates['elapsed_time'] >= 0, "Elapsed time should be non-negative"
        
        session.stop()


class TestMainAppIntegration:
    """Test integration with MainApp."""
    
    def test_mainapp_compatibility_sequential(self):
        """Test compatibility with MainApp in sequential mode."""
        config = HeadlessConfiguration(headless=True)
        
        # Mock MainApp behavior
        with patch('EXPERIMENTAL.core.main.MainApp') as MockMainApp:
            mock_app = MockMainApp.return_value
            mock_app._process_po_entries.return_value = (2, 0)  # 2 success, 0 failed
            
            session = ProcessingSession(
                headless_config=config,
                mode="sequential"
            )
            
            session.start()
            
            po_list = [
                {"po_number": "COMPAT-001", "supplier": "Compat Supplier A"},
                {"po_number": "COMPAT-002", "supplier": "Compat Supplier B"}
            ]
            
            # Process through session
            success, failed = session.process_po_entries(po_list, [], False)
            
            # Validate integration
            assert success == 2, "Should return MainApp success count"
            assert failed == 0, "Should return MainApp failed count"
            
            session.stop()
    
    def test_mainapp_parameter_forwarding(self):
        """Test that parameters are correctly forwarded to MainApp."""
        config = HeadlessConfiguration(headless=True)
        
        with patch('EXPERIMENTAL.core.main.MainApp') as MockMainApp:
            mock_app = MockMainApp.return_value
            mock_app._process_po_entries.return_value = (1, 0)
            
            session = ProcessingSession(headless_config=config, mode="sequential")
            session.start()
            
            po_list = [{"po_number": "FORWARD-001", "supplier": "Forward Supplier"}]
            hierarchy_cols = ["category"]
            
            # Process with specific parameters
            session.process_po_entries(
                po_list,
                hierarchy_cols=hierarchy_cols,
                has_hierarchy_data=True
            )
            
            # Verify parameters were forwarded
            mock_app._process_po_entries.assert_called_once()
            call_args = mock_app._process_po_entries.call_args
            
            assert call_args[0][0] == po_list, "PO list should be forwarded"
            assert call_args[1]['hierarchy_cols'] == hierarchy_cols, "Hierarchy cols should be forwarded"
            assert call_args[1]['has_hierarchy_data'] == True, "Hierarchy flag should be forwarded"
            
            session.stop()
    
    def test_error_handling_from_mainapp(self):
        """Test handling of errors from MainApp."""
        config = HeadlessConfiguration(headless=True)
        
        with patch('EXPERIMENTAL.core.main.MainApp') as MockMainApp:
            mock_app = MockMainApp.return_value
            mock_app._process_po_entries.side_effect = Exception("MainApp processing error")
            
            session = ProcessingSession(headless_config=config, mode="sequential")
            session.start()
            
            po_list = [{"po_number": "ERROR-001", "supplier": "Error Supplier"}]
            
            # Should handle MainApp errors gracefully
            with pytest.raises(ProcessingSessionError, match="Failed to process PO entries"):
                session.process_po_entries(po_list, [], False)
            
            session.stop()


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_worker_allocation_failure(self):
        """Test handling of worker allocation failures."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(
            headless_config=config,
            mode="parallel",
            max_workers=4
        )
        
        # Mock worker allocation failure
        with patch('EXPERIMENTAL.workers.pool.WorkerPool.start') as mock_start:
            mock_start.side_effect = WorkerAllocationError("Failed to allocate workers")
            
            with pytest.raises(ProcessingSessionError, match="Failed to start session"):
                session.start()
    
    def test_invalid_po_data_handling(self):
        """Test handling of invalid PO data."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(headless_config=config, mode="sequential")
        session.start()
        
        # Invalid PO data
        invalid_po_list = [
            None,  # None entry
            {},    # Empty entry
            {"po_number": ""},  # Missing required fields
            {"invalid": "data"}  # Wrong structure
        ]
        
        # Should handle invalid data gracefully
        success, failed = session.process_po_entries(invalid_po_list, [], False)
        assert success + failed == len(invalid_po_list), "All entries should be accounted for"
        assert failed > 0, "Some entries should fail validation"
        
        session.stop()
    
    def test_session_state_validation(self):
        """Test validation of session state for operations."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(headless_config=config, mode="sequential")
        
        # Operations on unstarted session
        with pytest.raises(SessionStateError):
            session.process_po_entries([], [], False)
        
        with pytest.raises(SessionStateError):
            session.get_statistics()
        
        # Start session
        session.start()
        
        # Stop session
        session.stop()
        
        # Operations on stopped session
        with pytest.raises(SessionStateError):
            session.process_po_entries([], [], False)
    
    def test_concurrent_session_operations(self):
        """Test safety of concurrent session operations."""
        config = HeadlessConfiguration(headless=True)
        session = ProcessingSession(
            headless_config=config,
            mode="parallel",
            max_workers=2
        )
        
        import threading
        
        errors = []
        
        def start_stop_worker():
            try:
                session.start()
                time.sleep(0.01)
                session.stop()
            except Exception as e:
                errors.append(e)
        
        # Run concurrent start/stop operations
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=start_stop_worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should handle concurrent operations gracefully
        # Some operations may fail, but session should be in consistent state
        assert session.get_status() in ["initialized", "stopped"], "Session should be in valid state"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])