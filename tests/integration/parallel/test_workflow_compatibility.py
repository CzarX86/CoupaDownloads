"""Integration test for existing workflow compatibility - T014

This test validates that existing workflows remain fully functional.
Tests should FAIL until the actual implementation is complete.
"""

import pytest
import os
import tempfile
import csv
from typing import Dict, Any, List

# Import will fail until implementation exists - expected for TDD
try:
    from EXPERIMENTAL.core.main import MainApp
    from EXPERIMENTAL.corelib.config import HeadlessConfiguration
except ImportError as e:
    pytest.skip(f"Workflow compatibility modules not implemented yet: {e}", allow_module_level=True)


class TestExistingWorkflowCompatibility:
    """Test that existing workflows continue to work without modification."""
    
    def test_legacy_csv_processing_unchanged(self):
        """Test that legacy CSV processing works exactly as before."""
        # Create temporary CSV file with legacy format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_writer = csv.writer(f)
            
            # Write header (legacy format)
            csv_writer.writerow(['po_number', 'supplier', 'url', 'amount'])
            
            # Write test data
            csv_writer.writerow(['LEGACY-001', 'Legacy Supplier A', 'https://example.com/legacy1', '1000.00'])
            csv_writer.writerow(['LEGACY-002', 'Legacy Supplier B', 'https://example.com/legacy2', '2000.00'])
            csv_writer.writerow(['LEGACY-003', 'Legacy Supplier C', 'https://example.com/legacy3', '1500.00'])
            
            csv_file = f.name
        
        try:
            # Process with legacy method (should work unchanged)
            config = HeadlessConfiguration(headless=True)
            app = MainApp(headless_config=config)
            
            # Legacy processing should work without parallel parameters
            success_count, failed_count = app.process_csv_file(
                csv_file,
                hierarchy_cols=[],
                has_hierarchy_data=False
            )
            
            # Validate legacy behavior
            assert success_count >= 0, "Legacy processing should return success count"
            assert failed_count >= 0, "Legacy processing should return failed count"
            assert success_count + failed_count == 3, "All 3 POs should be processed"
            
            print(f"Legacy CSV processing: {success_count} success, {failed_count} failed")
            
        finally:
            # Cleanup
            os.unlink(csv_file)
    
    def test_excel_processing_backward_compatibility(self):
        """Test that Excel processing maintains backward compatibility."""
        # Create temporary Excel file would go here
        # For now, test the interface compatibility
        
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        # Test that Excel processing interface is preserved
        # This would fail until implementation provides backward compatibility
        assert hasattr(app, 'process_excel_file'), "Excel processing method should exist"
        
        # Test method signature compatibility
        import inspect
        excel_method = getattr(app, 'process_excel_file')
        sig = inspect.signature(excel_method)
        
        # Check that legacy parameters are still supported
        expected_params = ['excel_file', 'hierarchy_cols', 'has_hierarchy_data']
        for param in expected_params:
            assert param in sig.parameters, f"Legacy parameter '{param}' should be supported"
        
        print("Excel processing interface backward compatibility verified")
    
    def test_single_po_processing_unchanged(self):
        """Test that single PO processing works unchanged."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        # Single PO data (legacy format)
        po_data = {
            'po_number': 'SINGLE-001',
            'supplier': 'Single Supplier',
            'url': 'https://example.com/single',
            'amount': 1000.00
        }
        
        # Process single PO (legacy method)
        success_count, failed_count = app._process_po_entries(
            [po_data],
            hierarchy_cols=[],
            has_hierarchy_data=False,
            use_process_pool=False,  # Legacy single-threaded
            headless_config=config
        )
        
        # Validate single PO processing
        assert success_count + failed_count == 1, "Single PO should be processed"
        assert success_count >= 0, "Success count should be valid"
        assert failed_count >= 0, "Failed count should be valid"
        
        print(f"Single PO processing: {success_count} success, {failed_count} failed")
    
    def test_hierarchy_processing_compatibility(self):
        """Test that hierarchy processing remains compatible."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        # Test data with hierarchy
        po_list = [
            {
                'po_number': 'HIER-001',
                'supplier': 'Hierarchy Supplier A',
                'url': 'https://example.com/hier1',
                'amount': 1000.00,
                'category': 'Category A',
                'department': 'Dept 1'
            },
            {
                'po_number': 'HIER-002',
                'supplier': 'Hierarchy Supplier B',
                'url': 'https://example.com/hier2',
                'amount': 2000.00,
                'category': 'Category B',
                'department': 'Dept 2'
            }
        ]
        
        hierarchy_cols = ['category', 'department']
        
        # Process with hierarchy (legacy method)
        success_count, failed_count = app._process_po_entries(
            po_list,
            hierarchy_cols=hierarchy_cols,
            has_hierarchy_data=True,
            use_process_pool=False,  # Legacy mode
            headless_config=config
        )
        
        # Validate hierarchy processing
        assert success_count + failed_count == 2, "Both hierarchy POs should be processed"
        assert success_count >= 0, "Success count should be valid"
        assert failed_count >= 0, "Failed count should be valid"
        
        print(f"Hierarchy processing: {success_count} success, {failed_count} failed")
    
    def test_configuration_backward_compatibility(self):
        """Test that configuration options remain backward compatible."""
        # Test legacy configuration creation
        config = HeadlessConfiguration(
            headless=True,
            download_timeout=30,
            page_load_timeout=60
        )
        
        # Validate configuration structure
        assert hasattr(config, 'headless'), "Headless option should exist"
        assert hasattr(config, 'download_timeout'), "Download timeout should exist"
        assert hasattr(config, 'page_load_timeout'), "Page load timeout should exist"
        
        # Test that legacy app creation works
        app = MainApp(headless_config=config)
        
        # Validate app structure
        assert hasattr(app, '_process_po_entries'), "Legacy processing method should exist"
        assert hasattr(app, 'process_csv_file'), "CSV processing should exist"
        
        print("Configuration backward compatibility verified")
    
    def test_error_handling_compatibility(self):
        """Test that error handling remains compatible with legacy code."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        # Test with invalid PO data (should handle gracefully)
        invalid_po_list = [
            {
                'po_number': 'INVALID-001',
                'supplier': '',  # Invalid: empty supplier
                'url': 'invalid-url',  # Invalid: malformed URL
                'amount': 'not-a-number'  # Invalid: non-numeric amount
            },
            {
                'po_number': '',  # Invalid: empty PO number
                'supplier': 'Valid Supplier',
                'url': 'https://example.com/valid',
                'amount': 1000.00
            }
        ]
        
        # Process invalid data (should not crash)
        try:
            success_count, failed_count = app._process_po_entries(
                invalid_po_list,
                hierarchy_cols=[],
                has_hierarchy_data=False,
                use_process_pool=False,
                headless_config=config
            )
            
            # Validate error handling
            assert success_count >= 0, "Success count should be non-negative"
            assert failed_count >= 0, "Failed count should be non-negative"
            assert success_count + failed_count == 2, "Both POs should be accounted for"
            
            print(f"Error handling: {success_count} success, {failed_count} failed")
            
        except Exception as e:
            # If exceptions are thrown, they should be legacy-compatible
            assert isinstance(e, (ValueError, TypeError, RuntimeError)), \
                   f"Exception should be legacy-compatible type, got {type(e)}"
            print(f"Legacy exception handling: {type(e).__name__}: {e}")
    
    def test_output_format_compatibility(self):
        """Test that output formats remain compatible."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        po_list = [
            {
                'po_number': 'OUTPUT-001',
                'supplier': 'Output Supplier',
                'url': 'https://example.com/output',
                'amount': 1000.00
            }
        ]
        
        # Process and check output format
        result = app._process_po_entries(
            po_list,
            hierarchy_cols=[],
            has_hierarchy_data=False,
            use_process_pool=False,
            headless_config=config
        )
        
        # Validate output format is a tuple (legacy expectation)
        assert isinstance(result, tuple), "Output should be a tuple"
        assert len(result) == 2, "Output should be (success_count, failed_count)"
        
        success_count, failed_count = result
        assert isinstance(success_count, int), "Success count should be integer"
        assert isinstance(failed_count, int), "Failed count should be integer"
        
        print(f"Output format compatibility: ({success_count}, {failed_count})")
    
    def test_legacy_logging_compatibility(self):
        """Test that logging behavior remains compatible."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        # Test that logging methods exist
        assert hasattr(app, 'logger') or hasattr(app, '_logger'), \
               "Logger should be available for compatibility"
        
        # Test basic logging functionality
        po_list = [
            {
                'po_number': 'LOG-001',
                'supplier': 'Logging Supplier',
                'url': 'https://example.com/log',
                'amount': 1000.00
            }
        ]
        
        # Process with logging (should not crash)
        success_count, failed_count = app._process_po_entries(
            po_list,
            hierarchy_cols=[],
            has_hierarchy_data=False,
            use_process_pool=False,
            headless_config=config
        )
        
        # Validate processing completed
        assert success_count + failed_count == 1, "PO should be processed"
        
        print("Legacy logging compatibility verified")


class TestAPIStabilityGuarantees:
    """Test that public API remains stable for existing integrations."""
    
    def test_mainapp_public_interface_stability(self):
        """Test that MainApp public interface is stable."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        # Check that public methods exist
        public_methods = [
            'process_csv_file',
            'process_excel_file',
            '_process_po_entries'
        ]
        
        for method_name in public_methods:
            assert hasattr(app, method_name), f"Public method '{method_name}' should exist"
            
            # Check that method is callable
            method = getattr(app, method_name)
            assert callable(method), f"'{method_name}' should be callable"
        
        print("MainApp public interface stability verified")
    
    def test_configuration_interface_stability(self):
        """Test that configuration interface is stable."""
        # Test that HeadlessConfiguration can be created with legacy parameters
        config = HeadlessConfiguration(
            headless=True,
            download_timeout=30,
            page_load_timeout=60
        )
        
        # Check that expected attributes exist
        expected_attrs = ['headless', 'download_timeout', 'page_load_timeout']
        for attr in expected_attrs:
            assert hasattr(config, attr), f"Configuration attribute '{attr}' should exist"
        
        # Test that values are preserved
        assert config.headless == True
        assert config.download_timeout == 30
        assert config.page_load_timeout == 60
        
        print("Configuration interface stability verified")
    
    def test_return_value_format_stability(self):
        """Test that return value formats are stable."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        po_list = [
            {
                'po_number': 'API-001',
                'supplier': 'API Supplier',
                'url': 'https://example.com/api',
                'amount': 1000.00
            }
        ]
        
        # Test _process_po_entries return format
        result = app._process_po_entries(
            po_list,
            hierarchy_cols=[],
            has_hierarchy_data=False,
            use_process_pool=False,
            headless_config=config
        )
        
        # Validate stable return format
        assert isinstance(result, tuple), "Should return tuple"
        assert len(result) == 2, "Should return (success_count, failed_count)"
        
        success_count, failed_count = result
        assert isinstance(success_count, int), "Success count should be int"
        assert isinstance(failed_count, int), "Failed count should be int"
        
        print("Return value format stability verified")
    
    def test_exception_handling_stability(self):
        """Test that exception handling behavior is stable."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        # Test with various error conditions
        test_cases = [
            # Empty PO list
            ([], [], False, False),
            
            # Missing required fields
            ([{'po_number': 'INCOMPLETE'}], [], False, False),
            
            # Invalid hierarchy configuration
            ([{'po_number': 'HIER', 'supplier': 'Test'}], ['nonexistent'], True, False)
        ]
        
        for po_list, hierarchy_cols, has_hierarchy, use_pool in test_cases:
            try:
                result = app._process_po_entries(
                    po_list,
                    hierarchy_cols=hierarchy_cols,
                    has_hierarchy_data=has_hierarchy,
                    use_process_pool=use_pool,
                    headless_config=config
                )
                
                # If no exception, validate result format
                assert isinstance(result, tuple), "Result should be tuple even with errors"
                assert len(result) == 2, "Result should have 2 elements"
                
            except Exception as e:
                # If exception occurs, should be expected type
                expected_types = (ValueError, TypeError, RuntimeError, AttributeError)
                assert isinstance(e, expected_types), \
                       f"Exception should be expected type, got {type(e)}"
        
        print("Exception handling stability verified")


