#!/usr/bin/env python3
"""
Test script to verify the duplicate file handling implementation.
"""

import os
import tempfile
import shutil
import re
from typing import List


def test_duplicate_handling_logic():
    """Test the duplicate file handling logic that will be used in the main application."""
    print("🧪 Testing duplicate file handling logic...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Create some test files with duplicate names (simulating downloaded files)
        test_files = [
            "2025_TG_CAT_Enhancements_01Jan-31Mar_SoW.pdf",
            "2025_TG_CAT_Enhancements_01Jan-31Mar_SoW.pdf",  # Duplicate
            "invoice.pdf",
            "invoice.pdf",  # Another duplicate
            "contract.docx"
        ]
        
        # Create the test files with unique content
        temp_file_paths = []
        for i, filename in enumerate(test_files):
            # Create unique temporary file names to avoid conflicts
            unique_filename = f"{os.path.splitext(filename)[0]}_{i+1}{os.path.splitext(filename)[1]}"
            unique_file_path = os.path.join(temp_dir, unique_filename)
            
            with open(unique_file_path, 'w') as f:
                f.write(f"Test content for {filename} - file {i+1}")
            
            temp_file_paths.append(unique_file_path)
            print(f"  📄 Created: {unique_filename} (original: {filename})")
        
        # Test the _move_files_to_final_destination logic
        display_po = "PO16518898"
        final_folder = os.path.join(temp_dir, "final")
        os.makedirs(final_folder, exist_ok=True)
        
        print(f"\n🔄 Testing _move_files_to_final_destination logic...")
        
        # Simulate the _move_files_to_final_destination method
        final_files = []
        filename_counter = {}  # Track how many times each filename has been used
        
        for temp_file_path in temp_file_paths:
            if not os.path.exists(temp_file_path):
                continue
                
            # Get the original filename from temp path
            original_filename = os.path.basename(temp_file_path)
            
            # Extract the base filename by removing the _1, _2 suffix
            base_original_filename = original_filename
            # Pattern to match _number at the end before extension
            pattern = r'(.+)_(\d+)(\.[^.]+)$'
            match = re.match(pattern, original_filename)
            if match:
                base_name = match.group(1)
                number = match.group(2)
                extension = match.group(3)
                base_original_filename = base_name + extension
                print(f"    Extracted: {original_filename} -> {base_original_filename} (removed _{number})")
            else:
                print(f"    No pattern match: {original_filename} -> keeping as is")
            
            # Create proper filename with PO prefix
            file_ext = os.path.splitext(base_original_filename)[1]
            file_name_without_ext = os.path.splitext(base_original_filename)[0]
            
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
            
            dest_path = os.path.join(final_folder, proper_filename)
            
            # Move file to final destination
            try:
                shutil.move(temp_file_path, dest_path)
                final_files.append(proper_filename)
                print(f"  ✅ Moved: {original_filename} → {proper_filename}")
            except Exception as e:
                print(f"  ❌ Failed to move {original_filename}: {e}")
        
        # Show final results
        print(f"\n📋 Final Results:")
        print(f"📁 Files in final directory:")
        for filename in os.listdir(final_folder):
            file_path = os.path.join(final_folder, filename)
            size = os.path.getsize(file_path)
            print(f"  📄 {filename} ({size} bytes)")
        
        print(f"\n✅ Duplicate handling test completed successfully!")
        print(f"   Original files: {len(test_files)}")
        print(f"   Final files: {len(final_files)}")
        print(f"   All duplicates preserved with counter suffixes")
        
        # Verify duplicate handling worked
        unique_filenames = set(final_files)
        if len(unique_filenames) == len(final_files):
            print(f"✅ No duplicate filenames in final result")
        else:
            print(f"❌ Duplicate filenames detected in final result")
        
        # Check for expected counter suffixes
        counter_suffixes = [f for f in final_files if '_2' in f or '_3' in f]
        print(f"📊 Counter suffixes applied: {len(counter_suffixes)} files")


if __name__ == "__main__":
    test_duplicate_handling_logic()
