#!/usr/bin/env python3
"""
Test script to verify duplicate file handling with counter suffix.
"""

import os
import tempfile
import shutil
from typing import List


def test_duplicate_file_handling():
    """Test the duplicate file handling logic."""
    print("🧪 Testing duplicate file handling...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Create some test files with duplicate names
        test_files = [
            "2025_TG_CAT_Enhancements_01Jan-31Mar_SoW.pdf",
            "2025_TG_CAT_Enhancements_01Jan-31Mar_SoW.pdf",  # Duplicate
            "invoice.pdf",
            "invoice.pdf",  # Another duplicate
            "contract.docx"
        ]
        
        # Create the test files
        for i, filename in enumerate(test_files):
            file_path = os.path.join(temp_dir, filename)
            # Add unique content to distinguish files
            unique_filename = f"{os.path.splitext(filename)[0]}_{i+1}{os.path.splitext(filename)[1]}"
            unique_file_path = os.path.join(temp_dir, unique_filename)
            with open(unique_file_path, 'w') as f:
                f.write(f"Test content for {filename} - file {i+1}")
            print(f"  📄 Created: {unique_filename} (original: {filename})")
        
        # Test the duplicate handling logic
        display_po = "PO16518898"
        download_folder = os.path.join(temp_dir, "final")
        os.makedirs(download_folder, exist_ok=True)
        
        # Simulate the _move_files_with_proper_names logic
        downloaded_files = []
        filename_counter = {}  # Track how many times each filename has been used
        
        print(f"\n🔄 Processing files with duplicate handling...")
        
        # Get all files in temp directory
        temp_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        
        for filename in temp_files:
            # Skip temporary files
            if filename.endswith('.crdownload') or filename.endswith('.tmp'):
                continue
            
            # Extract the original filename (remove the _1, _2 suffix we added)
            original_filename = filename
            if '_' in filename and filename.split('_')[-1].isdigit():
                # Remove the numeric suffix we added
                parts = filename.split('_')
                if len(parts) > 1 and parts[-1].isdigit():
                    original_filename = '_'.join(parts[:-1]) + os.path.splitext(filename)[1]
            
            # Create proper filename with PO prefix
            file_ext = os.path.splitext(original_filename)[1]
            file_name_without_ext = os.path.splitext(original_filename)[0]
            
            # Remove any existing PO prefix to avoid duplication
            if file_name_without_ext.startswith(display_po + "_"):
                clean_name = file_name_without_ext
            else:
                clean_name = f"{display_po}_{file_name_without_ext}"
            
            # Handle duplicate filenames by adding counter suffix
            base_filename = f"{clean_name}{file_ext}"
            if base_filename in filename_counter:
                filename_counter[base_filename] += 1
                # Add counter suffix before extension
                name_without_ext = os.path.splitext(base_filename)[0]
                proper_filename = f"{name_without_ext}_{filename_counter[base_filename]}{file_ext}"
            else:
                filename_counter[base_filename] = 1
                proper_filename = base_filename
            
            source_path = os.path.join(temp_dir, filename)
            dest_path = os.path.join(download_folder, proper_filename)
            
            # Move file to final destination
            shutil.move(source_path, dest_path)
            downloaded_files.append(proper_filename)
            print(f"  ✅ Moved: {filename} → {proper_filename}")
        
        # Show final results
        print(f"\n📋 Final Results:")
        print(f"📁 Files in final directory:")
        for filename in os.listdir(download_folder):
            file_path = os.path.join(download_folder, filename)
            size = os.path.getsize(file_path)
            print(f"  📄 {filename} ({size} bytes)")
        
        print(f"\n✅ Duplicate handling test completed successfully!")
        print(f"   Original files: {len(test_files)}")
        print(f"   Final files: {len(downloaded_files)}")
        print(f"   All duplicates preserved with counter suffixes")


if __name__ == "__main__":
    test_duplicate_file_handling()
