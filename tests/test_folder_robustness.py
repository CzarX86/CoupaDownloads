import os
import shutil
import tempfile
import pytest
from src.lib.folder_hierarchy import FolderHierarchyManager

def test_finalize_folder_merge():
    """Test that finalize_folder correctly merges folders when the target exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        fm = FolderHierarchyManager()
        
        # Create a work folder with some files
        work_dir = os.path.join(temp_dir, "PO_123__WORK")
        os.makedirs(work_dir)
        with open(os.path.join(work_dir, "file1.txt"), "w") as f:
            f.write("source content")
        
        # Create a target folder with some files
        target_dir = os.path.join(temp_dir, "PO_123_COMPLETED")
        os.makedirs(target_dir)
        with open(os.path.join(target_dir, "file2.txt"), "w") as f:
            f.write("target content")
            
        # Call finalize_folder
        final_path = fm.finalize_folder(work_dir, "COMPLETED")
        
        # Verify results
        assert final_path == target_dir
        assert os.path.exists(os.path.join(target_dir, "file1.txt"))
        assert os.path.exists(os.path.join(target_dir, "file2.txt"))
        assert not os.path.exists(work_dir)
        
        with open(os.path.join(target_dir, "file1.txt"), "r") as f:
            assert f.read() == "source content"

def test_finalize_folder_rename():
    """Test that finalize_folder correctly renames when target does not exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        fm = FolderHierarchyManager()
        
        # Create a work folder
        work_dir = os.path.join(temp_dir, "PO_456__WORK")
        os.makedirs(work_dir)
        with open(os.path.join(work_dir, "file1.txt"), "w") as f:
            f.write("source content")
            
        # Call finalize_folder
        final_path = fm.finalize_folder(work_dir, "COMPLETED")
        
        # Verify result
        target_dir = os.path.join(temp_dir, "PO_456_COMPLETED")
        assert final_path == target_dir
        assert os.path.exists(target_dir)
        assert os.path.exists(os.path.join(target_dir, "file1.txt"))
        assert not os.path.exists(work_dir)

if __name__ == "__main__":
    # Manual run if needed
    pytest.main([__file__])
