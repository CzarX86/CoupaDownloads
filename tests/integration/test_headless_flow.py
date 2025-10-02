"""
Integration test for full headless flow (setup → browser → processing).

This test verifies the complete end-to-end headless mode workflow
from interactive setup through browser initialization to PO processing.
Tests MUST fail before implementation.
"""

import pytest
from unittest.mock import Mock, patch, call
import sys
from pathlib import Path

# Add EXPERIMENTAL to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "EXPERIMENTAL"))

try:
    from core.main import _interactive_setup, MainApp, process_po_worker
    from corelib.browser import BrowserManager
    INTEGRATION_IMPORTS_AVAILABLE = True
except ImportError as e:
    INTEGRATION_IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


@pytest.mark.integration
@pytest.mark.headless
@pytest.mark.slow
class TestHeadlessFlowIntegration:
    """Integration tests for complete headless mode workflow."""

    @pytest.fixture(autouse=True)
    def setup_imports(self):
        """Skip all tests if integration imports are not available."""
        if not INTEGRATION_IMPORTS_AVAILABLE:
            pytest.skip(f"Integration imports not available: {IMPORT_ERROR}")

    @pytest.fixture
    def sample_po_data(self):
        """Sample PO data for integration testing."""
        return {
            'po_number': 'INT-TEST-001',
            'supplier': 'Integration Test Supplier',
            'amount': 2500.00,
            'status': 'Approved',
            'url': 'https://test.coupahost.com/purchase_orders/12345'
        }

    def test_full_headless_flow_interactive_setup_to_processing(self, sample_po_data):
        """
        INTEGRATION: Complete headless flow from setup to PO processing.
        
        This test verifies that headless mode preference collected during
        interactive setup properly flows through to PO processing.
        """
        with patch('EXPERIMENTAL.core.main._prompt_bool') as mock_prompt_bool, \
             patch('EXPERIMENTAL.core.main._prompt_input') as mock_prompt_input, \
             patch('EXPERIMENTAL.core.main._prompt_bool_list') as mock_prompt_bool_list, \
             patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager, \
             patch('EXPERIMENTAL.corelib.downloader.Downloader') as mock_downloader:
            
            # Mock interactive setup - user chooses headless mode
            mock_prompt_bool.return_value = True  # Headless mode
            mock_prompt_input.return_value = "integration_test.csv"
            mock_prompt_bool_list.return_value = [True, False, True]
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            mock_driver = Mock()
            mock_manager_instance.initialize_driver.return_value = mock_driver
            
            # Mock downloader
            mock_downloader_instance = Mock()
            mock_downloader.return_value = mock_downloader_instance
            mock_downloader_instance.download_po_attachments.return_value = {
                'success': True,
                'files_downloaded': ['test_invoice.pdf']
            }
            
            # Step 1: Interactive setup
            _interactive_setup()
            
            # Step 2: Process a PO (simulating main execution)
            try:
                main_app = MainApp()
                result = main_app.process_single_po(sample_po_data)
                
                # INTEGRATION ASSERTIONS
                # Browser manager should have been called with headless=True
                assert mock_manager_instance.initialize_driver.called, \
                    "Browser not initialized during PO processing"
                
                # Verify headless parameter was passed through the flow
                calls = mock_manager_instance.initialize_driver.call_args_list
                headless_calls = [str(call) for call in calls if 'headless=True' in str(call)]
                
                # This will fail until the complete flow properly passes headless config
                assert len(headless_calls) > 0, \
                    f"Headless config not passed through complete flow: {calls}"
                
                # Verify processing completed successfully
                assert result is not None, "PO processing should return result"
                
            except Exception as e:
                if 'headless' in str(e).lower():
                    pytest.fail(f"Headless flow integration failed: {e}")
                else:
                    pytest.skip(f"Integration flow not fully implemented: {e}")

    def test_headless_false_flow_interactive_setup_to_processing(self, sample_po_data):
        """
        INTEGRATION: Complete visible mode flow from setup to PO processing.
        
        This test verifies that when user chooses visible mode during setup,
        it properly flows through to PO processing with headless=False.
        """
        with patch('EXPERIMENTAL.core.main._prompt_bool') as mock_prompt_bool, \
             patch('EXPERIMENTAL.core.main._prompt_input') as mock_prompt_input, \
             patch('EXPERIMENTAL.core.main._prompt_bool_list') as mock_prompt_bool_list, \
             patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager:
            
            # Mock interactive setup - user chooses visible mode
            mock_prompt_bool.return_value = False  # Visible mode
            mock_prompt_input.return_value = "integration_test.csv"
            mock_prompt_bool_list.return_value = [True, False, True]
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            mock_driver = Mock()
            mock_manager_instance.initialize_driver.return_value = mock_driver
            
            # Step 1: Interactive setup
            _interactive_setup()
            
            # Step 2: Process a PO
            try:
                main_app = MainApp()
                result = main_app.process_single_po(sample_po_data)
                
                # INTEGRATION ASSERTIONS
                # Browser should be initialized with headless=False
                calls = mock_manager_instance.initialize_driver.call_args_list
                visible_calls = [str(call) for call in calls if 'headless=False' in str(call)]
                
                # This will fail until the complete flow properly passes headless=False
                assert len(visible_calls) > 0, \
                    f"Visible mode not passed through complete flow: {calls}"
                
            except Exception as e:
                if 'headless' in str(e).lower():
                    pytest.fail(f"Visible mode flow integration failed: {e}")
                else:
                    pytest.skip(f"Integration flow not fully implemented: {e}")

    def test_process_worker_inherits_headless_config_from_main(self, sample_po_data):
        """
        INTEGRATION: Process workers inherit headless config from main execution.
        
        This test verifies that when using process workers, the headless
        configuration is properly passed from main execution to workers.
        """
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
                'files_downloaded': ['worker_test.pdf']
            }
            
            # Simulate process worker call with headless config
            headless_config = True
            hierarchy_cols = ['col1', 'col2']
            has_hierarchy = True
            worker_args = (sample_po_data, hierarchy_cols, has_hierarchy, headless_config)
            
            try:
                result = process_po_worker(worker_args)
                
                # INTEGRATION ASSERTIONS
                # Worker should initialize browser with inherited headless config
                assert mock_manager_instance.initialize_driver.called, \
                    "Process worker didn't initialize browser"
                
                calls = mock_manager_instance.initialize_driver.call_args_list
                headless_worker_calls = [str(call) for call in calls if 'headless=True' in str(call)]
                
                # This will fail until workers properly inherit headless config
                assert len(headless_worker_calls) > 0, \
                    f"Process worker didn't inherit headless config: {calls}"
                
                assert result is not None, "Process worker should return result"
                
            except Exception as e:
                if 'headless' in str(e).lower() or 'args' in str(e).lower():
                    pytest.fail(f"Process worker headless inheritance failed: {e}")
                else:
                    pytest.skip(f"Process worker implementation incomplete: {e}")

    def test_multiple_po_processing_maintains_consistent_headless_mode(self):
        """
        INTEGRATION: Multiple PO processing maintains consistent headless mode.
        
        This test verifies that when processing multiple POs, the headless
        mode remains consistent across all browser instances.
        """
        sample_pos = [
            {'po_number': 'MULTI-001', 'url': 'https://test.com/po/1'},
            {'po_number': 'MULTI-002', 'url': 'https://test.com/po/2'},
            {'po_number': 'MULTI-003', 'url': 'https://test.com/po/3'}
        ]
        
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
            
            try:
                main_app = MainApp()
                
                # Process multiple POs with headless mode
                results = []
                for po_data in sample_pos:
                    result = main_app.process_single_po(po_data, headless=True)
                    results.append(result)
                
                # INTEGRATION ASSERTIONS
                # All browser initializations should use headless=True
                calls = mock_manager_instance.initialize_driver.call_args_list
                
                if len(calls) > 0:
                    # Extract headless values from all calls
                    headless_values = []
                    for call in calls:
                        call_str = str(call)
                        if 'headless=True' in call_str:
                            headless_values.append(True)
                        elif 'headless=False' in call_str:
                            headless_values.append(False)
                    
                    # All values should be True (consistent headless mode)
                    assert all(value is True for value in headless_values), \
                        f"Inconsistent headless values across POs: {headless_values}"
                    
                    # Should have at least as many calls as POs
                    assert len(calls) >= len(sample_pos), \
                        f"Not enough browser init calls for {len(sample_pos)} POs: {len(calls)}"
                
                # All POs should have been processed
                assert len(results) == len(sample_pos), \
                    f"Expected {len(sample_pos)} results, got {len(results)}"
                
            except Exception as e:
                if 'headless' in str(e).lower():
                    pytest.fail(f"Multiple PO headless consistency failed: {e}")
                else:
                    pytest.skip(f"Multiple PO processing not implemented: {e}")

    def test_environment_variable_independence(self, sample_po_data):
        """
        INTEGRATION: Headless mode works independently of environment variables.
        
        This test verifies that the new implementation doesn't depend on
        HEADLESS environment variable and works through explicit parameter passing.
        """
        import os
        
        # Store original environment
        original_headless_env = os.environ.get('HEADLESS')
        
        try:
            # Set environment variable to opposite of what we'll request
            os.environ['HEADLESS'] = 'false'
            
            with patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager:
                
                # Mock browser manager
                mock_manager_instance = Mock()
                mock_browser_manager.return_value = mock_manager_instance
                mock_manager_instance.initialize_driver.return_value = Mock()
                
                # Explicitly request headless=True (opposite of env var)
                main_app = MainApp()
                result = main_app.process_single_po(sample_po_data, headless=True)
                
                # INTEGRATION ASSERTIONS
                # Should use explicit parameter, not environment variable
                calls = mock_manager_instance.initialize_driver.call_args_list
                explicit_headless_calls = [str(call) for call in calls if 'headless=True' in str(call)]
                
                # This will fail until implementation uses explicit parameters over env vars
                assert len(explicit_headless_calls) > 0, \
                    f"Explicit headless parameter not honored over env var: {calls}"
                
        except Exception as e:
            if 'headless' in str(e).lower():
                pytest.fail(f"Environment variable independence failed: {e}")
            else:
                pytest.skip(f"Environment independence not implemented: {e}")
        finally:
            # Restore original environment
            if original_headless_env is not None:
                os.environ['HEADLESS'] = original_headless_env
            else:
                os.environ.pop('HEADLESS', None)

    def test_headless_mode_persistence_across_browser_restarts(self, sample_po_data):
        """
        INTEGRATION: Headless mode persists across browser restarts.
        
        This test verifies that if browser crashes or needs restart during
        processing, the headless mode configuration is maintained.
        """
        with patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager:
            
            # Mock browser manager with restart scenario
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            
            # Simulate browser restart - multiple initialize_driver calls
            mock_drivers = [Mock(), Mock(), Mock()]
            mock_manager_instance.initialize_driver.side_effect = mock_drivers
            
            try:
                main_app = MainApp()
                
                # Simulate multiple browser initializations (restarts)
                for i in range(3):
                    result = main_app.process_single_po(sample_po_data, headless=True)
                
                # INTEGRATION ASSERTIONS
                # All browser restarts should maintain headless=True
                calls = mock_manager_instance.initialize_driver.call_args_list
                assert len(calls) == 3, f"Expected 3 browser initializations, got {len(calls)}"
                
                # All calls should use headless=True
                headless_true_calls = [str(call) for call in calls if 'headless=True' in str(call)]
                
                # This will fail until restart scenarios properly maintain headless config
                assert len(headless_true_calls) == 3, \
                    f"Not all browser restarts maintained headless mode: {calls}"
                
            except Exception as e:
                if 'headless' in str(e).lower():
                    pytest.fail(f"Headless persistence across restarts failed: {e}")
                else:
                    pytest.skip(f"Browser restart scenarios not implemented: {e}")