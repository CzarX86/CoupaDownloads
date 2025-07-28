import os
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from selenium.common.exceptions import TimeoutException

# Import the functions we want to test
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import _wait_for_download_complete, ensure_logged_in


class TestWaitForDownloadComplete:
    """Test the _wait_for_download_complete function"""
    
    def test_wait_for_download_complete_success(self, temp_download_folder):
        """Test successful download completion"""
        # Create some files in the temp directory
        test_file = os.path.join(temp_download_folder, "test.pdf")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Should return immediately since no .crdownload files exist
        _wait_for_download_complete(temp_download_folder, timeout=5)
    
    def test_wait_for_download_complete_with_crdownload(self, temp_download_folder):
        """Test download completion with .crdownload files"""
        # Create a .crdownload file
        crdownload_file = os.path.join(temp_download_folder, "test.pdf.crdownload")
        with open(crdownload_file, 'w') as f:
            f.write("downloading...")
        
        # Mock time to control the timeout
        with patch('time.time') as mock_time:
            mock_time.side_effect = [0, 1, 2, 3]  # Time progression
            
            # Should timeout after 3 seconds
            with pytest.raises(TimeoutException):
                _wait_for_download_complete(temp_download_folder, timeout=2)
    
    def test_wait_for_download_complete_crdownload_disappears(self, temp_download_folder):
        """Test when .crdownload files disappear during wait"""
        # Create a .crdownload file
        crdownload_file = os.path.join(temp_download_folder, "test.pdf.crdownload")
        with open(crdownload_file, 'w') as f:
            f.write("downloading...")
        
        # Mock time and os.listdir to simulate file disappearing
        with patch('time.time') as mock_time, \
             patch('os.listdir') as mock_listdir:
            
            mock_time.side_effect = [0, 1, 2]
            # First call: file exists, second call: file gone
            mock_listdir.side_effect = [
                ["test.pdf.crdownload", "other.txt"],
                ["other.txt"]  # .crdownload file disappeared
            ]
            
            # Should complete successfully
            _wait_for_download_complete(temp_download_folder, timeout=5)


class TestEnsureLoggedIn:
    """Test the ensure_logged_in function"""
    
    def test_ensure_logged_in_not_login_page(self, mock_driver):
        """Test when not on login page"""
        mock_driver.current_url = "https://unilever.coupahost.com/order_headers/12345"
        mock_driver.title = "Coupa PO Page"
        
        # Should detect already logged in
        ensure_logged_in(mock_driver)
    
    def test_ensure_logged_in_login_page_url_timeout(self, mock_driver):
        """Test when on login page (URL contains login) - timeout scenario"""
        mock_driver.current_url = "https://unilever.coupahost.com/login"
        mock_driver.title = "Coupa Login"
        
        with patch('time.time') as mock_time, \
             patch('time.sleep') as mock_sleep:
            # Mock time progression to simulate timeout
            mock_time.side_effect = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61]
            
            # Should timeout after 60 seconds
            with pytest.raises(TimeoutException):
                ensure_logged_in(mock_driver)
    
    def test_ensure_logged_in_login_success(self, mock_driver):
        """Test successful login detection"""
        # Start on login page
        mock_driver.current_url = "https://unilever.coupahost.com/login"
        mock_driver.title = "Coupa Login"
        
        with patch('time.time') as mock_time, \
             patch('time.sleep') as mock_sleep:
            # Mock time progression
            mock_time.side_effect = [0, 1, 2, 3, 4, 5]
            
            # Simulate successful login by changing URL
            def change_url():
                mock_driver.current_url = "https://unilever.coupahost.com/order_headers/12345"
            
            # Change URL after 3 seconds
            with patch('time.sleep', side_effect=lambda x: change_url() if mock_time() > 2 else None):
                ensure_logged_in(mock_driver)
    
    def test_ensure_logged_in_login_page_title(self, mock_driver):
        """Test when on login page (title contains 'Log in')"""
        mock_driver.current_url = "https://unilever.coupahost.com/some_page"
        mock_driver.title = "Log in to Coupa"
        
        # This should detect login success since URL doesn't contain login/sign_in
        ensure_logged_in(mock_driver)
    
    def test_ensure_logged_in_sign_in_url(self, mock_driver):
        """Test when on login page (URL contains sign_in)"""
        mock_driver.current_url = "https://unilever.coupahost.com/sign_in"
        mock_driver.title = "Coupa Page"
        
        with patch('time.time') as mock_time, \
             patch('time.sleep') as mock_sleep:
            # Mock time progression to simulate timeout
            mock_time.side_effect = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61]
            
            # Should timeout after 60 seconds
            with pytest.raises(TimeoutException):
                ensure_logged_in(mock_driver) 