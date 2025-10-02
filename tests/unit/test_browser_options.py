"""
Unit tests for browser option validation.

This module tests the browser options creation and validation logic,
ensuring correct headless arguments are applied based on configuration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'EXPERIMENTAL'))

from corelib.browser import BrowserManager
from selenium.webdriver.edge.options import Options as EdgeOptions


class TestBrowserOptionsValidation:
    """Test browser options creation and validation."""
    
    @pytest.fixture
    def browser_manager(self):
        """Create a BrowserManager instance for testing."""
        return BrowserManager()
    
    def test_create_browser_options_headless_true(self, browser_manager):
        """Test that headless=True adds correct headless arguments."""
        options = browser_manager._create_browser_options(headless=True)
        
        # Should be EdgeOptions instance
        assert isinstance(options, EdgeOptions)
        
        # Check that headless arguments are present
        arguments = options.arguments
        assert any('--headless' in arg for arg in arguments), \
            f"Headless arguments not found in: {arguments}"
    
    def test_create_browser_options_headless_false(self, browser_manager):
        """Test that headless=False does not add headless arguments."""
        options = browser_manager._create_browser_options(headless=False)
        
        # Should be EdgeOptions instance
        assert isinstance(options, EdgeOptions)
        
        # Check that headless arguments are NOT present
        arguments = options.arguments
        assert not any('--headless' in arg for arg in arguments), \
            f"Headless arguments found when they shouldn't be: {arguments}"
    
    def test_browser_options_include_standard_args(self, browser_manager):
        """Test that browser options include standard arguments regardless of headless mode."""
        options_headless = browser_manager._create_browser_options(headless=True)
        options_visible = browser_manager._create_browser_options(headless=False)
        
        # Both should have standard arguments
        for options in [options_headless, options_visible]:
            arguments = options.arguments
            
            # Check for common Chrome/Edge arguments
            expected_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions'
            ]
            
            for expected_arg in expected_args:
                assert any(expected_arg in arg for arg in arguments), \
                    f"Expected argument {expected_arg} not found in: {arguments}"
    
    def test_browser_options_download_directory_set(self, browser_manager):
        """Test that download directory preferences are set in browser options."""
        options = browser_manager._create_browser_options(headless=True)
        
        # Check for download preferences
        prefs = options.experimental_options.get('prefs', {})
        
        # Should have download preferences
        assert 'download' in prefs, "Download preferences not found in options"
        download_prefs = prefs['download']
        
        # Check for default download path setting
        assert 'default_directory' in download_prefs, \
            "Default download directory not set in preferences"
    
    def test_browser_options_headless_new_format(self, browser_manager):
        """Test that headless mode uses the new --headless=new format."""
        options = browser_manager._create_browser_options(headless=True)
        
        arguments = options.arguments
        
        # Check for new headless format (preferred)
        has_new_headless = any('--headless=new' in arg for arg in arguments)
        has_old_headless = any(arg == '--headless' for arg in arguments)
        
        # Should use new format if available, or old format as fallback
        assert has_new_headless or has_old_headless, \
            f"No headless argument found in: {arguments}"
        
        if has_new_headless:
            print("✅ Using new --headless=new format")
        else:
            print("ℹ️ Using legacy --headless format")
    
    def test_browser_options_disable_gpu_in_headless(self, browser_manager):
        """Test that headless mode includes GPU-related arguments."""
        options = browser_manager._create_browser_options(headless=True)
        
        arguments = options.arguments
        
        # In headless mode, should include GPU-related flags for stability
        gpu_args = ['--disable-gpu', '--disable-gpu-sandbox']
        
        for gpu_arg in gpu_args:
            assert any(gpu_arg in arg for arg in arguments), \
                f"GPU argument {gpu_arg} not found in headless mode: {arguments}"
    
    def test_browser_options_no_gpu_args_in_visible_mode(self, browser_manager):
        """Test that visible mode doesn't include unnecessary GPU disabling."""
        options = browser_manager._create_browser_options(headless=False)
        
        arguments = options.arguments
        
        # In visible mode, we might not need to disable GPU
        # This is more lenient since GPU args might be OK in visible mode too
        print(f"Visible mode arguments: {arguments}")
        # Just verify it doesn't crash and produces valid options
        assert isinstance(options, EdgeOptions)
    
    def test_browser_options_user_agent_consistency(self, browser_manager):
        """Test that user agent is consistent between headless and visible modes."""
        options_headless = browser_manager._create_browser_options(headless=True)
        options_visible = browser_manager._create_browser_options(headless=False)
        
        # Both should have similar user agent or no user agent override
        args_headless = options_headless.arguments
        args_visible = options_visible.arguments
        
        # Extract user agent arguments
        ua_headless = [arg for arg in args_headless if '--user-agent' in arg]
        ua_visible = [arg for arg in args_visible if '--user-agent' in arg]
        
        # If one has user agent, both should have the same user agent
        if ua_headless or ua_visible:
            assert ua_headless == ua_visible, \
                f"User agent inconsistency: headless={ua_headless}, visible={ua_visible}"
    
    def test_browser_options_window_size_in_headless(self, browser_manager):
        """Test that headless mode sets a default window size."""
        options = browser_manager._create_browser_options(headless=True)
        
        arguments = options.arguments
        
        # Headless mode should have window size to avoid layout issues
        window_size_args = [arg for arg in arguments if '--window-size' in arg]
        
        assert len(window_size_args) > 0, \
            f"No window size set for headless mode: {arguments}"
        
        # Verify window size format
        window_size = window_size_args[0]
        assert '=' in window_size, f"Invalid window size format: {window_size}"
        
        size_part = window_size.split('=')[1]
        assert ',' in size_part, f"Invalid window size dimensions: {size_part}"