class TestIntegrationPointCompatibility:
    """Test that integration points remain compatible."""
    
    def test_cli_integration_compatibility(self):
        """Test that CLI integration points remain compatible."""
        # Test that MainApp can be instantiated for CLI usage
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        # Check that CLI-expected methods exist
        cli_methods = ['process_csv_file', 'process_excel_file']
        for method in cli_methods:
            assert hasattr(app, method), f"CLI method '{method}' should exist"
        
        print("CLI integration compatibility verified")
    
    def test_script_integration_compatibility(self):
        """Test that script integration points remain compatible."""
        # Test that MainApp can be used in scripts as before
        config = HeadlessConfiguration(headless=True)
        app = MainApp(headless_config=config)
        
        # Test minimal script usage pattern
        po_data = [
            {
                'po_number': 'SCRIPT-001',
                'supplier': 'Script Supplier',
                'url': 'https://example.com/script',
                'amount': 1000.00
            }
        ]
        
        # This should work without modification in existing scripts
        success, failed = app._process_po_entries(
            po_data,
            hierarchy_cols=[],
            has_hierarchy_data=False,
            use_process_pool=False,
            headless_config=config
        )
        
        assert isinstance(success, int)
        assert isinstance(failed, int)
        assert success + failed == 1
        
        print("Script integration compatibility verified")
    
    def test_library_integration_compatibility(self):
        """Test that library integration points remain compatible."""
        # Test that MainApp can be imported and used as a library
        from EXPERIMENTAL.core.main import MainApp
        from EXPERIMENTAL.corelib.config import HeadlessConfiguration
        
        # Test library usage pattern
        config = HeadlessConfiguration(headless=True)
        processor = MainApp(headless_config=config)
        
        # Validate that library interface is preserved
        assert hasattr(processor, '_process_po_entries')
        assert callable(processor._process_po_entries)
        
        print("Library integration compatibility verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])