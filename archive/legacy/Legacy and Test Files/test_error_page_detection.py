#!/usr/bin/env python3
"""
Test script to verify error page detection for "Oops! We couldn't find what you wanted."
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

def test_error_page_detection():
    """Test error page detection for POs that don't exist or have access denied."""
    print("🧪 Testing error page detection...")
    
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
        
        # Select 5 random POs to test
        selected_pos = random.sample(valid_pos, min(5, len(valid_pos)))
        print(f"🎲 Selected 5 random POs: {selected_pos}")
        
        # Check for login redirect first
        print("🔐 Checking login status...")
        test_url = Config.BASE_URL.format(selected_pos[0].replace("PO", "").replace("PM", ""))
        driver.get(test_url)
        
        if "login" in driver.current_url.lower() or "sign_in" in driver.current_url.lower():
            print("🔐 Login required - please log in manually and press Enter to continue...")
            input()
        
        # Test each PO for error page detection
        results = []
        for i, po_number in enumerate(selected_pos, 1):
            print(f"\n🔄 Testing PO {i}/5: {po_number}")
            
            try:
                # Navigate to PO page
                clean_po = po_number.replace("PO", "").replace("PM", "")
                po_url = Config.BASE_URL.format(clean_po)
                print(f"   🌐 Navigating to: {po_url}")
                driver.get(po_url)
                
                # Wait for page to load
                WebDriverWait(driver, Config.PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                print("   ✅ Page loaded")
                
                # Check for login redirect
                if "login" in driver.current_url.lower() or "sign_in" in driver.current_url.lower():
                    print("   🔐 Login required - please log in and press Enter...")
                    input()
                    driver.get(po_url)  # Navigate again after login
                
                # Check for error page
                page_text = driver.page_source.lower()
                title = driver.title.lower()
                
                error_detected = False
                error_type = None
                
                if "oops! we couldn't find what you wanted" in page_text:
                    error_detected = True
                    error_type = "NO_ACCESS"
                    print("   ❌ Error page detected: 'Oops! We couldn't find what you wanted'")
                elif "page not found" in title or "404" in title:
                    error_detected = True
                    error_type = "NO_ACCESS"
                    print("   ❌ Error page detected: Page not found (404)")
                else:
                    print("   ✅ No error page detected - PO appears to be accessible")
                
                # Store results
                result = {
                    'po_number': po_number,
                    'url': po_url,
                    'error_detected': error_detected,
                    'error_type': error_type,
                    'title': driver.title,
                    'page_contains_error': "oops! we couldn't find what you wanted" in page_text
                }
                results.append(result)
                
            except Exception as e:
                print(f"   ❌ Error testing {po_number}: {e}")
                results.append({
                    'po_number': po_number,
                    'url': po_url,
                    'error_detected': False,
                    'error_type': None,
                    'title': 'Error occurred',
                    'page_contains_error': False,
                    'error': str(e)
                })
        
        # Print summary
        print(f"\n📊 Error Page Detection Summary:")
        print(f"   Total POs tested: {len(results)}")
        error_pos = [r for r in results if r['error_detected']]
        print(f"   POs with access errors: {len(error_pos)}")
        print(f"   Accessible POs: {len(results) - len(error_pos)}")
        
        print(f"\n📋 Detailed Results:")
        for result in results:
            status = "❌" if result['error_detected'] else "✅"
            print(f"   {status} {result['po_number']}: {result['error_type'] if result['error_detected'] else 'Accessible'}")
            if result['error_detected']:
                print(f"      Title: {result['title']}")
                print(f"      Contains 'Oops' text: {result['page_contains_error']}")
        
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
    test_error_page_detection()