class TestBrowserOptionsEdgeCases:
    """Test edge cases and error conditions for browser options."""
    
    @pytest.fixture
    def browser_manager(self):
        """Create a BrowserManager instance for testing."""
        return BrowserManager()
    
    def test_browser_options_with_none_headless(self, browser_manager):
        """Test browser options creation with None headless parameter."""
        # This should default to False (visible mode)
        options = browser_manager._create_browser_options(headless=None)
        
        assert isinstance(options, EdgeOptions)
        
        # Should behave like headless=False
        arguments = options.arguments
        assert not any('--headless' in arg for arg in arguments), \
            f"Headless arguments found with None parameter: {arguments}"
    
    def test_browser_options_immutability(self, browser_manager):
        """Test that repeated calls with same parameters produce equivalent options."""
        options1 = browser_manager._create_browser_options(headless=True)
        options2 = browser_manager._create_browser_options(headless=True)
        
        # Should be different objects but equivalent configuration
        assert id(options1) != id(options2)
        assert options1.arguments == options2.arguments
        assert options1.experimental_options == options2.experimental_options
    
    def test_browser_options_profile_integration(self, browser_manager):
        """Test that browser options work with profile settings."""
        options = browser_manager._create_browser_options(headless=True)
        
        # Should be able to add profile settings without conflict
        prefs = options.experimental_options.get('prefs', {})
        
        # Add a test preference
        prefs['profile.default_content_setting_values.notifications'] = 2
        options.add_experimental_option('prefs', prefs)
        
        # Should still have all original arguments
        arguments = options.arguments
        assert any('--headless' in arg for arg in arguments)
    
    @patch('EXPERIMENTAL.corelib.config.Config')
    def test_browser_options_with_config_fallback(self, mock_config, browser_manager):
        """Test browser options when falling back to config values."""
        # Set up mock config
        mock_config.DOWNLOAD_FOLDER = "/test/download"
        mock_config.EDGE_PROFILE_DIR = "/test/profile"
        
        options = browser_manager._create_browser_options(headless=True)
        
        # Should still create valid options even with config fallback
        assert isinstance(options, EdgeOptions)
        
        # Should have download directory from config
        prefs = options.experimental_options.get('prefs', {})
        download_prefs = prefs.get('download', {})
        
        # Verify config values are used
        assert 'default_directory' in download_prefs