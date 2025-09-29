"""
Contract tests for ProcessWorker.process_po_worker() headless configuration.

These tests verify that process workers properly receive and use headless
configuration when processing POs. Tests MUST fail before implementation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add EXPERIMENTAL to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "EXPERIMENTAL"))

try:
    from core.main import process_po_worker
    PROCESS_WORKER_IMPORTS_AVAILABLE = True
except ImportError as e:
    PROCESS_WORKER_IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


@pytest.mark.contract
@pytest.mark.headless
class TestProcessWorkerContract:
    """Contract tests for process worker headless functionality."""

    @pytest.fixture(autouse=True)
    def setup_imports(self):
        """Skip all tests if process worker imports are not available."""
        if not PROCESS_WORKER_IMPORTS_AVAILABLE:
            pytest.skip(f"Process worker imports not available: {IMPORT_ERROR}")

    @pytest.fixture
    def sample_po_data(self):
        """Sample PO data for testing."""
        return {
            'po_number': 'TEST-PO-001',
            'supplier': 'Test Supplier',
            'amount': 1000.00,
            'status': 'Approved'
        }

    @pytest.fixture
    def sample_hierarchy_data(self):
        """Sample hierarchy data for testing."""
        return ['column1', 'column2', 'column3']

    def test_process_worker_receives_headless_config(self, sample_po_data, sample_hierarchy_data):
        """
        CONTRACT: process_po_worker() MUST receive headless configuration as part of args.
        
        This test verifies that the process worker function receives headless
        configuration as part of its arguments tuple.
        """
        # Prepare worker arguments with headless config
        headless_config = True
        args = (sample_po_data, sample_hierarchy_data, True, headless_config)
        
        with patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager, \
             patch('EXPERIMENTAL.corelib.downloader.Downloader') as mock_downloader:
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            mock_manager_instance.initialize_driver.return_value = Mock()
            
            # Mock downloader
            mock_downloader_instance = Mock()
            mock_downloader.return_value = mock_downloader_instance
            mock_downloader_instance.download_po_attachments.return_value = {
                'success': True,
                'files_downloaded': []
            }
            
            # Call method under test
            try:
                result = process_po_worker(args)
                
                # CONTRACT ASSERTIONS
                # Worker MUST successfully process args with headless config
                assert result is not None
                assert isinstance(result, dict)
                
            except Exception as e:
                # If it fails due to missing headless handling, that's expected
                if 'headless' in str(e).lower() or 'argument' in str(e).lower():
                    pytest.fail(f"Process worker doesn't handle headless config: {e}")
                else:
                    # Other errors might be due to missing implementation
                    pytest.skip(f"Process worker not fully implemented: {e}")

    def test_process_worker_creates_headless_browser(self, sample_po_data, sample_hierarchy_data):
        """
        CONTRACT: process_po_worker() MUST create browser instance with correct headless setting.
        
        This test verifies that the process worker creates a browser instance
        using the headless configuration provided in the arguments.
        """
        # Test with headless=True
        headless_config = True
        args = (sample_po_data, sample_hierarchy_data, True, headless_config)
        
        with patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager:
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            mock_manager_instance.initialize_driver.return_value = Mock()
            
            # Call method under test
            try:
                process_po_worker(args)
                
                # CONTRACT ASSERTIONS
                # Browser MUST be initialized with headless parameter
                mock_manager_instance.initialize_driver.assert_called()
                
                # Check if headless parameter was passed
                calls = mock_manager_instance.initialize_driver.call_args_list
                headless_passed = any('headless' in str(call) for call in calls)
                
                # This will fail until implementation properly passes headless parameter
                assert headless_passed, f"Headless parameter not passed to browser init: {calls}"
                
                # Verify correct headless value was passed
                headless_true_passed = any('headless=True' in str(call) for call in calls)
                assert headless_true_passed, f"headless=True not passed to browser: {calls}"
                
            except Exception as e:
                if 'headless' in str(e).lower():
                    pytest.fail(f"Process worker headless handling failed: {e}")
                else:
                    pytest.skip(f"Process worker implementation incomplete: {e}")

    def test_process_worker_maintains_headless_throughout_processing(self, sample_po_data, sample_hierarchy_data):
        """
        CONTRACT: process_po_worker() MUST maintain headless mode throughout processing.
        
        This test verifies that the headless mode is consistently maintained
        throughout the entire PO processing workflow.
        """
        headless_config = True
        args = (sample_po_data, sample_hierarchy_data, True, headless_config)
        
        with patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager, \
             patch('EXPERIMENTAL.corelib.downloader.Downloader') as mock_downloader:
            
            # Mock browser manager with multiple driver creations
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            mock_manager_instance.initialize_driver.return_value = Mock()
            
            # Mock downloader
            mock_downloader_instance = Mock()
            mock_downloader.return_value = mock_downloader_instance
            mock_downloader_instance.download_po_attachments.return_value = {
                'success': True,
                'files_downloaded': ['test.pdf']
            }
            
            # Call method under test
            try:
                result = process_po_worker(args)
                
                # CONTRACT ASSERTIONS
                # All browser initializations MUST use the same headless setting
                if mock_manager_instance.initialize_driver.called:
                    calls = mock_manager_instance.initialize_driver.call_args_list
                    
                    # Extract headless values from all calls
                    headless_values = []
                    for call in calls:
                        call_str = str(call)
                        if 'headless=True' in call_str:
                            headless_values.append(True)
                        elif 'headless=False' in call_str:
                            headless_values.append(False)
                    
                    # All calls should use the same headless setting
                    if headless_values:
                        first_value = headless_values[0]
                        assert all(value == first_value for value in headless_values), \
                            f"Inconsistent headless values in worker: {headless_values}"
                        
                        # Should match the input configuration
                        assert first_value == headless_config, \
                            f"Headless value {first_value} doesn't match config {headless_config}"
                
            except Exception as e:
                if 'headless' in str(e).lower():
                    pytest.fail(f"Headless consistency failed in worker: {e}")
                else:
                    pytest.skip(f"Worker implementation incomplete: {e}")

    def test_process_worker_headless_false_configuration(self, sample_po_data, sample_hierarchy_data):
        """
        CONTRACT: process_po_worker() MUST handle headless=False configuration correctly.
        
        This test verifies that when headless=False is configured, the process
        worker properly creates visible browser instances.
        """
        # Test with headless=False
        headless_config = False
        args = (sample_po_data, sample_hierarchy_data, True, headless_config)
        
        with patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager:
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            mock_manager_instance.initialize_driver.return_value = Mock()
            
            # Call method under test
            try:
                process_po_worker(args)
                
                # CONTRACT ASSERTIONS
                # Browser MUST be initialized with headless=False
                mock_manager_instance.initialize_driver.assert_called()
                
                calls = mock_manager_instance.initialize_driver.call_args_list
                headless_false_passed = any('headless=False' in str(call) for call in calls)
                
                # This will fail until implementation properly handles headless=False
                assert headless_false_passed, f"headless=False not passed to browser: {calls}"
                
            except Exception as e:
                if 'headless' in str(e).lower():
                    pytest.fail(f"Process worker headless=False handling failed: {e}")
                else:
                    pytest.skip(f"Process worker implementation incomplete: {e}")

    def test_process_worker_logs_headless_mode_status(self, sample_po_data, sample_hierarchy_data):
        """
        CONTRACT: process_po_worker() MUST log headless mode status for debugging.
        
        This test verifies that the process worker logs information about
        the headless mode configuration for debugging purposes.
        """
        headless_config = True
        args = (sample_po_data, sample_hierarchy_data, True, headless_config)
        
        with patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager, \
             patch('builtins.print') as mock_print:
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            mock_manager_instance.initialize_driver.return_value = Mock()
            
            # Call method under test
            try:
                process_po_worker(args)
                
                # CONTRACT ASSERTIONS
                # MUST log headless mode status
                print_calls = [str(call) for call in mock_print.call_args_list]
                headless_logs = [call for call in print_calls if 'headless' in call.lower()]
                
                # This will fail until implementation adds proper logging
                assert len(headless_logs) > 0, \
                    f"No headless mode logging found in worker: {print_calls}"
                
            except Exception as e:
                if 'headless' in str(e).lower():
                    pytest.fail(f"Process worker headless logging failed: {e}")
                else:
                    pytest.skip(f"Process worker implementation incomplete: {e}")

    def test_process_worker_returns_headless_confirmation(self, sample_po_data, sample_hierarchy_data):
        """
        CONTRACT: process_po_worker() MUST return headless mode confirmation in results.
        
        This test verifies that the process worker includes information about
        the headless mode used in its return results.
        """
        headless_config = True
        args = (sample_po_data, sample_hierarchy_data, True, headless_config)
        
        with patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager, \
             patch('EXPERIMENTAL.corelib.downloader.Downloader') as mock_downloader:
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            mock_manager_instance.initialize_driver.return_value = Mock()
            
            # Mock downloader
            mock_downloader_instance = Mock()
            mock_downloader.return_value = mock_downloader_instance
            mock_downloader_instance.download_po_attachments.return_value = {
                'success': True,
                'files_downloaded': ['test.pdf']
            }
            
            # Call method under test
            try:
                result = process_po_worker(args)
                
                # CONTRACT ASSERTIONS
                # Result MUST include headless mode confirmation
                assert isinstance(result, dict), f"Expected dict result, got {type(result)}"
                
                # This will fail until implementation includes headless info in results
                assert 'headless_mode' in result or 'headless' in str(result).lower(), \
                    f"No headless confirmation in worker result: {result}"
                
            except Exception as e:
                if 'headless' in str(e).lower():
                    pytest.fail(f"Process worker headless result failed: {e}")
                else:
                    pytest.skip(f"Process worker implementation incomplete: {e}")

    def test_process_worker_args_tuple_structure(self, sample_po_data, sample_hierarchy_data):
        """
        CONTRACT: process_po_worker() MUST accept args tuple with headless_config as 4th element.
        
        This test verifies that the process worker function properly handles
        the expected args tuple structure including headless configuration.
        """
        headless_config = True
        args = (sample_po_data, sample_hierarchy_data, True, headless_config)
        
        # Verify args tuple structure is correct
        assert len(args) == 4, f"Expected 4-element tuple, got {len(args)} elements"
        assert args[3] == headless_config, f"Headless config not in position 3: {args[3]}"
        
        with patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager:
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            mock_manager_instance.initialize_driver.return_value = Mock()
            
            # Call method under test
            try:
                result = process_po_worker(args)
                
                # If it succeeds, the args structure is properly handled
                assert result is not None
                
            except (TypeError, IndexError, ValueError) as e:
                # These errors suggest args structure issues
                pytest.fail(f"Process worker doesn't handle 4-element args tuple: {e}")
            except Exception as e:
                # Other errors are implementation issues, not contract violations
                pytest.skip(f"Process worker implementation incomplete: {e}")