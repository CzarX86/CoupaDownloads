import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestFileOperations:
    """Test file operations like downloading and renaming"""
    
    def test_file_extension_validation(self):
        """Test file extension validation"""
        ALLOWED_EXTENSIONS = [".pdf", ".msg", ".docx"]
        
        valid_files = ["invoice.pdf", "email.msg", "document.docx", "file.PDF", "file.MSG"]
        invalid_files = ["image.jpg", "video.mp4", "script.py", "data.txt", "archive.zip"]
        
        for filename in valid_files:
            assert any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)
        
        for filename in invalid_files:
            assert not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)
    
    def test_filename_extraction_from_aria_label(self):
        """Test extracting filename from aria-label"""
        import re
        
        test_cases = [
            ("invoice.pdf file attachment", "invoice.pdf"),
            ("email.msg file attachment", "email.msg"),
            ("document.docx file attachment", "document.docx"),
            ("file attachment", "attachment_1"),  # Fallback case
        ]
        
        for aria_label, expected in test_cases:
            filename_match = re.search(r"(.+?)\s*file attachment", aria_label)
            if filename_match:
                filename = filename_match.group(1)
            else:
                filename = "attachment_1"  # Fallback
            
            assert filename == expected
    
    def test_file_renaming_operation(self, temp_download_folder):
        """Test file renaming operation"""
        # Create a test file
        original_filename = "test_document.pdf"
        original_path = os.path.join(temp_download_folder, original_filename)
        
        with open(original_path, 'w') as f:
            f.write("test content")
        
        # Rename the file
        po_number = "15262984"
        new_filename = f"PO{po_number}_{original_filename}"
        new_path = os.path.join(temp_download_folder, new_filename)
        
        try:
            os.rename(original_path, new_path)
            
            # Verify the file was renamed
            assert os.path.exists(new_path)
            assert not os.path.exists(original_path)
            
            # Verify the content is preserved
            with open(new_path, 'r') as f:
                content = f.read()
            assert content == "test content"
            
        except Exception as e:
            pytest.fail(f"File renaming failed: {e}")
    
    def test_file_renaming_with_existing_file(self, temp_download_folder):
        """Test file renaming when target file already exists"""
        # Create original file
        original_filename = "test_document.pdf"
        original_path = os.path.join(temp_download_folder, original_filename)
        
        with open(original_path, 'w') as f:
            f.write("original content")
        
        # Create a file with the target name
        po_number = "15262984"
        target_filename = f"PO{po_number}_{original_filename}"
        target_path = os.path.join(temp_download_folder, target_filename)
        
        with open(target_path, 'w') as f:
            f.write("existing content")
        
        # Attempt to rename (behavior varies by OS)
        try:
            os.rename(original_path, target_path)
            # On some systems (like macOS), rename overwrites existing files
            # Check if the original file is gone and target has new content
            assert not os.path.exists(original_path)
            with open(target_path, 'r') as f:
                content = f.read()
            assert content == "original content"
        except FileExistsError:
            # On some systems (like Linux), rename raises FileExistsError
            # Expected behavior
            pass
    
    def test_download_folder_creation(self, temp_download_folder):
        """Test download folder creation"""
        # The folder should already exist from the fixture
        assert os.path.exists(temp_download_folder)
        assert os.path.isdir(temp_download_folder)
    
    def test_file_tracking_before_after(self, temp_download_folder):
        """Test tracking files before and after download"""
        # Create some initial files
        initial_files = ["existing1.pdf", "existing2.msg"]
        for filename in initial_files:
            filepath = os.path.join(temp_download_folder, filename)
            with open(filepath, 'w') as f:
                f.write(f"content for {filename}")
        
        # Track files before "download"
        before_files = set(os.listdir(temp_download_folder))
        
        # Simulate new files being downloaded
        new_files = ["new1.pdf", "new2.docx"]
        for filename in new_files:
            filepath = os.path.join(temp_download_folder, filename)
            with open(filepath, 'w') as f:
                f.write(f"content for {filename}")
        
        # Track files after "download"
        after_files = set(os.listdir(temp_download_folder))
        
        # Calculate new files
        new_files_set = after_files - before_files
        
        expected_new_files = set(new_files)
        assert new_files_set == expected_new_files
    
    def test_unsupported_file_skipping(self):
        """Test that unsupported file types are skipped"""
        ALLOWED_EXTENSIONS = [".pdf", ".msg", ".docx"]
        
        test_files = [
            ("invoice.pdf", True),      # Should be processed
            ("email.msg", True),        # Should be processed
            ("document.docx", True),    # Should be processed
            ("image.jpg", False),       # Should be skipped
            ("video.mp4", False),       # Should be skipped
            ("script.py", False),       # Should be skipped
            ("data.txt", False),        # Should be skipped
        ]
        
        for filename, should_process in test_files:
            is_supported = any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)
            assert is_supported == should_process, f"File {filename} should be {'processed' if should_process else 'skipped'}"
    
    def test_file_operations_error_handling(self, temp_download_folder):
        """Test error handling in file operations"""
        # Test renaming non-existent file
        non_existent_path = os.path.join(temp_download_folder, "nonexistent.pdf")
        new_path = os.path.join(temp_download_folder, "renamed.pdf")
        
        try:
            os.rename(non_existent_path, new_path)
            pytest.fail("Should have raised FileNotFoundError")
        except FileNotFoundError:
            # Expected behavior
            pass
        
        # Test renaming to invalid path
        test_file = os.path.join(temp_download_folder, "test.pdf")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        invalid_path = "/invalid/path/test.pdf"
        
        try:
            os.rename(test_file, invalid_path)
            pytest.fail("Should have raised OSError")
        except OSError:
            # Expected behavior
            pass 