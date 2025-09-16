#!/usr/bin/env python3
"""
Test script to run 15 random POs and create a tab for each PO for manual verification.
Enhanced version with better browser session management.
"""

import os
import sys
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSessionIdException, NoSuchWindowException

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import Config
from core.browser import BrowserManager
from core.driver_manager import DriverManager
from core.excel_processor import ExcelProcessor

def test_15_random_pos():
    """Test 15 random POs and create a tab for each PO for manual verification."""
    print("🧪 Testing 15 random POs with separate tabs for verification...")
    
    # Setup browser
    driver_manager = DriverManager()
    browser_manager = BrowserManager()
    driver = None
    
    try:
        # Initialize driver with enhanced options
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
        
        # Select 15 random POs
        num_pos_to_test = min(15, len(valid_pos))
        selected_pos = random.sample(valid_pos, num_pos_to_test)
        print(f"🎲 Selected {num_pos_to_test} random POs: {selected_pos}")
        
        # Check for login redirect first
        print("🔐 Checking login status...")
        test_url = Config.BASE_URL.format(selected_pos[0].replace("PO", "").replace("PM", ""))
        
        try:
            driver.get(test_url)
            
            # Check if login is required
            if "login" in driver.current_url.lower() or "sign_in" in driver.current_url.lower():
                print("🔐 Login required - please log in manually and press Enter to continue...")
                input()
        except (NoSuchWindowException, InvalidSessionIdException) as e:
            print(f"⚠️ Browser window closed during login check: {e}")
            print("🔄 Reinitializing browser...")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            driver = browser_manager.initialize_driver()
            driver.get(test_url)
            if "login" in driver.current_url.lower() or "sign_in" in driver.current_url.lower():
                print("🔐 Login required - please log in manually and press Enter to continue...")
                input()
        
        # Store original window handle
        try:
            original_window = driver.current_window_handle
        except (NoSuchWindowException, InvalidSessionIdException):
            print("⚠️ Could not get original window handle, using first available...")
            original_window = driver.window_handles[0] if driver.window_handles else None
        
        # Test each PO in separate tabs
        results = []
        for i, po_number in enumerate(selected_pos, 1):
            print(f"\n🔄 Testing PO {i}/{num_pos_to_test}: {po_number}")
            
            try:
                # Check if session is still valid
                try:
                    driver.current_url
                except (InvalidSessionIdException, NoSuchWindowException):
                    print("   ⚠️ Browser session expired, reinitializing...")
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                    driver = browser_manager.initialize_driver()
                    # Re-login if needed
                    driver.get(test_url)
                    if "login" in driver.current_url.lower() or "sign_in" in driver.current_url.lower():
                        print("   🔐 Login required again - please log in and press Enter...")
                        input()
                    original_window = driver.current_window_handle
                
                # Create new tab for this PO
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[-1])
                
                # Navigate to PO page
                clean_po = po_number.replace("PO", "").replace("PM", "")
                po_url = Config.BASE_URL.format(clean_po)
                print(f"   🌐 Opening new tab: {po_url}")
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
                
                # Wait for attachments with enhanced timeout
                print("   ⏳ Waiting for attachments to load...")
                try:
                    WebDriverWait(driver, 15).until(  # Increased timeout
                        EC.presence_of_element_located((By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR))
                    )
                    print("   ✅ Attachments found with selector")
                except TimeoutException:
                    print("   ⚠️ No attachments found with selector")
                
                # Find attachments
                attachments = driver.find_elements(By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
                print(f"   📎 Found {len(attachments)} attachments")
                
                # Test filename extraction for each attachment
                filenames = []
                for j, attachment in enumerate(attachments):
                    try:
                        # Try different methods to get filename
                        aria_label = attachment.get_attribute("aria-label")
                        text_content = attachment.text.strip()
                        href = attachment.get_attribute("href")
                        title = attachment.get_attribute("title")
                        tag_name = attachment.tag_name
                        
                        # Determine the best filename source
                        filename = None
                        if text_content and any(ext in text_content.lower() for ext in ['.pdf', '.docx', '.msg', '.xlsx', '.txt', '.jpg', '.png', '.zip', '.rar', '.csv', '.xml']):
                            filename = text_content
                        elif aria_label and "file attachment" in aria_label:
                            filename = aria_label.split("file attachment")[0].strip()
                        elif title:
                            filename = title
                        elif href:
                            filename = os.path.basename(href)
                        
                        if filename:
                            filenames.append(filename)
                            print(f"     📄 Attachment {j+1}: '{filename}' (tag: {tag_name})")
                        else:
                            print(f"     ❌ Attachment {j+1}: Could not extract filename")
                            
                    except Exception as e:
                        print(f"     ❌ Error processing attachment {j+1}: {e}")
                
                # Store results
                result = {
                    'po_number': po_number,
                    'url': po_url,
                    'attachments_found': len(attachments),
                    'filenames': filenames,
                    'success': len(attachments) > 0,
                    'tab_index': i
                }
                results.append(result)
                
                print(f"   📋 Result: {len(attachments)} attachments found")
                print(f"   📑 Tab {i} ready for inspection")
                
                # Small delay between POs to prevent overwhelming the browser
                time.sleep(1)
                
            except (WebDriverException, NoSuchWindowException, InvalidSessionIdException) as e:
                print(f"   ❌ Browser error testing {po_number}: {e}")
                results.append({
                    'po_number': po_number,
                    'url': po_url,
                    'attachments_found': 0,
                    'filenames': [],
                    'success': False,
                    'error': str(e),
                    'tab_index': i
                })
            except Exception as e:
                print(f"   ❌ Error testing {po_number}: {e}")
                results.append({
                    'po_number': po_number,
                    'url': po_url,
                    'attachments_found': 0,
                    'filenames': [],
                    'success': False,
                    'error': str(e),
                    'tab_index': i
                })
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"   Total POs tested: {len(results)}")
        successful_pos = [r for r in results if r['success']]
        print(f"   Successful detections: {len(successful_pos)}")
        print(f"   Failed detections: {len(results) - len(successful_pos)}")
        
        print(f"\n📋 Detailed Results:")
        for result in results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} Tab {result['tab_index']} - {result['po_number']}: {result['attachments_found']} attachments")
            if result['filenames']:
                for filename in result['filenames']:
                    print(f"      📄 {filename}")
        
        # Try to switch back to first tab and keep all tabs open for manual verification
        try:
            if original_window and original_window in driver.window_handles:
                driver.switch_to.window(original_window)
            print(f"\n🔍 All tabs are open for manual verification...")
            for i, po in enumerate(selected_pos, 1):
                print(f"   Tab {i}: {po}")
            print(f"   Press Enter to close browser when done...")
            input()
        except Exception as e:
            print(f"⚠️ Could not switch back to original window: {e}")
            print(f"🔍 Browser tabs are still open for manual verification...")
            print(f"   Press Enter to close browser when done...")
            input()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if driver:
                driver.quit()
        except:
            pass

if __name__ == "__main__":
    test_15_random_pos()
