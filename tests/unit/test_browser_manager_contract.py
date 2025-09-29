"""
Contract tests for BrowserManager.initialize_driver() headless parameter.

These tests verify that the BrowserManager honors the headless parameter
in all initialization scenarios. Tests MUST fail before implementation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add EXPERIMENTAL to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "EXPERIMENTAL"))

try:
    from corelib.browser import BrowserManager
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options as EdgeOptions
    BROWSER_IMPORTS_AVAILABLE = True
except ImportError as e:
    BROWSER_IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


class HeadlessInitializationError(Exception):
    """Mock exception for headless initialization failures."""
    def __init__(self, attempt_number: int, original_error: str):
        self.attempt_number = attempt_number
        self.original_error = original_error
        super().__init__(f"Headless initialization failed on attempt {attempt_number}: {original_error}")


@pytest.mark.contract
@pytest.mark.headless
class TestBrowserManagerContract:
    """Contract tests for BrowserManager headless functionality."""

    @pytest.fixture(autouse=True)
    def setup_imports(self):
        """Skip all tests if browser imports are not available."""
        if not BROWSER_IMPORTS_AVAILABLE:
            pytest.skip(f"Browser imports not available: {IMPORT_ERROR}")

    @pytest.fixture
    def browser_manager(self):
        """Create a BrowserManager instance for testing."""
        return BrowserManager()

    def test_initialize_driver_headless_true_applies_headless_options(self, browser_manager):
        """
        CONTRACT: BrowserManager.initialize_driver(headless=True) MUST apply headless options.
        
        This test verifies that when headless=True is passed explicitly,
        the browser options include --headless=new argument.
        """
        with patch.object(browser_manager, '_create_browser_options') as mock_create_options, \
             patch('selenium.webdriver.Edge') as mock_edge:
            
            # Mock browser options
            mock_options = Mock(spec=EdgeOptions)
            mock_create_options.return_value = mock_options
            
            # Mock driver
            mock_driver = Mock(spec=webdriver.Edge)
            mock_edge.return_value = mock_driver
            
            # Call method under test
            result = browser_manager.initialize_driver(headless=True)
            
            # CONTRACT ASSERTIONS
            # MUST call _create_browser_options with headless=True
            mock_create_options.assert_called_once_with(headless=True)
            
            # MUST return a webdriver instance
            assert result == mock_driver
            
            # MUST create Edge driver with the options
            mock_edge.assert_called_once()

    def test_initialize_driver_headless_false_no_headless_options(self, browser_manager):
        """
        CONTRACT: BrowserManager.initialize_driver(headless=False) MUST NOT apply headless options.
        
        This test verifies that when headless=False is passed explicitly,
        the browser options do NOT include headless arguments.
        """
        with patch.object(browser_manager, '_create_browser_options') as mock_create_options, \
             patch('selenium.webdriver.Edge') as mock_edge:
            
            # Mock browser options
            mock_options = Mock(spec=EdgeOptions)
            mock_create_options.return_value = mock_options
            
            # Mock driver
            mock_driver = Mock(spec=webdriver.Edge)
            mock_edge.return_value = mock_driver
            
            # Call method under test
            result = browser_manager.initialize_driver(headless=False)
            
            # CONTRACT ASSERTIONS
            # MUST call _create_browser_options with headless=False
            mock_create_options.assert_called_once_with(headless=False)
            
            # MUST return a webdriver instance
            assert result == mock_driver

    def test_initialize_driver_headless_failure_retries_once(self, browser_manager):
        """
        CONTRACT: BrowserManager.initialize_driver() MUST retry once if headless mode fails.
        
        This test verifies that when headless browser initialization fails,
        the system attempts retry exactly once before further action.
        """
        with patch.object(browser_manager, '_create_browser_options') as mock_create_options, \
             patch('selenium.webdriver.Edge') as mock_edge:
            
            # Mock first call fails, second succeeds
            mock_edge.side_effect = [
                Exception("Headless initialization failed"),  # First attempt fails
                Mock(spec=webdriver.Edge)  # Retry succeeds
            ]
            
            # Mock options
            mock_options = Mock(spec=EdgeOptions)
            mock_create_options.return_value = mock_options
            
            # Call method under test
            result = browser_manager.initialize_driver(headless=True)
            
            # CONTRACT ASSERTIONS
            # MUST attempt initialization twice (original + retry)
            assert mock_edge.call_count == 2
            
            # MUST return successful driver after retry
            assert result is not None

    def test_initialize_driver_retry_failure_prompts_user(self, browser_manager):
        """
        CONTRACT: BrowserManager.initialize_driver() MUST prompt user after retry failure.
        
        This test verifies that when both initial and retry attempts fail,
        the system prompts the user for fallback choice.
        """
        with patch.object(browser_manager, '_create_browser_options') as mock_create_options, \
             patch('selenium.webdriver.Edge') as mock_edge, \
             patch('builtins.input') as mock_input:
            
            # Mock both attempts fail
            mock_edge.side_effect = [
                Exception("Headless initialization failed"),  # First attempt fails
                Exception("Headless retry failed")  # Retry also fails
            ]
            
            # Mock user chooses visible mode
            mock_input.return_value = 'visible'
            
            # Mock options
            mock_options = Mock(spec=EdgeOptions)
            mock_create_options.return_value = mock_options
            
            # Call method under test - this should either:
            # 1. Prompt user and continue with visible mode, OR
            # 2. Raise HeadlessInitializationError with retry info
            try:
                result = browser_manager.initialize_driver(headless=True)
                # If it succeeds, user prompt must have been called
                mock_input.assert_called()
            except HeadlessInitializationError as e:
                # If it raises error, it must include retry information
                assert e.attempt_number == 2
                assert "retry" in str(e).lower()

    def test_create_browser_options_headless_true_adds_headless_flag(self, browser_manager):
        """
        CONTRACT: BrowserManager._create_browser_options(headless=True) MUST add --headless=new.
        
        This test verifies that the headless flag is properly applied to browser options.
        """
        # Call method under test
        options = browser_manager._create_browser_options(headless=True)
        
        # CONTRACT ASSERTIONS
        # MUST be EdgeOptions instance
        assert isinstance(options, EdgeOptions)
        
        # MUST include headless argument
        # Note: This will fail until implementation is complete
        # We check the internal arguments list for --headless=new
        arguments = getattr(options, '_arguments', [])
        headless_args = [arg for arg in arguments if 'headless' in arg.lower()]
        assert len(headless_args) > 0, "Headless argument not found in browser options"
        assert any('--headless=new' in arg for arg in headless_args), "Expected --headless=new flag"

    def test_create_browser_options_headless_false_no_headless_flag(self, browser_manager):
        """
        CONTRACT: BrowserManager._create_browser_options(headless=False) MUST NOT add headless flags.
        
        This test verifies that no headless flags are added when headless=False.
        """
        # Call method under test
        options = browser_manager._create_browser_options(headless=False)
        
        # CONTRACT ASSERTIONS
        # MUST be EdgeOptions instance
        assert isinstance(options, EdgeOptions)
        
        # MUST NOT include headless arguments
        arguments = getattr(options, '_arguments', [])
        headless_args = [arg for arg in arguments if 'headless' in arg.lower()]
        assert len(headless_args) == 0, f"Unexpected headless arguments found: {headless_args}"

    def test_initialize_driver_honors_explicit_headless_over_config(self, browser_manager):
        """
        CONTRACT: Explicit headless parameter MUST override Config.HEADLESS.
        
        This test verifies that when an explicit headless parameter is provided,
        it takes precedence over the global configuration setting.
        """
        with patch('EXPERIMENTAL.corelib.config.Config') as mock_config, \
             patch.object(browser_manager, '_create_browser_options') as mock_create_options, \
             patch('selenium.webdriver.Edge') as mock_edge:
            
            # Set Config.HEADLESS to opposite of what we'll request
            mock_config.HEADLESS = True
            
            # Mock options and driver
            mock_options = Mock(spec=EdgeOptions)
            mock_create_options.return_value = mock_options
            mock_driver = Mock(spec=webdriver.Edge)
            mock_edge.return_value = mock_driver
            
            # Call with explicit headless=False (opposite of Config.HEADLESS=True)
            result = browser_manager.initialize_driver(headless=False)
            
            # CONTRACT ASSERTIONS
            # MUST honor explicit parameter, not config
            mock_create_options.assert_called_once_with(headless=False)
            assert result == mock_driver

    def test_initialize_driver_falls_back_to_config_when_no_explicit_param(self, browser_manager):
        """
        CONTRACT: When no explicit headless parameter, MUST use Config.HEADLESS.
        
        This test verifies that the Config.HEADLESS setting is used when
        no explicit headless parameter is provided.
        """
        with patch('EXPERIMENTAL.corelib.config.Config') as mock_config, \
             patch.object(browser_manager, '_create_browser_options') as mock_create_options, \
             patch('selenium.webdriver.Edge') as mock_edge:
            
            # Set Config.HEADLESS
            mock_config.HEADLESS = True
            
            # Mock options and driver
            mock_options = Mock(spec=EdgeOptions)
            mock_create_options.return_value = mock_options
            mock_driver = Mock(spec=webdriver.Edge)
            mock_edge.return_value = mock_driver
            
            # Call without explicit headless parameter (should use default)
            result = browser_manager.initialize_driver()
            
            # CONTRACT ASSERTIONS
            # Should detect Config.HEADLESS=True and apply it
            # This will fail until implementation correctly handles Config fallback
            mock_create_options.assert_called_once_with(headless=True)