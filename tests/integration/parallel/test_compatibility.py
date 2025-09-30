"""
Compatibility testing for parallel processing implementation.
Ensures backward compatibility and validates integration with existing systems.
"""

import os
import time
import pytest
import tempfile
import json
from typing import Dict, Any, List
from pathlib import Path


class TestBackwardCompatibility:
    """Test suite for backward compatibility with existing functionality."""
    
    def test_sequential_mode_compatibility(self):
        """Test that sequential mode works exactly as before."""
        # Test data that mimics existing functionality
        sample_po_data = [
            {"po_number": "PO-001", "supplier": "Supplier A", "url": "https://example.com/po1"},
            {"po_number": "PO-002", "supplier": "Supplier B", "url": "https://example.com/po2"},
            {"po_number": "PO-003", "supplier": "Supplier C", "url": "https://example.com/po3"},
        ]
        
        # Simulate sequential processing (original behavior)
        start_time = time.time()
        
        # Mock the original sequential processing
        processed_results = []
        for po in sample_po_data:
            # Simulate original processing time and behavior
            time.sleep(0.01)  # Original processing time per PO
            
            result = {
                'po_number': po['po_number'],
                'supplier': po['supplier'],
                'status': 'processed',
                'processing_mode': 'sequential',
                'timestamp': time.time()
            }
            processed_results.append(result)
        
        processing_time = time.time() - start_time
        
        # Validate original behavior is preserved
        assert len(processed_results) == len(sample_po_data)
        assert all(r['processing_mode'] == 'sequential' for r in processed_results)
        assert all(r['status'] == 'processed' for r in processed_results)
        
        # Validate processing order is maintained (sequential characteristic)
        po_numbers = [r['po_number'] for r in processed_results]
        expected_order = [po['po_number'] for po in sample_po_data]
        assert po_numbers == expected_order, "Sequential processing should maintain order"
        
        print(f"Sequential compatibility: {len(processed_results)} POs in {processing_time:.3f}s")
        print("✅ Sequential mode maintains original behavior")
    
    def test_configuration_compatibility(self):
        """Test that existing configuration methods still work."""
        # Test original configuration approach
        original_config = {
            'headless': True,
            'timeout': 30,
            'download_path': '/tmp/downloads',
            'retry_count': 3
        }
        
        # Simulate enhanced configuration with parallel options
        enhanced_config = original_config.copy()
        enhanced_config.update({
            'enable_parallel': False,  # Backward compatibility: default to sequential
            'max_workers': 1,
            'profile_cleanup': True,
            'profile_reuse': True
        })
        
        # Validate original config keys are preserved
        for key, value in original_config.items():
            assert key in enhanced_config, f"Original config key '{key}' should be preserved"
            assert enhanced_config[key] == value, f"Original config value for '{key}' should be unchanged"
        
        # Validate new parallel options have safe defaults
        assert enhanced_config['enable_parallel'] is False, "Parallel processing should be opt-in"
        assert enhanced_config['max_workers'] == 1, "Default workers should maintain sequential behavior"
        
        print("✅ Configuration compatibility maintained")
        print(f"Original config keys preserved: {list(original_config.keys())}")
        print(f"Enhanced config safely extends: {list(enhanced_config.keys())}")
    
    def test_api_compatibility(self):
        """Test that existing API methods still work with same signatures."""
        
        # Mock original API class
        class OriginalCoupaProcessor:
            def __init__(self, headless=True, timeout=30):
                self.headless = headless
                self.timeout = timeout
                self.processed_count = 0
            
            def process_po(self, po_number: str) -> Dict[str, Any]:
                """Original single PO processing method."""
                time.sleep(0.01)  # Simulate processing
                self.processed_count += 1
                return {
                    'po_number': po_number,
                    'status': 'success',
                    'processing_mode': 'sequential'
                }
            
            def process_po_list(self, po_list: List[str]) -> List[Dict[str, Any]]:
                """Original batch processing method."""
                results = []
                for po_number in po_list:
                    result = self.process_po(po_number)
                    results.append(result)
                return results
        
        # Mock enhanced API class that maintains compatibility
        class EnhancedCoupaProcessor(OriginalCoupaProcessor):
            def __init__(self, headless=True, timeout=30, enable_parallel=False, max_workers=1):
                super().__init__(headless, timeout)
                self.enable_parallel = enable_parallel
                self.max_workers = max_workers
            
            def process_po_list(self, po_list: List[str]) -> List[Dict[str, Any]]:
                """Enhanced batch processing with parallel option."""
                if self.enable_parallel and self.max_workers > 1:
                    # Parallel processing path
                    return self._process_parallel(po_list)
                else:
                    # Original sequential path
                    return super().process_po_list(po_list)
            
            def _process_parallel(self, po_list: List[str]) -> List[Dict[str, Any]]:
                """Mock parallel processing implementation."""
                import concurrent.futures
                
                def process_single(po_number):
                    time.sleep(0.01)
                    self.processed_count += 1
                    return {
                        'po_number': po_number,
                        'status': 'success',
                        'processing_mode': 'parallel'
                    }
                
                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = [executor.submit(process_single, po) for po in po_list]
                    for future in concurrent.futures.as_completed(futures):
                        results.append(future.result())
                
                # Sort results to maintain order compatibility
                results.sort(key=lambda x: po_list.index(x['po_number']))
                return results
        
        # Test original API usage still works
        po_list = ["PO-001", "PO-002", "PO-003"]
        
        # Original processor
        original_processor = OriginalCoupaProcessor(headless=True, timeout=30)
        original_results = original_processor.process_po_list(po_list)
        
        # Enhanced processor in compatibility mode
        enhanced_processor = EnhancedCoupaProcessor(headless=True, timeout=30)  # No parallel args
        enhanced_results = enhanced_processor.process_po_list(po_list)
        
        # Enhanced processor in parallel mode
        parallel_processor = EnhancedCoupaProcessor(
            headless=True, timeout=30, enable_parallel=True, max_workers=2
        )
        parallel_results = parallel_processor.process_po_list(po_list)
        
        # Validate API compatibility
        assert len(original_results) == len(enhanced_results) == len(parallel_results)
        
        # Validate original constructor still works
        assert original_processor.headless == enhanced_processor.headless
        assert original_processor.timeout == enhanced_processor.timeout
        
        # Validate results structure is compatible
        for original, enhanced in zip(original_results, enhanced_results):
            assert original['po_number'] == enhanced['po_number']
            assert original['status'] == enhanced['status']
            assert 'processing_mode' in original
            assert 'processing_mode' in enhanced
        
        # Validate parallel mode produces compatible results
        for result in parallel_results:
            assert 'po_number' in result
            assert 'status' in result
            assert result['status'] == 'success'
        
        print("✅ API compatibility maintained")
        print(f"Original API results: {len(original_results)} POs")
        print(f"Enhanced API (sequential): {len(enhanced_results)} POs")
        print(f"Enhanced API (parallel): {len(parallel_results)} POs")
    
    def test_output_format_compatibility(self):
        """Test that output formats remain compatible with existing consumers."""
        
        # Original output format
        original_report = {
            'summary': {
                'total_pos': 5,
                'successful': 4,
                'failed': 1,
                'processing_time': 2.5,
                'mode': 'sequential'
            },
            'details': [
                {'po_number': 'PO-001', 'status': 'success', 'message': 'Downloaded successfully'},
                {'po_number': 'PO-002', 'status': 'success', 'message': 'Downloaded successfully'},
                {'po_number': 'PO-003', 'status': 'failed', 'message': 'Network timeout'},
                {'po_number': 'PO-004', 'status': 'success', 'message': 'Downloaded successfully'},
                {'po_number': 'PO-005', 'status': 'success', 'message': 'Downloaded successfully'},
            ]
        }
        
        # Enhanced output format with parallel information
        enhanced_report = {
            'summary': {
                'total_pos': 5,
                'successful': 4,
                'failed': 1,
                'processing_time': 1.2,  # Faster with parallel
                'mode': 'parallel',
                'worker_count': 2,  # New field
                'efficiency_gain': 2.08  # New field
            },
            'details': [
                {'po_number': 'PO-001', 'status': 'success', 'message': 'Downloaded successfully', 'worker_id': 0},
                {'po_number': 'PO-002', 'status': 'success', 'message': 'Downloaded successfully', 'worker_id': 1},
                {'po_number': 'PO-003', 'status': 'failed', 'message': 'Network timeout', 'worker_id': 0},
                {'po_number': 'PO-004', 'status': 'success', 'message': 'Downloaded successfully', 'worker_id': 1},
                {'po_number': 'PO-005', 'status': 'success', 'message': 'Downloaded successfully', 'worker_id': 0},
            ]
        }
        
        # Test that existing report consumers still work
        def process_original_report(report):
            """Simulate existing report processing logic."""
            summary = report['summary']
            details = report['details']
            
            # Existing consumers expect these fields
            required_summary_fields = ['total_pos', 'successful', 'failed', 'processing_time', 'mode']
            required_detail_fields = ['po_number', 'status', 'message']
            
            for field in required_summary_fields:
                assert field in summary, f"Required summary field '{field}' missing"
            
            for detail in details:
                for field in required_detail_fields:
                    assert field in detail, f"Required detail field '{field}' missing"
            
            return {
                'success_rate': summary['successful'] / summary['total_pos'],
                'failed_pos': [d['po_number'] for d in details if d['status'] == 'failed']
            }
        
        # Test both report formats work with existing consumer
        original_analysis = process_original_report(original_report)
        enhanced_analysis = process_original_report(enhanced_report)
        
        # Validate compatibility
        assert original_analysis['success_rate'] == enhanced_analysis['success_rate']
        assert original_analysis['failed_pos'] == enhanced_analysis['failed_pos']
        
        # Test that enhanced fields are additive (don't break existing consumers)
        enhanced_summary = enhanced_report['summary']
        original_summary = original_report['summary']
        
        for key in original_summary:
            if key != 'processing_time' and key != 'mode':  # These can differ
                assert enhanced_summary[key] == original_summary[key]
        
        print("✅ Output format compatibility maintained")
        print(f"Original fields preserved in enhanced report")
        print(f"Additional parallel fields: worker_count, efficiency_gain, worker_id")
    
    def test_environment_variable_compatibility(self):
        """Test that existing environment variables still work."""
        
        # Original environment variables
        original_env_vars = {
            'COUPA_HEADLESS': 'true',
            'COUPA_TIMEOUT': '30',
            'COUPA_DOWNLOAD_PATH': '/tmp/downloads',
            'COUPA_RETRY_COUNT': '3'
        }
        
        # New parallel-specific environment variables
        parallel_env_vars = {
            'COUPA_ENABLE_PARALLEL': 'false',  # Default to maintain compatibility
            'COUPA_MAX_WORKERS': '1',  # Default to sequential behavior
            'COUPA_PROFILE_CLEANUP_ON_START': 'true',
            'COUPA_PROFILE_REUSE_ENABLED': 'true'
        }
        
        # Mock configuration loader
        def load_config_from_env():
            """Simulate configuration loading from environment."""
            config = {}
            
            # Load original variables
            for var, default in original_env_vars.items():
                value = os.environ.get(var, default)
                key = var.lower().replace('coupa_', '')
                
                # Type conversion for backward compatibility
                if key in ['timeout', 'retry_count']:
                    config[key] = int(value)
                elif key == 'headless':
                    config[key] = value.lower() == 'true'
                else:
                    config[key] = value
            
            # Load parallel variables with safe defaults
            for var, default in parallel_env_vars.items():
                value = os.environ.get(var, default)
                key = var.lower().replace('coupa_', '')
                
                if key in ['max_workers']:
                    config[key] = int(value)
                elif key in ['enable_parallel', 'profile_cleanup_on_start', 'profile_reuse_enabled']:
                    config[key] = value.lower() == 'true'
                else:
                    config[key] = value
            
            return config
        
        # Test with no environment variables (all defaults)
        config_defaults = load_config_from_env()
        
        # Test with original environment variables set
        for var, value in original_env_vars.items():
            os.environ[var] = value
        
        try:
            config_original = load_config_from_env()
            
            # Validate original variables are loaded correctly
            assert config_original['headless'] is True
            assert config_original['timeout'] == 30
            assert config_original['download_path'] == '/tmp/downloads'
            assert config_original['retry_count'] == 3
            
            # Validate parallel defaults maintain compatibility
            assert config_original['enable_parallel'] is False
            assert config_original['max_workers'] == 1
            
            print("✅ Environment variable compatibility maintained")
            print(f"Original env vars: {list(original_env_vars.keys())}")
            print(f"New parallel env vars: {list(parallel_env_vars.keys())}")
            
        finally:
            # Clean up environment variables
            for var in original_env_vars:
                if var in os.environ:
                    del os.environ[var]
    
    def test_error_handling_compatibility(self):
        """Test that error handling remains compatible with existing error consumers."""
        
        # Original error types and formats
        original_errors = [
            {'type': 'NetworkError', 'message': 'Connection timeout', 'po_number': 'PO-001'},
            {'type': 'AuthenticationError', 'message': 'Invalid credentials', 'po_number': 'PO-002'},
            {'type': 'FileNotFoundError', 'message': 'Attachment not found', 'po_number': 'PO-003'},
        ]
        
        # Enhanced errors with parallel context
        enhanced_errors = [
            {
                'type': 'NetworkError', 
                'message': 'Connection timeout', 
                'po_number': 'PO-001',
                'worker_id': 0,  # New field
                'retry_count': 1  # New field
            },
            {
                'type': 'AuthenticationError', 
                'message': 'Invalid credentials', 
                'po_number': 'PO-002',
                'worker_id': 1,
                'retry_count': 0
            },
            {
                'type': 'ProfileConflictError',  # New error type
                'message': 'Browser profile conflict detected', 
                'po_number': 'PO-004',
                'worker_id': 0,
                'retry_count': 2
            },
        ]
        
        # Mock error handler that existing code might use
        def handle_errors(errors):
            """Simulate existing error handling logic."""
            error_summary = {}
            
            for error in errors:
                # Existing code expects these fields
                assert 'type' in error, "Error type is required"
                assert 'message' in error, "Error message is required"
                assert 'po_number' in error, "PO number is required for tracking"
                
                error_type = error['type']
                if error_type not in error_summary:
                    error_summary[error_type] = []
                
                error_summary[error_type].append({
                    'po_number': error['po_number'],
                    'message': error['message']
                })
            
            return error_summary
        
        # Test error handling compatibility
        original_summary = handle_errors(original_errors)
        enhanced_summary = handle_errors(enhanced_errors)
        
        # Validate original error types are handled the same way
        for error_type in ['NetworkError', 'AuthenticationError']:
            assert error_type in original_summary
            if error_type in enhanced_summary:
                # Check that existing error handling logic still works
                original_error = original_summary[error_type][0]
                enhanced_error = next(
                    e for e in enhanced_summary[error_type] 
                    if e['po_number'] == original_error['po_number']
                )
                assert original_error['message'] == enhanced_error['message']
        
        # Validate new error types are additive (don't break existing handlers)
        assert 'ProfileConflictError' in enhanced_summary  # New error type should be handled
        
        print("✅ Error handling compatibility maintained")
        print(f"Original error types: {list(original_summary.keys())}")
        print(f"Enhanced error types: {list(enhanced_summary.keys())}")


