#!/usr/bin/env python3
"""
Test script to verify the new improvements:
1. Page complete loading check
2. Download start confirmation
3. Status determination before folder creation
"""

import os
import sys
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import Config
from core.browser import BrowserManager
from core.driver_manager import DriverManager
from core.excel_processor import ExcelProcessor
from core.downloader import DownloadManager

def test_new_improvements():
    """Test the new improvements for robust download handling."""
    print("🧪 Testing new improvements for robust download handling...")
    
    # Setup browser
    driver_manager = DriverManager()
    browser_manager = BrowserManager()
    
    try:
        # Initialize driver
        driver = browser_manager.initialize_driver()
        print("✅ Browser initialized")
        
        # Read PO numbers from Excel
        excel_processor = ExcelProcessor()
        excel_file_path = excel_processor.get_excel_file_path()
        
        if not os.path.exists(excel_file_path):
            print(f"❌ Excel file not found: {excel_file_path}")
            return
        
        # Read PO numbers
        po_entries, original_cols, hierarchy_cols, has_hierarchy_data = excel_processor.read_po_numbers_from_excel(excel_file_path)
        valid_pos = [entry['po_number'] for entry in po_entries if entry['po_number']]
        
        if not valid_pos:
            print("❌ No valid PO numbers found in Excel file")
            return
        
        print(f"📋 Found {len(valid_pos)} valid POs in Excel file")
        
        # Select 3 random POs with attachments (based on previous test results)
        # We'll use POs that we know have attachments from previous tests
        known_pos_with_attachments = [
            'PO16832069',  # 1 attachment
            'PO15973679',  # 1 attachment  
            'PO16485957',  # 2 attachments (duplicates)
            'PO15911402',  # 3 attachments
            'PO16549980',  # 3 attachments
            'PO16370617',  # 6 attachments
            'PO16039221',  # 1 attachment
            'PO16815648',  # 1 attachment
            'PO16675134',  # 3 attachments
            'PO16750239'   # 4 attachments
        ]
        
        # Filter to only include POs that exist in our data
        available_pos = [po for po in known_pos_with_attachments if po in valid_pos]
        selected_pos = random.sample(available_pos, min(3, len(available_pos)))
        
        print(f"🎲 Selected 3 POs with known attachments: {selected_pos}")
        
        # Check for login redirect first
        print("🔐 Checking login status...")
        test_url = Config.BASE_URL.format(selected_pos[0].replace("PO", "").replace("PM", ""))
        driver.get(test_url)
        
        if "login" in driver.current_url.lower() or "sign_in" in driver.current_url.lower():
            print("🔐 Login required - please log in manually and press Enter to continue...")
            input()
        
        # Create download manager
        download_manager = DownloadManager(driver)
        
        # Test each PO with new improvements
        results = []
        for i, po_number in enumerate(selected_pos, 1):
            print(f"\n🔄 Testing PO {i}/3: {po_number}")
            
            try:
                # Create mock PO data
                po_data = {
                    'po_number': po_number,
                    'status': 'PENDING',
                    'supplier': f'Test_Supplier_{i}'
                }
                
                # Add hierarchy data if available
                if has_hierarchy_data:
                    for col in hierarchy_cols:
                        po_data[col] = f'Test_{col}_{i}'
                
                # Test the download process with new improvements
                clean_po = po_number.replace("PO", "").replace("PM", "")
                
                # Navigate to PO page
                po_url = Config.BASE_URL.format(clean_po)
                print(f"   🌐 Navigating to: {po_url}")
                driver.get(po_url)
                
                # Test page complete loading
                print("   ⏳ Testing page complete loading...")
                download_manager._wait_for_page_complete()
                print("   ✅ Page completely loaded")
                
                # Check for login redirect
                if "login" in driver.current_url.lower() or "sign_in" in driver.current_url.lower():
                    print("   🔐 Login required - please log in and press Enter...")
                    input()
                    driver.get(po_url)  # Navigate again after login
                
                # Find attachments
                print("   🔍 Finding attachments...")
                attachments = download_manager._find_attachments()
                attachments_found = len(attachments)
                print(f"   📎 Found {attachments_found} attachments")
                
                if not attachments:
                    print("   ⚠️ No attachments found - skipping download test")
                    results.append({
                        'po_number': po_number,
                        'attachments_found': 0,
                        'downloads_started': False,
                        'downloads_completed': False,
                        'final_status': 'NO_ATTACHMENTS',
                        'success': False
                    })
                    continue
                
                # Test download start confirmation
                print("   ⏳ Testing download start confirmation...")
                downloads_started = download_manager._wait_for_downloads_to_start(attachments)
                print(f"   {'✅' if downloads_started else '⚠️'} Downloads started: {downloads_started}")
                
                # Test download completion
                print("   ⏳ Testing download completion...")
                downloaded_files = download_manager._wait_for_downloads_complete(attachments)
                downloads_completed = len(downloaded_files) > 0
                print(f"   {'✅' if downloads_completed else '⚠️'} Downloads completed: {len(downloaded_files)} files")
                
                # Test status determination
                print("   🎯 Testing status determination...")
                final_status = download_manager._determine_final_status(attachments_found, downloaded_files)
                print(f"   📊 Final status: {final_status}")
                
                # Store results
                result = {
                    'po_number': po_number,
                    'attachments_found': attachments_found,
                    'downloads_started': downloads_started,
                    'downloads_completed': downloads_completed,
                    'downloaded_files': downloaded_files,
                    'final_status': final_status,
                    'success': downloads_completed
                }
                results.append(result)
                
            except Exception as e:
                print(f"   ❌ Error testing {po_number}: {e}")
                results.append({
                    'po_number': po_number,
                    'attachments_found': 0,
                    'downloads_started': False,
                    'downloads_completed': False,
                    'final_status': 'FAILED',
                    'success': False,
                    'error': str(e)
                })
        
        # Print summary
        print(f"\n📊 New Improvements Test Summary:")
        print(f"   Total POs tested: {len(results)}")
        successful_pos = [r for r in results if r['success']]
        print(f"   Successful downloads: {len(successful_pos)}")
        print(f"   Failed downloads: {len(results) - len(successful_pos)}")
        
        print(f"\n📋 Detailed Results:")
        for result in results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['po_number']}:")
            print(f"      Attachments found: {result['attachments_found']}")
            print(f"      Downloads started: {result['downloads_started']}")
            print(f"      Downloads completed: {result['downloads_completed']}")
            print(f"      Final status: {result['final_status']}")
            if result.get('downloaded_files'):
                print(f"      Downloaded files: {len(result['downloaded_files'])}")
        
        print(f"\n🔍 Browser will remain open for manual verification...")
        print(f"   Press Enter to close browser when done...")
        input()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if 'driver' in locals():
                driver.quit()
        except:
            pass

if __name__ == "__main__":
    test_new_improvements()
