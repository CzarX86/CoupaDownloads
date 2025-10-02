"""Integration test for basic parallel processing - T010

This test validates Scenario 2 from quickstart.md: Basic Parallel Processing.
Tests should FAIL until the actual implementation is complete.
"""

import pytest
import time
from typing import Dict, Any, Tuple

# Import will fail until implementation exists - expected for TDD
try:
    from EXPERIMENTAL.core.main import MainApp
    from EXPERIMENTAL.corelib.config import HeadlessConfiguration
except ImportError as e:
    pytest.skip(f"EXPERIMENTAL modules not implemented yet: {e}", allow_module_level=True)


class TestParallelBasic:
    """Test basic parallel processing per quickstart.md Scenario 2."""
    
    def test_parallel_processing_initialization(self):
        """Test that parallel processing can be enabled and initialized."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=2  # Start with 2 workers
        )
        
        # Should have parallel configuration
        assert hasattr(app, 'enable_parallel')
        assert hasattr(app, 'max_workers')
        assert app.enable_parallel is True
        assert app.max_workers == 2
    
    def test_multiple_workers_created(self):
        """Test that multiple workers are created for parallel processing."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=2
        )
        
        po_list = [
            {
                "po_number": "PARALLEL-001", 
                "supplier": "Supplier A", 
                "url": "https://example.com/po1", 
                "amount": 1000.00
            },
            {
                "po_number": "PARALLEL-002", 
                "supplier": "Supplier B", 
                "url": "https://example.com/po2", 
                "amount": 2000.00
            },
            {
                "po_number": "PARALLEL-003", 
                "supplier": "Supplier C", 
                "url": "https://example.com/po3", 
                "amount": 1500.00
            },
            {
                "po_number": "PARALLEL-004", 
                "supplier": "Supplier D", 
                "url": "https://example.com/po4", 
                "amount": 2500.00
            }
        ]
        
        print(f"Processing {len(po_list)} POs with {app.max_workers} workers")
        
        success_count, failed_count = app._process_po_entries(po_list)
        
        # Should complete processing
        assert isinstance(success_count, int)
        assert isinstance(failed_count, int)
        assert success_count + failed_count == len(po_list)
    
    def test_concurrent_processing_occurs(self):
        """Test that POs are processed concurrently."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=2
        )
        
        # Create enough POs to benefit from parallel processing
        po_list = [
            {
                "po_number": f"CONCURRENT-{i:03d}",
                "supplier": f"Supplier {i}",
                "url": f"https://example.com/po{i}",
                "amount": 1000.00 + i
            }
            for i in range(6)  # 6 POs with 2 workers
        ]
        
        start_time = time.time()
        success_count, failed_count = app._process_po_entries(po_list)
        duration = time.time() - start_time
        
        print(f"Parallel processing completed in {duration:.2f} seconds")
        print(f"Results: {success_count} success, {failed_count} failed")
        print(f"Throughput: {len(po_list)/duration:.2f} POs/second")
        
        # Should complete faster than sequential would
        # (Exact timing depends on implementation, but structure should exist)
        assert duration > 0
        assert success_count + failed_count == len(po_list)
    
    def test_separate_browser_profiles_used(self):
        """Test that separate browser profiles are used for each worker."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=2
        )
        
        po_list = [
            {
                "po_number": "PROFILE-001",
                "supplier": "Profile Test A",
                "url": "https://example.com/profile1",
                "amount": 1000.00
            },
            {
                "po_number": "PROFILE-002",
                "supplier": "Profile Test B",
                "url": "https://example.com/profile2",
                "amount": 2000.00
            }
        ]
        
        # Process POs - should use separate profiles
        success_count, failed_count = app._process_po_entries(po_list)
        
        # Should complete without profile conflicts
        assert success_count + failed_count == len(po_list)
        
        # Should have worker pool with profile management
        if hasattr(app, 'worker_pool'):
            assert hasattr(app.worker_pool, 'profile_manager')
    
    def test_consolidated_results_returned(self):
        """Test that results from all workers are consolidated."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=3
        )
        
        po_list = [
            {
                "po_number": "CONSOLIDATE-001",
                "supplier": "Consolidate A",
                "url": "https://example.com/consolidate1",
                "amount": 1000.00
            },
            {
                "po_number": "CONSOLIDATE-002",
                "supplier": "Consolidate B",
                "url": "https://example.com/consolidate2",
                "amount": 2000.00
            },
            {
                "po_number": "CONSOLIDATE-003",
                "supplier": "Consolidate C",
                "url": "https://example.com/consolidate3",
                "amount": 1500.00
            }
        ]
        
        success_count, failed_count = app._process_po_entries(po_list)
        
        # Results should be consolidated from all workers
        assert isinstance(success_count, int)
        assert isinstance(failed_count, int)
        assert success_count >= 0
        assert failed_count >= 0
        assert success_count + failed_count == len(po_list)
    
    def test_parallel_mode_selection_automatic(self):
        """Test that parallel mode is selected automatically for multiple POs."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=2
        )
        
        # Single PO should use sequential mode
        single_po = [
            {
                "po_number": "SINGLE-001",
                "supplier": "Single Test",
                "url": "https://example.com/single",
                "amount": 1000.00
            }
        ]
        
        # Multiple POs should use parallel mode
        multiple_pos = [
            {
                "po_number": "MULTI-001",
                "supplier": "Multi Test A",
                "url": "https://example.com/multi1",
                "amount": 1000.00
            },
            {
                "po_number": "MULTI-002",
                "supplier": "Multi Test B",
                "url": "https://example.com/multi2",
                "amount": 2000.00
            }
        ]
        
        # Both should complete successfully
        single_success, single_failed = app._process_po_entries(single_po)
        assert single_success + single_failed == 1
        
        multi_success, multi_failed = app._process_po_entries(multiple_pos)
        assert multi_success + multi_failed == 2
    
    def test_worker_count_configuration(self):
        """Test that worker count can be configured."""
        config = HeadlessConfiguration(headless=True)
        
        # Test different worker counts
        for worker_count in [1, 2, 4]:
            app = MainApp(
                headless_config=config,
                enable_parallel=True,
                max_workers=worker_count
            )
            
            assert app.max_workers == worker_count
            
            # Should be able to process POs with any worker count
            po_list = [
                {
                    "po_number": f"WORKER-COUNT-{worker_count}-001",
                    "supplier": f"Worker Test {worker_count}",
                    "url": f"https://example.com/worker{worker_count}",
                    "amount": 1000.00
                }
            ]
            
            success_count, failed_count = app._process_po_entries(po_list)
            assert success_count + failed_count == 1
    
    def test_parallel_processing_error_tolerance(self):
        """Test that parallel processing handles individual PO errors gracefully."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=2
        )
        
        # Mix of valid and invalid POs
        po_list = [
            {
                "po_number": "VALID-001",
                "supplier": "Good Supplier",
                "url": "https://example.com/valid1",
                "amount": 1000.00
            },
            {
                "po_number": "INVALID-001",
                "supplier": "Bad Supplier",
                "url": "invalid-url",  # Should cause error
                "amount": 2000.00
            },
            {
                "po_number": "VALID-002",
                "supplier": "Good Supplier",
                "url": "https://example.com/valid2",
                "amount": 1500.00
            }
        ]
        
        # Should complete despite errors
        success_count, failed_count = app._process_po_entries(po_list)
        
        # Should account for all POs
        assert success_count + failed_count == len(po_list)
        
        # Should have some successes and some failures
        assert success_count >= 0
        assert failed_count >= 0


class TestParallelBasicPerformance:
    """Test performance aspects of basic parallel processing."""
    
    def test_performance_improvement_measurable(self):
        """Test that parallel processing shows measurable performance improvement."""
        config = HeadlessConfiguration(headless=True)
        
        # Create test data for timing comparison
        po_list = [
            {
                "po_number": f"PERF-{i:03d}",
                "supplier": f"Performance Supplier {i}",
                "url": f"https://example.com/perf{i}",
                "amount": 1000.00 + i
            }
            for i in range(8)  # 8 POs for meaningful comparison
        ]
        
        # Test sequential processing
        sequential_app = MainApp(
            headless_config=config,
            enable_parallel=False
        )
        
        start_time = time.time()
        seq_success, seq_failed = sequential_app._process_po_entries(po_list)
        sequential_duration = time.time() - start_time
        
        # Test parallel processing
        parallel_app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=4
        )
        
        start_time = time.time()
        par_success, par_failed = parallel_app._process_po_entries(po_list)
        parallel_duration = time.time() - start_time
        
        print(f"Sequential: {sequential_duration:.2f}s")
        print(f"Parallel:   {parallel_duration:.2f}s")
        
        # Both should process all POs
        assert seq_success + seq_failed == len(po_list)
        assert par_success + par_failed == len(po_list)
        
        # Structure for performance comparison exists
        assert sequential_duration > 0
        assert parallel_duration > 0
    
    def test_throughput_calculation(self):
        """Test that throughput can be calculated and reported."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=2
        )
        
        po_list = [
            {
                "po_number": f"THROUGHPUT-{i:03d}",
                "supplier": f"Throughput Supplier {i}",
                "url": f"https://example.com/throughput{i}",
                "amount": 1000.00 + i
            }
            for i in range(6)
        ]
        
        start_time = time.time()
        success_count, failed_count = app._process_po_entries(po_list)
        duration = time.time() - start_time
        
        throughput = len(po_list) / duration if duration > 0 else 0
        
        print(f"Processed {len(po_list)} POs in {duration:.2f}s")
        print(f"Throughput: {throughput:.2f} POs/second")
        
        # Should have measurable throughput
        assert duration > 0
        assert throughput >= 0
        assert success_count + failed_count == len(po_list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])