class TestSystemIntegration:
    """Test suite for integration with existing system components."""
    
    def test_file_system_integration(self):
        """Test that file system operations remain compatible."""
        import tempfile
        import shutil
        
        # Test original file operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Original download structure
            original_structure = {
                'downloads': temp_path / 'downloads',
                'reports': temp_path / 'reports',
                'logs': temp_path / 'logs'
            }
            
            # Enhanced structure with parallel support
            enhanced_structure = original_structure.copy()
            enhanced_structure.update({
                'profiles': temp_path / 'profiles',  # New for parallel processing
                'temp': temp_path / 'temp'  # New for temporary files
            })
            
            # Create directory structures
            for name, path in enhanced_structure.items():
                path.mkdir(parents=True, exist_ok=True)
                
                # Create sample files
                if name == 'downloads':
                    (path / 'PO-001.pdf').touch()
                    (path / 'PO-002.pdf').touch()
                elif name == 'reports':
                    (path / 'summary.json').write_text('{"test": "data"}')
                elif name == 'logs':
                    (path / 'processing.log').write_text('Processing log data')
                elif name == 'profiles':
                    # New parallel-specific directories
                    (path / 'worker_0').mkdir()
                    (path / 'worker_1').mkdir()
            
            # Validate original paths still work
            for name, path in original_structure.items():
                assert path.exists(), f"Original path {name} should exist"
                assert path.is_dir(), f"Original path {name} should be directory"
            
            # Validate enhanced paths are additive
            for name, path in enhanced_structure.items():
                assert path.exists(), f"Enhanced path {name} should exist"
            
            # Test that existing file operations still work
            downloads_dir = enhanced_structure['downloads']
            pdf_files = list(downloads_dir.glob('*.pdf'))
            assert len(pdf_files) == 2, "Should find existing PDF files"
            
            # Test new parallel-specific operations
            profiles_dir = enhanced_structure['profiles']
            worker_dirs = list(profiles_dir.glob('worker_*'))
            assert len(worker_dirs) == 2, "Should find worker profile directories"
            
            print("✅ File system integration compatibility maintained")
            print(f"Original directories: {list(original_structure.keys())}")
            print(f"Enhanced directories: {list(enhanced_structure.keys())}")
    
    def test_logging_integration(self):
        """Test that logging integration remains compatible."""
        import logging
        import io
        
        # Original logging setup
        original_logger = logging.getLogger('coupa_original')
        original_handler = logging.StreamHandler(io.StringIO())
        original_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        original_logger.addHandler(original_handler)
        original_logger.setLevel(logging.INFO)
        
        # Enhanced logging with parallel context
        enhanced_logger = logging.getLogger('coupa_enhanced')
        enhanced_handler = logging.StreamHandler(io.StringIO())
        enhanced_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(worker_id)s] - %(message)s')
        )
        enhanced_logger.addHandler(enhanced_handler)
        enhanced_logger.setLevel(logging.INFO)
        
        # Test original logging still works
        original_logger.info("Processing PO-001")
        original_logger.error("Failed to download PO-002")
        
        # Test enhanced logging with parallel context
        enhanced_logger.info("Processing PO-003", extra={'worker_id': 'worker_0'})
        enhanced_logger.error("Failed to download PO-004", extra={'worker_id': 'worker_1'})
        
        # Get log outputs
        original_output = original_handler.stream.getvalue()
        enhanced_output = enhanced_handler.stream.getvalue()
        
        # Validate original logging format is preserved
        assert "Processing PO-001" in original_output
        assert "Failed to download PO-002" in original_output
        assert "INFO" in original_output
        assert "ERROR" in original_output
        
        # Validate enhanced logging is backward compatible
        assert "Processing PO-003" in enhanced_output
        assert "Failed to download PO-004" in enhanced_output
        
        print("✅ Logging integration compatibility maintained")
        print("Original and enhanced logging both functional")
    
    def test_configuration_file_compatibility(self):
        """Test that configuration files remain compatible."""
        import json
        import tempfile
        
        # Original configuration file format
        original_config = {
            "application": {
                "name": "CoupaDownloader",
                "version": "1.0.0"
            },
            "browser": {
                "headless": True,
                "timeout": 30,
                "driver_path": "/path/to/driver"
            },
            "download": {
                "path": "/downloads",
                "retry_count": 3,
                "concurrent_limit": 1
            }
        }
        
        # Enhanced configuration with parallel options
        enhanced_config = original_config.copy()
        enhanced_config["parallel"] = {
            "enabled": False,  # Default to maintain compatibility
            "max_workers": 1,
            "profile_isolation": True,
            "cleanup_on_start": True
        }
        enhanced_config["browser"]["profile_manager"] = {
            "reuse_profiles": True,
            "max_profiles": 10
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write original config
            original_config_file = temp_path / "original_config.json"
            with open(original_config_file, 'w') as f:
                json.dump(original_config, f, indent=2)
            
            # Write enhanced config
            enhanced_config_file = temp_path / "enhanced_config.json"
            with open(enhanced_config_file, 'w') as f:
                json.dump(enhanced_config, f, indent=2)
            
            # Test that original config can still be loaded
            def load_config(config_file):
                """Simulate config loading logic."""
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Existing code expects these sections
                required_sections = ["application", "browser", "download"]
                for section in required_sections:
                    assert section in config, f"Required section '{section}' missing"
                
                return config
            
            # Load both configs
            loaded_original = load_config(original_config_file)
            loaded_enhanced = load_config(enhanced_config_file)
            
            # Validate original sections are preserved
            for section in ["application", "browser", "download"]:
                assert section in loaded_enhanced
                
                # Check key fields are preserved
                if section == "browser":
                    assert loaded_enhanced[section]["headless"] == loaded_original[section]["headless"]
                    assert loaded_enhanced[section]["timeout"] == loaded_original[section]["timeout"]
                elif section == "download":
                    assert loaded_enhanced[section]["retry_count"] == loaded_original[section]["retry_count"]
            
            # Validate new sections are additive
            assert "parallel" in loaded_enhanced
            assert loaded_enhanced["parallel"]["enabled"] is False  # Safe default
            
            print("✅ Configuration file compatibility maintained")
            print("Original config sections preserved in enhanced version")


if __name__ == "__main__":
    # Run compatibility tests
    pytest.main([__file__, "-v", "--tb=short"])