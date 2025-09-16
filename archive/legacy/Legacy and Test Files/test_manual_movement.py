#!/usr/bin/env python3
"""
Test to verify hierarchical folder movement with manual CSV data.
"""

import os
import sys
import csv

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add parallel_test to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from download_control import DownloadControlManager
from excel_processor import ExcelProcessor


def test_manual_movement():
    """Test hierarchical folder movement with manual CSV data."""
    print("🧪 Testing Manual Hierarchical Movement")
    print("=" * 50)
    
    # Create manual CSV data
    csv_path = "data/control/download_control_parallel.csv"
    
    # Create CSV with test data
    with open(csv_path, 'w', newline='') as csvfile:
        fieldnames = ['po_number', 'tab_id', 'file_name', 'status', 'download_start_time', 'download_complete_time', 'target_folder', 'error_message', 'tab_state']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Add test data
        writer.writerow({
            'po_number': 'PO16518898',
            'tab_id': 'TEST_TAB_1',
            'file_name': '2025_TG_CAT_Enhancements_01Jan-31Mar_SoW.pdf',
            'status': 'COMPLETED',
            'download_start_time': '2025-09-03T02:45:00.000000',
            'download_complete_time': '2025-09-03T02:45:05.000000',
            'target_folder': '/Users/juliocezar/Downloads/CoupaDownloads/PO16518898_Test',
            'error_message': '',
            'tab_state': 'CLOSED'
        })
        
        writer.writerow({
            'po_number': 'PO16229343',
            'tab_id': 'TEST_TAB_2',
            'file_name': 'Informatica_Q_-218480_C4U00085575.pdf',
            'status': 'COMPLETED',
            'download_start_time': '2025-09-03T02:45:10.000000',
            'download_complete_time': '2025-09-03T02:45:15.000000',
            'target_folder': '/Users/juliocezar/Downloads/CoupaDownloads/PO16229343_Test',
            'error_message': '',
            'tab_state': 'CLOSED'
        })
    
    print("📄 Created test CSV data")
    
    # Initialize components
    download_control = DownloadControlManager()
    excel_processor = ExcelProcessor()
    
    print("\n📊 CSV contents:")
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
    test_manual_movement()
