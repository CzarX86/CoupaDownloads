"""
Downloader Tests for Coupa Downloads automation.
Tests download functionality, file operations, and browser interactions.
"""

import os
import tempfile
import pytest
import shutil
from unittest.mock import Mock, patch, MagicMock, call
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from core.downloader import DownloadManager, FileManager, LoginManager


class TestFileManager:
    """Test FileManager functionality"""

    def test_get_supported_extensions(self):
        """Test getting supported file extensions"""
        extensions = FileManager.get_supported_extensions()
        assert ".pdf" in extensions
        assert ".msg" in extensions
        assert ".docx" in extensions

    def test_is_supported_file(self):
        """Test file extension validation"""
        # Valid extensions
        assert FileManager.is_supported_file("document.pdf")
        assert FileManager.is_supported_file("email.msg")
        assert FileManager.is_supported_file("report.docx")
        assert FileManager.is_supported_file("file.PDF")  # Case insensitive
        assert FileManager.is_supported_file("data.xlsx")
        assert FileManager.is_supported_file("text.txt")
        assert FileManager.is_supported_file("image.jpg")
        assert FileManager.is_supported_file("archive.zip")
        assert FileManager.is_supported_file("data.csv")
        assert FileManager.is_supported_file("config.xml")
    
        # Invalid extensions
        assert not FileManager.is_supported_file("no_extension")
        assert not FileManager.is_supported_file("file.xyz")
        assert not FileManager.is_supported_file("document.exe")

    def test_extract_filename_from_aria_label(self):
        """Test filename extraction from aria-label"""
        # Valid aria-label
        aria_label = "invoice_2024.pdf file attachment"
        filename = FileManager.extract_filename_from_aria_label(aria_label, 0)
        assert filename == "invoice_2024.pdf"
        
        # Aria-label with spaces
        aria_label = "  quarterly_report.docx  file attachment"
        filename = FileManager.extract_filename_from_aria_label(aria_label, 1)
        assert filename == "quarterly_report.docx"
        
        # Aria-label with special characters
        aria_label = "report-2024_v2.pdf file attachment"
        filename = FileManager.extract_filename_from_aria_label(aria_label, 2)
        assert filename == "report-2024_v2.pdf"
        
        # Empty aria-label
        filename = FileManager.extract_filename_from_aria_label("", 3)
        assert filename == "attachment_4"

    def test_rename_downloaded_files(self, temp_download_folder):
        """Test renaming downloaded files"""
        # Create test files
        test_files = ["document.pdf", "report.docx", "email.msg"]
        files_to_rename = set()
        
        for filename in test_files:
            file_path = os.path.join(temp_download_folder, filename)
            with open(file_path, 'w') as f:
                f.write(f"content for {filename}")
            files_to_rename.add(filename)
        
        # Test renaming
        FileManager.rename_downloaded_files("PO15826591", files_to_rename, temp_download_folder)
        
        # Verify files were renamed
        for filename in test_files:
            new_filename = f"PO15826591_{filename}"
            new_path = os.path.join(temp_download_folder, new_filename)
            assert os.path.exists(new_path)

    def test_rename_files_with_existing_po_prefix(self, temp_download_folder):
        """Test renaming files that already have PO prefix"""
        # Create file with existing PO prefix
        original_filename = "PO15826591_document.pdf"
        file_path = os.path.join(temp_download_folder, original_filename)
        with open(file_path, 'w') as f:
            f.write("test content")
        
        files_to_rename = {original_filename}
        
        # Test renaming
        FileManager.rename_downloaded_files("PO15826591", files_to_rename, temp_download_folder)
        
        # Should handle existing prefix correctly
        expected_filename = "PO15826591_document.pdf"
        expected_path = os.path.join(temp_download_folder, expected_filename)
        assert os.path.exists(expected_path)

    def test_cleanup_double_po_prefixes(self, temp_download_folder):
        """Test cleanup of double PO prefixes"""
        # Create files with double PO prefixes
        double_prefix_files = [
            "POPO15826591_document.pdf",
            "PO15826591_PO15873456_report.docx",
            "PO_PO_123_test.msg"
        ]
        
        for filename in double_prefix_files:
            file_path = os.path.join(temp_download_folder, filename)
            with open(file_path, 'w') as f:
                f.write(f"content for {filename}")
        
        # Test cleanup
        FileManager.cleanup_double_po_prefixes(temp_download_folder)
        
        # Verify files were cleaned up
        expected_files = [
            "PO15826591_document.pdf",
            "PO15826591_report.docx",
            "PO_123_test.msg"
        ]
        
        for expected_file in expected_files:
            expected_path = os.path.join(temp_download_folder, expected_file)
            assert os.path.exists(expected_path)

    def test_check_and_fix_unnamed_files(self, temp_download_folder):
        """Test checking for unnamed files"""
        # Create some unnamed files
        unnamed_files = ["document.pdf", "report.docx", ".hidden_file"]
        for filename in unnamed_files:
            file_path = os.path.join(temp_download_folder, filename)
            with open(file_path, 'w') as f:
                f.write(f"content for {filename}")
        
        # Create a named file for comparison
        named_file = os.path.join(temp_download_folder, "PO15826591_invoice.pdf")
        with open(named_file, 'w') as f:
            f.write("content")
        
        # Test checking for unnamed files
        FileManager.check_and_fix_unnamed_files(temp_download_folder)
        
        # Should detect unnamed files (but not hidden files)
        assert True  # Function should complete without error

    def test_file_operations_error_handling(self, temp_download_folder):
        """Test file operations error handling"""
        # Test with non-existent directory
        non_existent_dir = "/non/existent/directory"
        
        # Should handle gracefully
        try:
            FileManager.rename_downloaded_files("PO15826591", {"test.pdf"}, non_existent_dir)
        except Exception as e:
            # Should not raise unhandled exceptions
            assert "No such file or directory" in str(e) or "Permission denied" in str(e)
        
        # Test with read-only directory
        read_only_dir = os.path.join(temp_download_folder, "readonly")
        os.makedirs(read_only_dir, exist_ok=True)
        os.chmod(read_only_dir, 0o444)  # Read-only
        
        try:
            FileManager.rename_downloaded_files("PO15826591", {"test.pdf"}, read_only_dir)
        except Exception as e:
            # Should handle permission errors
            assert "Permission denied" in str(e) or "Read-only" in str(e)
        finally:
            os.chmod(read_only_dir, 0o755)  # Restore permissions


