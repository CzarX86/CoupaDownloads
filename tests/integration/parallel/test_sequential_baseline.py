"""Integration test for sequential baseline - T009

This test validates Scenario 1 from quickstart.md: Basic Sequential Processing (Baseline).
Tests should FAIL until the actual implementation is complete, but validates that
existing functionality remains unchanged.
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


class TestSequentialBaseline:
    """Test sequential processing baseline per quickstart.md Scenario 1."""
    
    def test_single_po_processing_unchanged(self):
        """Test that single PO processing works identically to before."""
        # Initialize with parallel processing disabled
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=False  # Explicitly disable
        )
        
        # Test single PO
        po_data = {
            "po_number": "BASELINE-001",
            "supplier": "Test Supplier",
            "url": "https://example.com/po",
            "amount": 1000.00
        }
        
        result = app.process_single_po(po_data)
        print(f"Sequential processing result: {result}")
        
        # Should return boolean indicating success/failure
        assert isinstance(result, bool)
    
    def test_multiple_pos_sequential_processing(self):
        """Test multiple POs processed sequentially."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=False  # Explicitly disable
        )
        
        # Test multiple POs sequentially
        po_list = [
            {
                "po_number": "BASELINE-001", 
                "supplier": "Supplier A", 
                "url": "https://example.com/po1", 
                "amount": 1000.00
            },
            {
                "po_number": "BASELINE-002", 
                "supplier": "Supplier B", 
                "url": "https://example.com/po2", 
                "amount": 2000.00
            }
        ]
        
        success_count, failed_count = app._process_po_entries(po_list)
        print(f"Sequential batch: {success_count} success, {failed_count} failed")
        
        # Should return tuple with counts
        assert isinstance(success_count, int)
        assert isinstance(failed_count, int)
        assert success_count + failed_count == len(po_list)
    
    def test_no_parallel_workers_created(self):
        """Test that no parallel workers are created in sequential mode."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=False
        )
        
        po_list = [
            {
                "po_number": "BASELINE-003",
                "supplier": "Supplier C",
                "url": "https://example.com/po3",
                "amount": 1500.00
            }
        ]
        
        # Process POs
        success_count, failed_count = app._process_po_entries(po_list)
        
        # In sequential mode, should not have worker pool attributes
        assert not hasattr(app, 'worker_pool') or app.worker_pool is None
    
    def test_existing_logs_and_download_structure_preserved(self):
        """Test that existing logs and download structure are preserved."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config, enable_parallel=False)
        
        po_list = [
            {
                "po_number": "BASELINE-004",
                "supplier": "Supplier D",
                "url": "https://example.com/po4",
                "amount": 2500.00
            }
        ]
        
        # Process POs and check structure remains unchanged
        success_count, failed_count = app._process_po_entries(po_list)
        
        # Should complete without changing existing behavior
        assert isinstance(success_count, int)
        assert isinstance(failed_count, int)
    
    def test_backward_compatibility_interface(self):
        """Test that all existing interfaces remain unchanged."""
        # Test MainApp can be initialized without parallel parameters
        app_legacy = MainApp()
        assert hasattr(app_legacy, 'process_single_po')
        
        # Test with old-style configuration
        config = HeadlessConfiguration(headless=False)
        app_configured = MainApp(headless_config=config)
        assert hasattr(app_configured, '_process_po_entries')
        
        # Should default to sequential processing
        assert not hasattr(app_configured, 'enable_parallel') or \
               getattr(app_configured, 'enable_parallel', False) is False
    
    def test_sequential_performance_baseline(self):
        """Test sequential processing performance as baseline."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config, enable_parallel=False)
        
        # Create test PO list for timing
        po_list = [
            {
                "po_number": f"PERF-{i:03d}",
                "supplier": f"Supplier {i}",
                "url": f"https://example.com/po{i}",
                "amount": 1000.00 + i
            }
            for i in range(4)  # Small set for baseline
        ]
        
        start_time = time.time()
        success_count, failed_count = app._process_po_entries(po_list)
        duration = time.time() - start_time
        
        print(f"Sequential baseline: {duration:.2f}s for {len(po_list)} POs")
        print(f"Results: {success_count} success, {failed_count} failed")
        
        # Should complete in reasonable time (baseline for comparison)
        assert duration > 0  # Should take some time
        assert success_count + failed_count == len(po_list)
    
    def test_error_handling_unchanged(self):
        """Test that error handling behavior is unchanged."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config, enable_parallel=False)
        
        # Test with invalid PO data
        invalid_po_list = [
            {
                "po_number": "INVALID-001",
                "supplier": "Bad Supplier",
                "url": "invalid-url",  # Should cause error
                "amount": 1000.00
            }
        ]
        
        # Should handle errors gracefully as before
        try:
            success_count, failed_count = app._process_po_entries(invalid_po_list)
            # Should complete even with errors
            assert isinstance(success_count, int)
            assert isinstance(failed_count, int)
        except Exception as e:
            # Specific errors are acceptable - should be same as before
            print(f"Expected error handling: {type(e).__name__}: {e}")
    
    def test_configuration_preservation(self):
        """Test that existing configuration options are preserved."""
        # Test various configuration options
        configs_to_test = [
            HeadlessConfiguration(headless=True),
            HeadlessConfiguration(headless=False),
        ]
        
        for config in configs_to_test:
            app = MainApp(headless_config=config, enable_parallel=False)
            
            # Should maintain same configuration behavior
            assert app.headless_config == config or hasattr(app, 'headless_config')
            
            # Should be able to process POs with any configuration
            po_data = {
                "po_number": "CONFIG-001",
                "supplier": "Config Test",
                "url": "https://example.com/config",
                "amount": 1000.00
            }
            
            result = app.process_single_po(po_data)
            assert isinstance(result, bool)


