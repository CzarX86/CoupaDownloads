#!/usr/bin/env python3
"""
Test script to verify that downloads are saved in the correct hierarchical folders.
"""

import os
import sys
import time
from src.core.browser import BrowserManager
from src.core.downloader import Downloader
from src.core.excel_processor import ExcelProcessor
from src.core.folder_hierarchy import FolderHierarchyManager

def test_download_hierarchy():
    """Test that downloads are saved in the correct hierarchical folders."""
    print("🧪 Testing Download Hierarchy Functionality")
    print("=" * 50)
    
    # Initialize components
    excel_processor = ExcelProcessor()
    browser_manager = BrowserManager()
    folder_hierarchy = FolderHierarchyManager()
    
    try:
        # Read Excel file
        excel_path = excel_processor.get_excel_file_path()
        po_entries, original_cols, hierarchy_cols, has_hierarchy_data = excel_processor.read_po_numbers_from_excel(excel_path)
        
        print(f"📊 Excel Analysis Results:")
        print(f"   Original columns: {original_cols}")
        print(f"   Hierarchy columns: {hierarchy_cols}")
        print(f"   Has hierarchy data: {has_hierarchy_data}")
        print()
        
        # Test with first PO that has attachments
        test_po = None
        for entry in po_entries:
            if entry.get('po_number') == 'PO16518898':  # This PO has 2 attachments
                test_po = entry
                break
        
        if not test_po:
            print("❌ PO16518898 not found in entries")
            return
        
        print(f"🔍 Testing PO: {test_po.get('po_number', 'Unknown')}")
        print(f"   Attachments found: {test_po.get('attachments_found', 0)}")
        
        # Create folder path
        folder_path = folder_hierarchy.create_folder_path(
            test_po, hierarchy_cols, has_hierarchy_data
        )
        print(f"   📁 Created folder: {folder_path}")
        
        # Initialize browser with specific download directory
        browser_manager.initialize_driver_with_download_dir(folder_path)
        downloader = Downloader(browser_manager.driver, browser_manager)
        
        # Get clean PO number (without PO prefix)
        po_number = test_po['po_number']
        clean_po = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
        
        print(f"   🌐 Downloading attachments for PO: {clean_po}")
        
        # Download attachments
        success, message = downloader.download_attachments_for_po(clean_po)
        
        print(f"   📥 Download result: {success}")
        print(f"   📝 Message: {message}")
        
        # Wait a bit for downloads to complete
        time.sleep(5)
        
        # Check if files were downloaded to the correct folder
        if os.path.exists(folder_path):
            files_in_folder = os.listdir(folder_path)
            print(f"   📁 Files in folder: {files_in_folder}")
            
            if files_in_folder:
                print("   ✅ Files were downloaded to the correct hierarchical folder!")
            else:
                print("   ⚠️ No files found in the hierarchical folder")
        else:
            print("   ❌ Hierarchical folder does not exist")
        
        # Cleanup
        browser_manager.cleanup()
        
        print("✅ Download hierarchy test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        browser_manager.cleanup()

if __name__ == "__main__":
    test_download_hierarchy()
