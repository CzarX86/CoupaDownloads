#!/usr/bin/env python3
"""
Test to force movement of downloaded files from temp to hierarchical folders using CSV control.
"""

import os
import sys
import shutil
import csv

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add parallel_test to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from excel_processor import ExcelProcessor
from folder_hierarchy import FolderHierarchyManager


def test_correct_movement():
    """Test correct movement using CSV control."""
    print("🧪 Testing Correct File Movement Using CSV")
    print("=" * 50)
    
    # Initialize components
    excel_processor = ExcelProcessor()
    folder_manager = FolderHierarchyManager()
    
    # Read CSV control file
    csv_path = "data/control/download_control_parallel.csv"
    
    print("\n📊 Reading CSV control file:")
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            print(f.read())
    
    print("\n📁 Files in temp folder:")
    temp_folder = "/Users/juliocezar/Downloads/CoupaDownloads/Temp"
    if os.path.exists(temp_folder):
        files = os.listdir(temp_folder)
        for file in files:
            print(f"   📄 {file}")
    
    # Read CSV to get download records
    download_records = []
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['po_number'] and row['file_name'] and row['status'] == 'COMPLETED':
                    download_records.append(row)
    
    print(f"\n📋 Found {len(download_records)} completed downloads in CSV")
    
    # Group by PO
    po_downloads = {}
    for record in download_records:
        po_number = record['po_number']
        if po_number not in po_downloads:
            po_downloads[po_number] = []
        po_downloads[po_number].append(record)
    
    # Process each PO with its downloads
    for po_number, downloads in po_downloads.items():
        print(f"\n🔍 Processing PO: {po_number}")
        print(f"   📋 Downloads: {len(downloads)}")
        
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
                
                # Move files for this specific PO
                moved_count = 0
                for download_record in downloads:
                    original_filename = download_record['file_name']
                    temp_file_path = os.path.join(temp_folder, original_filename)
                    
                    if os.path.exists(temp_file_path):
                        new_filename = f"{po_number}_{original_filename}"
                        final_file_path = os.path.join(final_folder, new_filename)
                        
                        # Handle duplicates
                        counter = 1
                        while os.path.exists(final_file_path):
                            name, ext = os.path.splitext(new_filename)
                            final_file_path = os.path.join(final_folder, f"{name} ({counter}){ext}")
                            counter += 1
                        
                        # Move file
                        shutil.move(temp_file_path, final_file_path)
                        print(f"      ✅ Moved: {original_filename} → {os.path.basename(final_file_path)}")
                        moved_count += 1
                    else:
                        print(f"      ⚠️ File not found: {temp_file_path}")
                
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
    test_correct_movement()
