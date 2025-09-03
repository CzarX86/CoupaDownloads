#!/usr/bin/env python3
"""
Simple test to verify main.py is working correctly.
"""

import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.excel_processor import ExcelProcessor
from core.browser import BrowserManager
from core.downloader import DownloadManager, LoginManager

def test_main_components():
    """Test main components to identify issues."""
    print("🧪 Testing main components...")
    
    try:
        # Test 1: Excel Processor
        print("\n1️⃣ Testing Excel Processor...")
        excel_processor = ExcelProcessor()
        excel_file_path = excel_processor.get_excel_file_path()
        
        if not os.path.exists(excel_file_path):
            print(f"❌ Excel file not found: {excel_file_path}")
            return
        
        print(f"✅ Excel file found: {excel_file_path}")
        
        # Read PO numbers
        po_entries, original_cols, hierarchy_cols, has_hierarchy_data = excel_processor.read_po_numbers_from_excel(excel_file_path)
        print(f"✅ Read {len(po_entries)} PO entries")
        print(f"✅ Hierarchy columns: {hierarchy_cols}")
        print(f"✅ Has hierarchy data: {has_hierarchy_data}")
        
        # Process PO numbers
        valid_entries = excel_processor.process_po_numbers(po_entries)
        print(f"✅ Valid entries: {len(valid_entries)}")
        
        if valid_entries:
            print(f"✅ Sample PO: {valid_entries[0]}")
        
        # Test 2: Browser Manager
        print("\n2️⃣ Testing Browser Manager...")
        browser_manager = BrowserManager()
        
        try:
            driver = browser_manager.initialize_driver()
            print("✅ Browser initialized successfully")
            
            # Test 3: Download Manager
            print("\n3️⃣ Testing Download Manager...")
            download_manager = DownloadManager(driver)
            print("✅ Download Manager created successfully")
            
            # Test 4: Login Manager
            print("\n4️⃣ Testing Login Manager...")
            login_manager = LoginManager(driver)
            print("✅ Login Manager created successfully")
            
            # Test login status
            is_logged_in = login_manager.is_logged_in()
            print(f"✅ Login status check: {'Logged in' if is_logged_in else 'Not logged in'}")
            
            # Clean up
            driver.quit()
            print("✅ Browser closed successfully")
            
        except Exception as e:
            print(f"❌ Browser test failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n✅ All main components are working!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_main_components()
