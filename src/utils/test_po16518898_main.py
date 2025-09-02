#!/usr/bin/env python3
"""
Test script to run the main program on PO16518898 to verify duplicate handling.
"""

import os
import sys
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.excel_processor import ExcelProcessor
from core.downloader import DownloadManager
from core.browser import BrowserManager


def test_po16518898_download():
    """Test downloading PO16518898 to verify duplicate handling."""
    print("🧪 Testing PO16518898 download with duplicate handling...")
    
    # Create a test Excel file with just PO16518898
    test_data = {
        'PO_NUMBER': ['PO16518898'],
        'STATUS': ['PENDING'],
        'SUPPLIER': ['Test Supplier'],
        'ATTACHMENTS_FOUND': [0],
        'ATTACHMENTS_DOWNLOADED': [0],
        'Priority': ['High'],
        'Supplier Segment': ['IT'],
        'Spend Type': ['Services'],
        'L1 UU Supplier Name': ['Test Supplier'],
        '<|>': [''],
        'AttachmentName': ['']
    }
    
    # Create test Excel file
    test_excel_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'input', 'test_po16518898.xlsx')
    os.makedirs(os.path.dirname(test_excel_path), exist_ok=True)
    
    df = pd.DataFrame(test_data)
    df.to_excel(test_excel_path, index=False)
    print(f"📄 Created test Excel file: {test_excel_path}")
    
    # Setup browser and download manager
    browser_manager = BrowserManager()
    driver = browser_manager.initialize_driver()
    download_manager = DownloadManager(driver)
    
    try:
        # Navigate to PO page
        po_url = f"https://unilever.coupahost.com/order_headers/16518898"
        print(f"🌐 Navigating to: {po_url}")
        driver.get(po_url)
        
        # Check for login requirement
        if "login" in driver.current_url.lower() or "sign_in" in driver.current_url.lower() or "identity" in driver.current_url.lower():
            print(f"🔐 Login required. Please login manually and press Enter when ready...")
            input("Press Enter after logging in...")
            driver.get(po_url)
        
        # Find attachments
        attachments = download_manager._find_attachments()
        print(f"📎 Found {len(attachments)} attachments")
        
        if attachments:
            # Create a test download folder
            test_download_folder = os.path.join(os.path.expanduser("~"), "Downloads", "Test_PO16518898")
            os.makedirs(test_download_folder, exist_ok=True)
            print(f"📁 Using test download folder: {test_download_folder}")
            
            # Mock PO data
            po_data = {
                'po_number': 'PO16518898',
                'status': 'PENDING',
                'supplier': 'Test Supplier',
                'attachments_found': len(attachments),
                'attachments_downloaded': 0
            }
            
            # Download attachments using the actual method
            downloaded_files = download_manager._download_with_proper_names(
                attachments, 'PO16518898', test_download_folder, False
            )
            
            print(f"\n📋 Download Results:")
            print(f"📁 Files downloaded: {len(downloaded_files)}")
            for filename in downloaded_files:
                file_path = os.path.join(test_download_folder, filename)
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    print(f"  📄 {filename} ({size} bytes)")
                else:
                    print(f"  ❌ {filename} (file not found)")
            
            # Check for duplicates
            if len(downloaded_files) == len(attachments):
                print(f"✅ Success! All {len(attachments)} attachments downloaded")
                if len(set(downloaded_files)) == len(downloaded_files):
                    print(f"✅ No duplicate filenames - counter suffix working correctly")
                else:
                    print(f"⚠️ Duplicate filenames detected - counter suffix may not be working")
            else:
                print(f"❌ Only {len(downloaded_files)} files downloaded out of {len(attachments)} attachments")
        
    finally:
        driver.quit()
        print("🔧 Browser closed")


if __name__ == "__main__":
    test_po16518898_download()
