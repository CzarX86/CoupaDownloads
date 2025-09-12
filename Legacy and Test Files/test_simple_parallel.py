#!/usr/bin/env python3
"""
Simple test to verify tab isolation in parallel processing.
"""

import os
import sys
import time
import pandas as pd

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add parallel_test to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from browser import BrowserManager
from downloader import Downloader
from download_control import DownloadControlManager
from excel_processor import ExcelProcessor


def test_simple_parallel():
    """Test simple parallel processing with specific POs."""
    print("🧪 Testing Simple Parallel Processing")
    print("=" * 50)
    
    # Initialize browser
    print("🚀 Initializing browser...")
    browser_manager = BrowserManager()
    
    # Ask user for download directory FIRST, before initializing browser
    print("\n📁 Download Directory Configuration:")
    user_directory = input("   Where to save CoupaDownloads folder? (Enter for default ~/Downloads): ").strip()
    
    if not user_directory:
        base_download_dir = os.path.expanduser("~/Downloads")
    else:
        base_download_dir = user_directory
    
    # Create the full CoupaDownloads path
    coupa_downloads_dir = os.path.join(base_download_dir, "CoupaDownloads")
    temp_download_dir = os.path.join(coupa_downloads_dir, "Temp")
    
    print(f"   📂 Base directory: {base_download_dir}")
    print(f"   📂 CoupaDownloads will be created at: {coupa_downloads_dir}")
    print(f"   📂 Temporary files will be saved at: {temp_download_dir}")
    
    # Ensure directories exist
    os.makedirs(temp_download_dir, exist_ok=True)
    
    # Initialize browser with the correct download directory
    browser_manager.initialize_driver_with_download_dir(temp_download_dir)
    
    # Initialize download control and Excel processor
    download_control = DownloadControlManager()
    excel_processor = ExcelProcessor()
    
    # Read POs from Excel file instead of hardcoded list
    print("📊 Reading POs from Excel file...")
    excel_path = excel_processor.get_excel_file_path()
    po_entries, _, _, _ = excel_processor.read_po_numbers_from_excel(excel_path)
    
    # Filter POs to process (only pending ones)
    pending_pos = [po for po in po_entries if po.get('status', 'Pending') == 'Pending' or pd.isna(po.get('status')) or po.get('status') == '']
    
    if not pending_pos:
        print("✅ All POs already processed")
        return
    
    print(f"📋 Found {len(pending_pos)} POs to process")
    
    # Process each PO in its own tab (create one at a time)
    print(f"\n🔍 Processing each PO in its own tab...")
    for i, po_data in enumerate(pending_pos):
        po_number = po_data['po_number']
        print(f"\n📋 Processing PO {i+1}/{len(pending_pos)}: {po_number}")
        
        # Create tab for this specific PO
        try:
            tab_handle = browser_manager.create_new_tab()
            
            if not tab_handle:
                print(f"   ❌ Failed to create tab for {po_number}")
                continue
        except Exception as e:
            print(f"   ❌ Error creating tab for {po_number}: {e}")
            # Try to create a new browser session if all tabs are closed
            try:
                print(f"   🔄 Attempting to restart browser session...")
                browser_manager.cleanup()
                browser_manager.initialize_driver_with_download_dir(temp_download_dir)
                tab_handle = browser_manager.create_new_tab()
                if not tab_handle:
                    print(f"   ❌ Failed to create tab after restart for {po_number}")
                    continue
            except Exception as restart_error:
                print(f"   ❌ Failed to restart browser: {restart_error}")
                continue
            
        print(f"   ✅ Created tab for {po_number}: {tab_handle}")
        
        # Create downloader for this tab
        downloader = Downloader(browser_manager.driver, browser_manager, download_control, temp_download_dir)
        
        # Process the PO with retry logic
        max_retries = 2
        success = False
        message = ""
        
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"   🔄 Retry attempt {attempt + 1}/{max_retries}")
                time.sleep(3)  # Wait before retry
            
            try:
                success, message = downloader.download_attachments_for_po(po_number, tab_handle, coupa_downloads_dir)
                
                if success:
                    print(f"   ✅ Success on attempt {attempt + 1}: {message}")
                    break
                else:
                    print(f"   ❌ Failed on attempt {attempt + 1}: {message}")
                    # If it's an access error (page not found), don't retry
                    if "PO not found or page error detected" in message:
                        print(f"   🚫 Access error detected, skipping retry")
                        break
            except Exception as e:
                print(f"   ❌ Exception on attempt {attempt + 1}: {e}")
                # If it's a window closed error, don't retry
                if "no such window" in str(e).lower():
                    print(f"   🚫 Window closed error detected, skipping retry")
                    break
                # For other exceptions, continue to retry
                continue
        
        # Update Excel with result
        try:
            excel_processor.update_po_status(
                po_number=po_number,
                status="Success" if success else "Error",
                error_message=message if not success else "",
                coupa_url=f"https://unilever.coupahost.com/order_headers/{po_number.replace('PO', '')}"
            )
            print(f"   📊 Excel updated for {po_number}")
        except Exception as e:
            print(f"   ⚠️ Failed to update Excel for {po_number}: {e}")
        
        # Close the tab after processing
        try:
            # Only close the tab if it's still open
            if tab_handle in browser_manager.driver.window_handles:
                browser_manager.driver.switch_to.window(tab_handle)
                browser_manager.driver.close()
                
                # Switch back to main tab
                if browser_manager.driver.window_handles:
                    browser_manager.driver.switch_to.window(browser_manager.driver.window_handles[0])
                
                print(f"   🔒 Tab closed for {po_number}")
            else:
                print(f"   ⚠️ Tab already closed for {po_number}")
        except Exception as e:
            print(f"   ⚠️ Error closing tab for {po_number}: {e}")
        
        # Brief wait between POs (no need to wait for download completion)
        time.sleep(1)
    
    # Show CSV results
    print("\n📊 CSV Control Results:")
    print("=" * 30)
    
    csv_file = download_control.get_csv_path()
    if os.path.exists(csv_file):
        with open(csv_file, 'r') as f:
            content = f.read()
            print(content)
    else:
        print("❌ CSV file not found")
    
    # Close browser
    print("\n🛑 Closing browser...")
    browser_manager.cleanup()
    print("✅ Test completed!")


if __name__ == "__main__":
    test_simple_parallel()