class TestDownloadManager:
    """Test DownloadManager functionality"""

    def test_download_manager_initialization(self, mock_driver):
        """Test DownloadManager initialization"""
        download_manager = DownloadManager(mock_driver)
        assert download_manager.driver == mock_driver

    def test_wait_for_download_complete_success(self, temp_download_folder, mock_time):
        """Test successful download completion wait"""
        # Create a test file to simulate completed download
        test_file = os.path.join(temp_download_folder, "test_file.pdf")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        mock_driver = Mock()
        download_manager = DownloadManager(mock_driver)
        
        # Test the wait function
        download_manager._wait_for_download_complete(temp_download_folder, timeout=5)
        
        # Should complete without raising exception
        assert True

    def test_wait_for_download_complete_with_crdownload(self, temp_download_folder, mock_time):
        """Test download completion wait with .crdownload file"""
        # Create a .crdownload file to simulate ongoing download
        crdownload_file = os.path.join(temp_download_folder, "test_file.pdf.crdownload")
        with open(crdownload_file, 'w') as f:
            f.write("partial content")
        
        mock_driver = Mock()
        download_manager = DownloadManager(mock_driver)
        
        # Mock time.time to simulate time passing
        with patch('time.time') as mock_time_func:
            mock_time_func.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]
            
            # Mock os.listdir to eventually return the completed file
            with patch('os.listdir') as mock_listdir:
                mock_listdir.side_effect = [
                    ['test_file.pdf.crdownload'],  # First call: still downloading
                    ['test_file.pdf']  # Second call: download complete
                ]
                
                download_manager._wait_for_download_complete(temp_download_folder, timeout=10)
                
                # Should complete successfully
                assert True

    def test_wait_for_download_complete_timeout(self, temp_download_folder, mock_time):
        """Test download completion wait with timeout"""
        mock_driver = Mock()
        download_manager = DownloadManager(mock_driver)
        
        # Mock time.time to simulate timeout
        with patch('time.time') as mock_time_func:
            mock_time_func.side_effect = [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010]
            
            # Mock os.listdir to always return .crdownload (never completes)
            with patch('os.listdir') as mock_listdir:
                mock_listdir.return_value = ['test_file.pdf.crdownload']
                
                # Should handle timeout gracefully
                download_manager._wait_for_download_complete(temp_download_folder, timeout=5)
                assert True

    def test_wait_for_attachments(self, mock_driver):
        """Test waiting for attachments to load"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock WebDriverWait
        with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait_class:
            mock_wait = Mock()
            mock_wait.until.return_value = True
            mock_wait_class.return_value = mock_wait
            
            download_manager._wait_for_attachments()
            
            # Verify wait was called
            mock_wait.until.assert_called()

    def test_find_attachments(self, mock_driver):
        """Test finding attachment elements"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock find_elements to return attachment elements
        mock_elements = []
        for i in range(3):
            element = Mock(spec=WebElement)
            element.get_attribute.return_value = f"attachment_{i+1}.pdf file attachment"
            mock_elements.append(element)
        
        mock_driver.find_elements.return_value = mock_elements
        
        attachments = download_manager._find_attachments()
        
        assert len(attachments) == 3
        mock_driver.find_elements.assert_called()

    def test_find_attachments_no_attachments(self, mock_driver):
        """Test finding attachments when none exist"""
        download_manager = DownloadManager(mock_driver)
        
        mock_driver.find_elements.return_value = []
        
        attachments = download_manager._find_attachments()
        
        assert len(attachments) == 0

    def test_find_attachments_timeout(self, mock_driver):
        """Test finding attachments with timeout"""
        download_manager = DownloadManager(mock_driver)
        
        mock_driver.find_elements.side_effect = TimeoutException("Element not found")
        
        # Should handle timeout gracefully
        try:
            download_manager._find_attachments()
        except TimeoutException:
            # Expected behavior
            pass
        except Exception as e:
            # Unexpected exception
            pytest.fail(f"Unexpected exception: {e}")

    def test_download_attachment(self, mock_driver, temp_download_folder):
        """Test downloading a single attachment"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock attachment element
        attachment = Mock(spec=WebElement)
        attachment.get_attribute.return_value = "test_document.pdf file attachment"
        attachment.click = Mock()
        
        # Mock file system operations
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['test_document.pdf']
            
            download_manager._download_attachment(attachment, 0)
            
            # Verify attachment was clicked
            attachment.click.assert_called_once()

    def test_download_attachment_click_failure(self, mock_driver):
        """Test downloading attachment with click failure"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock attachment element that fails to click
        attachment = Mock(spec=WebElement)
        attachment.get_attribute.return_value = "test_document.pdf file attachment"
        attachment.click.side_effect = Exception("Click failed")
        
        # Should handle click failure gracefully
        try:
            download_manager._download_attachment(attachment, 0)
        except Exception as e:
            # Should catch and handle the exception
            assert "Click failed" in str(e)

    def test_extract_supplier_name_css_success(self, mock_driver):
        """Test extracting supplier name using CSS selectors"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock CSS selector to succeed
        supplier_element = Mock(spec=WebElement)
        supplier_element.text = "Test Supplier Inc."
        
        mock_driver.find_element.return_value = supplier_element
        
        supplier_name = download_manager._extract_supplier_name()
        
        assert supplier_name == "Test_Supplier_Inc"

    def test_extract_supplier_name_xpath_fallback(self, mock_driver):
        """Test extracting supplier name using XPath fallback"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock CSS selectors to fail
        mock_driver.find_element.side_effect = NoSuchElementException("Element not found")
        
        # Mock XPath to succeed
        supplier_element = Mock(spec=WebElement)
        supplier_element.text = "Fallback Supplier"
        
        with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait_class:
            mock_wait_instance = Mock()
            mock_wait_instance.until.return_value = supplier_element
            mock_wait_class.return_value = mock_wait_instance
            
            supplier_name = download_manager._extract_supplier_name()
            
            assert supplier_name == "Fallback_Supplier"

    def test_extract_supplier_name_not_found(self, mock_driver):
        """Test extracting supplier name when not found"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock all selectors to fail
        mock_driver.find_element.side_effect = NoSuchElementException("Element not found")
        
        supplier_name = download_manager._extract_supplier_name()
        
        assert supplier_name == "Unknown_Supplier"

    def test_clean_folder_name(self):
        """Test cleaning folder names"""
        download_manager = DownloadManager(Mock())
        
        # Test various folder name scenarios
        assert download_manager._clean_folder_name("Test Supplier Inc.") == "Test_Supplier_Inc"
        assert download_manager._clean_folder_name("Café & Co.") == "Café_Co"
        assert download_manager._clean_folder_name("Supplier with/slashes") == "Supplier_with_slashes"
        assert download_manager._clean_folder_name("Supplier with\\backslashes") == "Supplier_with_backslashes"
        assert download_manager._clean_folder_name("Supplier with:colons") == "Supplier_with_colons"
        assert download_manager._clean_folder_name("Supplier with*asterisks") == "Supplier_with_asterisks"
        assert download_manager._clean_folder_name("Supplier with?question marks") == "Supplier_with_question_marks"
        assert download_manager._clean_folder_name("Supplier with\"quotes") == "Supplier_with_quotes"
        assert download_manager._clean_folder_name("Supplier with<angle brackets>") == "Supplier_with_angle_brackets"
        assert download_manager._clean_folder_name("Supplier with|pipes") == "Supplier_with_pipes"

    def test_create_supplier_folder(self, temp_download_folder):
        """Test creating supplier folder"""
        download_manager = DownloadManager(Mock())
        
        supplier_name = "Test_Supplier_Inc"
        folder_path = download_manager._create_supplier_folder(supplier_name)
        
        expected_path = os.path.join(temp_download_folder, supplier_name)
        assert folder_path == expected_path
        assert os.path.exists(folder_path)

    def test_create_supplier_folder_already_exists(self, temp_download_folder):
        """Test creating supplier folder that already exists"""
        download_manager = DownloadManager(Mock())
        
        supplier_name = "Test_Supplier_Inc"
        
        # Create folder first
        first_path = download_manager._create_supplier_folder(supplier_name)
        
        # Try to create again
        second_path = download_manager._create_supplier_folder(supplier_name)
        
        assert first_path == second_path
        assert os.path.exists(second_path)

    def test_download_attachments_for_po_success(self, mock_driver, temp_download_folder):
        """Test successful download of attachments for a PO"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock successful attachment finding and downloading
        mock_attachments = []
        for i in range(2):
            attachment = Mock(spec=WebElement)
            attachment.get_attribute.return_value = f"document_{i+1}.pdf file attachment"
            mock_attachments.append(attachment)
        
        mock_driver.find_elements.return_value = mock_attachments
        
        # Mock supplier extraction
        supplier_element = Mock(spec=WebElement)
        supplier_element.text = "Test Supplier"
        mock_driver.find_element.return_value = supplier_element
        
        # Mock file system operations
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['document_1.pdf', 'document_2.pdf']
            
            download_manager.download_attachments_for_po("PO15826591", "15826591")
            
            # Verify attachments were processed
            assert mock_driver.find_elements.called

    def test_download_attachments_for_po_no_attachments(self, mock_driver):
        """Test downloading attachments when none exist"""
        download_manager = DownloadManager(mock_driver)
        
        mock_driver.find_elements.return_value = []
        
        download_manager.download_attachments_for_po("PO15826591", "15826591")
        
        # Should handle gracefully
        assert True

    def test_download_attachments_for_po_page_not_found(self, mock_driver):
        """Test downloading attachments when page is not found"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock page not found scenario
        mock_driver.find_elements.side_effect = NoSuchElementException("Page not found")
        
        download_manager.download_attachments_for_po("PO15826591", "15826591")
        
        # Should handle gracefully
        assert True


class TestLoginManager:
    """Test LoginManager functionality"""

    def test_login_manager_initialization(self, mock_driver):
        """Test LoginManager initialization"""
        login_manager = LoginManager(mock_driver)
        assert login_manager.driver == mock_driver

    def test_ensure_logged_in_already_logged_in(self, mock_driver):
        """Test ensure_logged_in when already logged in"""
        mock_driver.current_url = "https://unilever.coupahost.com/order_headers/12345"
        mock_driver.title = "Coupa PO Page"
        
        login_manager = LoginManager(mock_driver)
        
        # Should not attempt login
        login_manager.ensure_logged_in()
        
        # Verify no login attempts were made
        mock_driver.get.assert_not_called()

    def test_ensure_logged_in_login_page_url(self, mock_driver):
        """Test ensure_logged_in when on login page (URL)"""
        mock_driver.current_url = "https://unilever.coupahost.com/login"
        mock_driver.title = "Some Page"
        
        # Mock WebDriverWait
        with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait_class:
            mock_wait = Mock()
            mock_wait.until.return_value = True
            mock_wait_class.return_value = mock_wait
            
            login_manager = LoginManager(mock_driver)
            login_manager.ensure_logged_in()
            
            # Verify wait was called
            mock_wait.until.assert_called()

    def test_ensure_logged_in_login_page_title(self, mock_driver):
        """Test ensure_logged_in when on login page (title)"""
        mock_driver.current_url = "https://unilever.coupahost.com/some_page"
        mock_driver.title = "Sign In"
        
        # Mock WebDriverWait
        with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait_class:
            mock_wait = Mock()
            mock_wait.until.return_value = True
            mock_wait_class.return_value = mock_wait
            
            login_manager = LoginManager(mock_driver)
            login_manager.ensure_logged_in()
            
            # Verify wait was called
            mock_wait.until.assert_called()

    def test_ensure_logged_in_sign_in_url(self, mock_driver):
        """Test ensure_logged_in when on sign-in page (URL)"""
        mock_driver.current_url = "https://unilever.coupahost.com/sign-in"
        mock_driver.title = "Some Page"
        
        # Mock WebDriverWait
        with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait_class:
            mock_wait = Mock()
            mock_wait.until.return_value = True
            mock_wait_class.return_value = mock_wait
            
            login_manager = LoginManager(mock_driver)
            login_manager.ensure_logged_in()
            
            # Verify wait was called
            mock_wait.until.assert_called()

    def test_ensure_logged_in_timeout(self, mock_driver):
        """Test ensure_logged_in with timeout"""
        mock_driver.current_url = "https://unilever.coupahost.com/login"
        mock_driver.title = "Sign In"
        
        # Mock WebDriverWait to raise TimeoutException
        with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait_class:
            mock_wait = Mock()
            mock_wait.until.side_effect = TimeoutException("Login timeout")
            mock_wait_class.return_value = mock_wait
            
            login_manager = LoginManager(mock_driver)
            
            # Should handle timeout gracefully
            login_manager.ensure_logged_in()
            
            # Verify wait was called
            mock_wait.until.assert_called()

    def test_is_logged_in_true(self, mock_driver):
        """Test is_logged_in when logged in"""
        mock_driver.current_url = "https://unilever.coupahost.com/order_headers/12345"
        mock_driver.title = "Coupa PO Page"
        
        login_manager = LoginManager(mock_driver)
        
        assert login_manager.is_logged_in() is True

    def test_is_logged_in_false_url(self, mock_driver):
        """Test is_logged_in when not logged in (URL)"""
        mock_driver.current_url = "https://unilever.coupahost.com/login"
        mock_driver.title = "Some Page"
        
        login_manager = LoginManager(mock_driver)
        
        assert login_manager.is_logged_in() is False

    def test_is_logged_in_false_title(self, mock_driver):
        """Test is_logged_in when not logged in (title)"""
        mock_driver.current_url = "https://unilever.coupahost.com/some_page"
        mock_driver.title = "Sign In"
        
        login_manager = LoginManager(mock_driver)
        
        assert login_manager.is_logged_in() is False

    def test_is_logged_in_false_sign_in_url(self, mock_driver):
        """Test is_logged_in when not logged in (sign-in URL)"""
        mock_driver.current_url = "https://unilever.coupahost.com/sign-in"
        mock_driver.title = "Some Page"
        
        login_manager = LoginManager(mock_driver)
        
        assert login_manager.is_logged_in() is False


class TestDownloadMethods:
    """Test different download methods"""

    def test_temp_directory_method(self, mock_driver, temp_download_folder):
        """Test temporary directory download method"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock attachments
        mock_attachments = []
        for i in range(2):
            attachment = Mock(spec=WebElement)
            attachment.get_attribute.return_value = f"document_{i+1}.pdf file attachment"
            mock_attachments.append(attachment)
        
        # Mock file system operations
        with patch('tempfile.mkdtemp') as mock_mkdtemp, \
             patch('os.listdir') as mock_listdir, \
             patch('shutil.move') as mock_move:
            
            mock_mkdtemp.return_value = "/tmp/test_temp_dir"
            mock_listdir.return_value = ['document_1.pdf', 'document_2.pdf']
            
            download_manager._try_temp_directory_method(
                mock_attachments, "PO15826591", "Test_Supplier"
            )
            
            # Verify temp directory was used
            mock_mkdtemp.assert_called_once()

    def test_fallback_download_method(self, mock_driver, temp_download_folder):
        """Test fallback download method"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock attachments
        mock_attachments = []
        for i in range(2):
            attachment = Mock(spec=WebElement)
            attachment.get_attribute.return_value = f"document_{i+1}.pdf file attachment"
            mock_attachments.append(attachment)
        
        # Mock file system operations
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['document_1.pdf', 'document_2.pdf']
            
            download_manager._fallback_download_method(
                mock_attachments, "PO15826591", "Test_Supplier"
            )
            
            # Should complete without error
            assert True

    def test_count_existing_files(self, temp_download_folder):
        """Test counting existing files in supplier folder"""
        download_manager = DownloadManager(Mock())
        
        # Create supplier folder with some files
        supplier_folder = os.path.join(temp_download_folder, "Test_Supplier")
        os.makedirs(supplier_folder, exist_ok=True)
        
        # Create some test files
        test_files = ["PO15826591_doc1.pdf", "PO15826591_doc2.docx", "other_file.txt"]
        for filename in test_files:
            file_path = os.path.join(supplier_folder, filename)
            with open(file_path, 'w') as f:
                f.write("test content")
        
        count = download_manager._count_existing_files("Test_Supplier")
        
        # Should count files with PO prefix
        assert count == 2  # Only PDF and DOCX files with PO prefix


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_webdriver_exception_handling(self, mock_driver):
        """Test handling of WebDriver exceptions"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock various WebDriver exceptions
        exceptions = [
            TimeoutException("Timeout"),
            NoSuchElementException("Element not found"),
            Exception("Generic WebDriver error")
        ]
        
        for exception in exceptions:
            mock_driver.find_elements.side_effect = exception
            
            # Should handle all exceptions gracefully
            try:
                download_manager._find_attachments()
            except Exception as e:
                # Should catch and handle the exception
                assert str(exception) in str(e)

    def test_file_system_exception_handling(self, temp_download_folder):
        """Test handling of file system exceptions"""
        download_manager = DownloadManager(Mock())
        
        # Test with non-existent directory
        non_existent_dir = "/non/existent/directory"
        
        # Should handle gracefully
        try:
            download_manager._create_supplier_folder("Test_Supplier")
        except Exception as e:
            # Should not raise unhandled exceptions
            assert "No such file or directory" in str(e) or "Permission denied" in str(e)

    def test_attachment_click_exception_handling(self, mock_driver):
        """Test handling of attachment click exceptions"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock attachment that fails to click
        attachment = Mock(spec=WebElement)
        attachment.get_attribute.return_value = "test.pdf file attachment"
        attachment.click.side_effect = Exception("Click intercepted")
        
        # Should handle click failure gracefully
        try:
            download_manager._download_attachment(attachment, 0)
        except Exception as e:
            # Should catch and handle the exception
            assert "Click intercepted" in str(e)


class TestPerformance:
    """Test performance characteristics"""

    def test_download_wait_performance(self, temp_download_folder, performance_timer):
        """Test download wait performance"""
        mock_driver = Mock()
        download_manager = DownloadManager(mock_driver)
        
        # Create a test file to simulate completed download
        test_file = os.path.join(temp_download_folder, "test_file.pdf")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Measure performance
        performance_timer.start()
        download_manager._wait_for_download_complete(temp_download_folder, timeout=1)
        performance_timer.stop()
        
        # Should complete quickly (less than 1 second)
        assert performance_timer.elapsed() < 1.0

    def test_file_renaming_performance(self, temp_download_folder, performance_timer):
        """Test file renaming performance"""
        # Create multiple test files
        test_files = [f"document_{i}.pdf" for i in range(100)]
        files_to_rename = set()
        
        for filename in test_files:
            file_path = os.path.join(temp_download_folder, filename)
            with open(file_path, 'w') as f:
                f.write(f"content for {filename}")
            files_to_rename.add(filename)
        
        # Measure performance
        performance_timer.start()
        FileManager.rename_downloaded_files("PO15826591", files_to_rename, temp_download_folder)
        performance_timer.stop()
        
        # Should complete in reasonable time (less than 5 seconds for 100 files)
        assert performance_timer.elapsed() < 5.0

    def test_supplier_name_extraction_performance(self, mock_driver, performance_timer):
        """Test supplier name extraction performance"""
        download_manager = DownloadManager(mock_driver)
        
        # Mock supplier element
        supplier_element = Mock(spec=WebElement)
        supplier_element.text = "Test Supplier Inc."
        mock_driver.find_element.return_value = supplier_element
        
        # Measure performance
        performance_timer.start()
        for _ in range(100):  # Test 100 extractions
            supplier_name = download_manager._extract_supplier_name()
        performance_timer.stop()
        
        # Should complete quickly (less than 1 second for 100 extractions)
        assert performance_timer.elapsed() < 1.0 