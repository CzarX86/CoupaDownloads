#!/usr/bin/env python3
"""
Test to force movement of downloaded files from temp to hierarchical folders without CSV clearing.
"""

import os
import sys
import shutil

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add parallel_test to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from excel_processor import ExcelProcessor
from folder_hierarchy import FolderHierarchyManager


def test_force_movement():
    """Test force movement of downloaded files to hierarchical folders."""
    print("🧪 Testing Force File Movement")
    print("=" * 50)
    
    # Initialize components
    excel_processor = ExcelProcessor()
    folder_manager = FolderHierarchyManager()
    
    print("\n📁 Files in temp folder:")
    temp_folder = "/Users/juliocezar/Downloads/CoupaDownloads/Temp"
    if os.path.exists(temp_folder):
        files = os.listdir(temp_folder)
        for file in files:
            print(f"   📄 {file}")
    
    # Test movement for each PO
    test_pos = ["PO16518898", "PO16229343"]
    
    for po_number in test_pos:
        print(f"\n🔍 Testing movement for {po_number}:")
        
        try:
            # Read Excel to get PO hierarchy
            excel_path = excel_processor.get_excel_file_path()
            po_entries, original_cols, hierarchy_cols, has_hierarchy_data = excel_processor.read_po_numbers_from_excel(excel_path)
            
            # Find this PO in the data
            po_data = None
            for entry in po_entries:
                if entry.get('po_number') == po_number:
                    po_data = entry
                    break
            
            if po_data and has_hierarchy_data:
                # Create hierarchical folder path
                hierarchical_folder = folder_manager.create_folder_path(po_data, hierarchy_cols, True)
                print(f"   📁 Hierarchical folder: {hierarchical_folder}")
                
                # Determine status (assuming Success for this test)
                final_status = "Success"
                final_folder = f"{hierarchical_folder}_{final_status}"
                
                # Create final folder
                os.makedirs(final_folder, exist_ok=True)
                print(f"   📁 Created final folder: {final_folder}")
                
                # Move files from temp to final folder
                temp_files = os.listdir(temp_folder)
                moved_count = 0
                
                for temp_file in temp_files:
                    # Check if this file belongs to this PO (simplified logic)
                    if po_number in temp_file or temp_file.endswith('.pdf'):
                        temp_file_path = os.path.join(temp_folder, temp_file)
                        new_filename = f"{po_number}_{temp_file}"
                        final_file_path = os.path.join(final_folder, new_filename)
                        
                        # Handle duplicates
                        counter = 1
                        while os.path.exists(final_file_path):
                            name, ext = os.path.splitext(new_filename)
                            final_file_path = os.path.join(final_folder, f"{name} ({counter}){ext}")
                            counter += 1
                        
                        # Move file
                        shutil.move(temp_file_path, final_file_path)
                        print(f"      ✅ Moved: {temp_file} → {os.path.basename(final_file_path)}")
                        moved_count += 1
                
                print(f"   📦 Moved {moved_count} files for {po_number}")
                
            else:
                print(f"   ❌ PO {po_number} not found in Excel or no hierarchy data")
                
        except Exception as e:
            print(f"   ❌ Error processing {po_number}: {e}")
    
    print("\n📁 Final folder structure:")
    base_folder = "/Users/juliocezar/Downloads/CoupaDownloads"
    if os.path.exists(base_folder):
        for root, dirs, files in os.walk(base_folder):
            level = root.replace(base_folder, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}📁 {os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}📄 {file}")


if __name__ == "__main__":
    test_force_movement()