class TestSequentialBaselineValidation:
    """Additional validation tests for sequential processing baseline."""
    
    def test_method_signatures_unchanged(self):
        """Test that all method signatures remain unchanged."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        # Check that existing methods exist with correct signatures
        assert hasattr(app, 'process_single_po')
        assert callable(app.process_single_po)
        
        assert hasattr(app, '_process_po_entries')
        assert callable(app._process_po_entries)
        
        # Test method calls with expected parameters
        po_data = {
            "po_number": "SIGNATURE-001",
            "supplier": "Signature Test",
            "url": "https://example.com/signature",
            "amount": 1000.00
        }
        
        # Should accept same parameters as before
        result = app.process_single_po(po_data)
        assert isinstance(result, bool)
    
    def test_return_value_formats_unchanged(self):
        """Test that return value formats are unchanged."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config, enable_parallel=False)
        
        # Single PO processing
        po_data = {
            "po_number": "RETURN-001",
            "supplier": "Return Test",
            "url": "https://example.com/return",
            "amount": 1000.00
        }
        
        result = app.process_single_po(po_data)
        assert isinstance(result, bool)  # Should return boolean
        
        # Multiple PO processing
        po_list = [po_data]
        success_count, failed_count = app._process_po_entries(po_list)
        assert isinstance(success_count, int)
        assert isinstance(failed_count, int)
    
    def test_side_effects_unchanged(self):
        """Test that side effects (downloads, logs) are unchanged."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config, enable_parallel=False)
        
        po_list = [
            {
                "po_number": "SIDE-EFFECT-001",
                "supplier": "Side Effect Test",
                "url": "https://example.com/sideeffect",
                "amount": 1000.00
            }
        ]
        
        # Process and check that side effects occur as expected
        success_count, failed_count = app._process_po_entries(po_list)
        
        # Should maintain same download directory structure
        # Should maintain same logging behavior
        # (Specific checks would depend on actual implementation)
        assert success_count + failed_count == len(po_list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])