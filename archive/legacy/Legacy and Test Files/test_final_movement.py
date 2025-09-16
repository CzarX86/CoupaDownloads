#!/usr/bin/env python3
"""
Test to force movement of downloaded files from temp to hierarchical folders.
"""

import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add parallel_test to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from download_control import DownloadControlManager
from excel_processor import ExcelProcessor


def test_final_movement():
    """Test final movement of downloaded files to hierarchical folders."""
    print("🧪 Testing Final File Movement")
    print("=" * 50)
    
    # Initialize components
    download_control = DownloadControlManager()
    excel_processor = ExcelProcessor()
    
    print("\n📊 Current CSV contents:")
    csv_path = download_control.get_csv_path()
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            print(f.read())
    
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
        
        # Get final status
        final_status = download_control.get_po_final_status(po_number)
        print(f"   📊 Final status: {final_status}")
        
        # Move files
        success = download_control.move_completed_po_files(po_number, excel_processor)
        print(f"   ✅ Movement result: {success}")
    
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
    test_final_movement()
