"""
Contract tests for InteractiveSetup._interactive_setup() headless collection.

These tests verify that the interactive setup properly collects headless
preference from user and passes it through the system. Tests MUST fail before implementation.
"""

import pytest
from unittest.mock import Mock, patch, call
import sys
from pathlib import Path

# Add EXPERIMENTAL to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "EXPERIMENTAL"))

try:
    from core.main import _interactive_setup, _prompt_bool
    MAIN_IMPORTS_AVAILABLE = True
except ImportError as e:
    MAIN_IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


@pytest.mark.contract
@pytest.mark.headless
class TestInteractiveSetupContract:
    """Contract tests for interactive setup headless functionality."""

    @pytest.fixture(autouse=True)
    def setup_imports(self):
        """Skip all tests if main imports are not available."""
        if not MAIN_IMPORTS_AVAILABLE:
            pytest.skip(f"Main imports not available: {IMPORT_ERROR}")

    def test_interactive_setup_collects_headless_preference(self):
        """
        CONTRACT: _interactive_setup() MUST prompt user for headless mode preference.
        
        This test verifies that the interactive setup function prompts
        the user for their headless mode preference using the correct prompt.
        """
        with patch('EXPERIMENTAL.core.main._prompt_bool') as mock_prompt_bool, \
             patch('EXPERIMENTAL.core.main._prompt_input') as mock_prompt_input, \
             patch('EXPERIMENTAL.core.main._prompt_bool_list') as mock_prompt_bool_list:
            
            # Mock user responses
            mock_prompt_bool.return_value = True  # User chooses headless mode
            mock_prompt_input.return_value = "test_input.csv"
            mock_prompt_bool_list.return_value = [True, False, True]  # Mock other prompts
            
            # Call method under test
            _interactive_setup()
            
            # CONTRACT ASSERTIONS
            # MUST prompt for headless mode
            headless_calls = [call for call in mock_prompt_bool.call_args_list 
                            if 'headless' in str(call).lower()]
            assert len(headless_calls) > 0, "No headless mode prompt found"
            
            # Verify the prompt text is appropriate
            headless_call = headless_calls[0]
            prompt_text = str(headless_call)
            assert 'headless' in prompt_text.lower(), f"Headless prompt not found: {prompt_text}"

    def test_interactive_setup_passes_headless_to_browser_init(self):
        """
        CONTRACT: _interactive_setup() MUST pass headless configuration to browser initialization.
        
        This test verifies that the headless preference collected from the user
        is properly passed to the browser initialization process.
        """
        with patch('EXPERIMENTAL.core.main._prompt_bool') as mock_prompt_bool, \
             patch('EXPERIMENTAL.core.main._prompt_input') as mock_prompt_input, \
             patch('EXPERIMENTAL.core.main._prompt_bool_list') as mock_prompt_bool_list, \
             patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager:
            
            # Mock user chooses headless mode
            mock_prompt_bool.return_value = True
            mock_prompt_input.return_value = "test_input.csv"
            mock_prompt_bool_list.return_value = [True, False, True]
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            
            # Call method under test
            _interactive_setup()
            
            # CONTRACT ASSERTIONS
            # The headless preference MUST be passed to browser initialization
            # This will fail until implementation properly passes headless parameter
            
            # Check if browser manager was instantiated with headless config
            # Or if initialize_driver was called with headless parameter
            if mock_manager_instance.initialize_driver.called:
                # Verify headless parameter was passed
                calls = mock_manager_instance.initialize_driver.call_args_list
                headless_calls = [call for call in calls if 'headless' in str(call)]
                assert len(headless_calls) > 0, "Browser not initialized with headless parameter"
            else:
                # This test will fail until browser initialization is properly integrated
                pytest.fail("Browser manager initialize_driver not called during interactive setup")

    def test_interactive_setup_no_environment_variable_modification(self):
        """
        CONTRACT: _interactive_setup() MUST NOT modify environment variables.
        
        This test verifies that the interactive setup does not set HEADLESS
        environment variable, per the new implementation requirements.
        """
        import os
        
        with patch('EXPERIMENTAL.core.main._prompt_bool') as mock_prompt_bool, \
             patch('EXPERIMENTAL.core.main._prompt_input') as mock_prompt_input, \
             patch('EXPERIMENTAL.core.main._prompt_bool_list') as mock_prompt_bool_list, \
             patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager:
            
            # Store original environment
            original_headless = os.environ.get('HEADLESS')
            
            # Mock user responses
            mock_prompt_bool.return_value = True  # User chooses headless
            mock_prompt_input.return_value = "test_input.csv"
            mock_prompt_bool_list.return_value = [True, False, True]
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            
            # Call method under test
            _interactive_setup()
            
            # CONTRACT ASSERTIONS
            # Environment variable MUST NOT be modified
            current_headless = os.environ.get('HEADLESS')
            
            # This test will fail if the current implementation still sets env vars
            assert current_headless == original_headless, \
                f"HEADLESS environment variable was modified: {original_headless} -> {current_headless}"

    def test_interactive_setup_headless_false_passes_correct_value(self):
        """
        CONTRACT: When user selects NO headless mode, MUST pass headless=False.
        
        This test verifies that when the user chooses not to use headless mode,
        the correct value (False) is passed to browser initialization.
        """
        with patch('EXPERIMENTAL.core.main._prompt_bool') as mock_prompt_bool, \
             patch('EXPERIMENTAL.core.main._prompt_input') as mock_prompt_input, \
             patch('EXPERIMENTAL.core.main._prompt_bool_list') as mock_prompt_bool_list, \
             patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager:
            
            # Mock user chooses NO headless mode
            mock_prompt_bool.return_value = False
            mock_prompt_input.return_value = "test_input.csv"
            mock_prompt_bool_list.return_value = [True, False, True]
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            
            # Call method under test
            _interactive_setup()
            
            # CONTRACT ASSERTIONS
            # Browser initialization MUST receive headless=False
            if mock_manager_instance.initialize_driver.called:
                calls = mock_manager_instance.initialize_driver.call_args_list
                
                # Look for calls with headless=False
                found_false_call = False
                for call in calls:
                    if 'headless' in str(call) and 'False' in str(call):
                        found_false_call = True
                        break
                
                # This will fail until implementation properly passes headless=False
                assert found_false_call, f"headless=False not passed to browser init: {calls}"
            else:
                pytest.fail("Browser manager initialize_driver not called")

    def test_interactive_setup_headless_preference_consistent_throughout_execution(self):
        """
        CONTRACT: Headless preference MUST remain consistent throughout execution.
        
        This test verifies that the headless preference collected during setup
        is consistently applied to all browser operations in the session.
        """
        with patch('EXPERIMENTAL.core.main._prompt_bool') as mock_prompt_bool, \
             patch('EXPERIMENTAL.core.main._prompt_input') as mock_prompt_input, \
             patch('EXPERIMENTAL.core.main._prompt_bool_list') as mock_prompt_bool_list, \
             patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock_browser_manager:
            
            # Mock user chooses headless mode
            mock_prompt_bool.return_value = True
            mock_prompt_input.return_value = "test_input.csv"
            mock_prompt_bool_list.return_value = [True, False, True]
            
            # Mock browser manager
            mock_manager_instance = Mock()
            mock_browser_manager.return_value = mock_manager_instance
            
            # Call method under test
            _interactive_setup()
            
            # CONTRACT ASSERTIONS
            # All browser initialization calls MUST use the same headless setting
            if mock_manager_instance.initialize_driver.called:
                calls = mock_manager_instance.initialize_driver.call_args_list
                
                # Extract headless parameter from all calls
                headless_values = []
                for call in calls:
                    # Parse call arguments to find headless parameter
                    call_str = str(call)
                    if 'headless=True' in call_str:
                        headless_values.append(True)
                    elif 'headless=False' in call_str:
                        headless_values.append(False)
                
                # All values should be the same (consistent)
                if headless_values:
                    first_value = headless_values[0]
                    assert all(value == first_value for value in headless_values), \
                        f"Inconsistent headless values: {headless_values}"

    def test_interactive_setup_provides_clear_headless_feedback(self):
        """
        CONTRACT: _interactive_setup() MUST provide clear feedback about headless mode status.
        
        This test verifies that the interactive setup provides clear feedback
        to the user about the headless mode configuration.
        """
        with patch('EXPERIMENTAL.core.main._prompt_bool') as mock_prompt_bool, \
             patch('EXPERIMENTAL.core.main._prompt_input') as mock_prompt_input, \
             patch('EXPERIMENTAL.core.main._prompt_bool_list') as mock_prompt_bool_list, \
             patch('builtins.print') as mock_print:
            
            # Mock user responses
            mock_prompt_bool.return_value = True  # User chooses headless
            mock_prompt_input.return_value = "test_input.csv"
            mock_prompt_bool_list.return_value = [True, False, True]
            
            # Call method under test
            _interactive_setup()
            
            # CONTRACT ASSERTIONS
            # MUST provide feedback about headless mode configuration
            print_calls = [str(call) for call in mock_print.call_args_list]
            headless_feedback = [call for call in print_calls if 'headless' in call.lower()]
            
            # This will fail until implementation provides proper feedback
            assert len(headless_feedback) > 0, \
                f"No headless mode feedback found in prints: {print_calls}"