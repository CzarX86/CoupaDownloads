#!/usr/bin/env python3
"""
Simple test to verify download process is working.
"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import Config
from core.browser import BrowserManager
from core.driver_manager import DriverManager
from core.downloader import DownloadManager

def test_simple_download():
    """Test simple download process."""
    print("🧪 Testing simple download process...")
    
    # Setup browser
    driver_manager = DriverManager()
    browser_manager = BrowserManager()
    
    try:
        # Initialize driver
        driver = browser_manager.initialize_driver()
        print("✅ Browser initialized")
        
        # Create download manager
        download_manager = DownloadManager(driver)
        
        # Test with a known PO that has attachments
        po_number = "PO16815648"
        clean_po = po_number.replace("PO", "").replace("PM", "")
        po_url = Config.BASE_URL.format(clean_po)
        
        print(f"🌐 Navigating to: {po_url}")
        driver.get(po_url)
        
        # Wait for page to load
        WebDriverWait(driver, Config.PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check for login redirect
        if "login" in driver.current_url.lower() or "sign_in" in driver.current_url.lower():
            print("🔐 Login required - please log in and press Enter...")
            input()
            driver.get(po_url)  # Navigate again after login
        
        # Find attachments
        print("🔍 Finding attachments...")
        attachments = download_manager._find_attachments()
        print(f"📎 Found {len(attachments)} attachments")
        
        if not attachments:
            print("❌ No attachments found")
            return
        
        # Test clicking the first attachment
        print("🖱️ Testing click on first attachment...")
        first_attachment = attachments[0]
        
        # Get filename
        filename = download_manager.extract_filename_from_element(first_attachment, 0)
        print(f"📄 Filename: {filename}")
        
        # Check if element is clickable
        print(f"🔍 Element enabled: {first_attachment.is_enabled()}")
        print(f"🔍 Element displayed: {first_attachment.is_displayed()}")
        
        # Try to click
        try:
            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView();", first_attachment)
            time.sleep(1)
            
            # Try regular click
            print("🖱️ Attempting regular click...")
            first_attachment.click()
            print("✅ Regular click successful!")
            
        except Exception as e:
            print(f"❌ Regular click failed: {e}")
            
            try:
                # Try JavaScript click
                print("🖱️ Attempting JavaScript click...")
                driver.execute_script("arguments[0].click();", first_attachment)
                print("✅ JavaScript click successful!")
                
            except Exception as e2:
                print(f"❌ JavaScript click also failed: {e2}")
        
        # Wait a bit to see if download starts
        print("⏳ Waiting 10 seconds to see if download starts...")
        import time
        time.sleep(10)
        
        # Check for downloads
        download_dir = Config.DOWNLOAD_FOLDER
        crdownload_files = [f for f in os.listdir(download_dir) if f.endswith('.crdownload')]
        downloaded_files = [f for f in os.listdir(download_dir) if any(f.lower().endswith(ext) for ext in Config.ALLOWED_EXTENSIONS)]
        
        print(f"📥 Downloads in progress: {len(crdownload_files)}")
        print(f"📥 Downloaded files: {len(downloaded_files)}")
        
        if crdownload_files:
            print(f"📥 Files downloading: {crdownload_files}")
        
        if downloaded_files:
            print(f"📥 Files downloaded: {downloaded_files}")
        
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
    test_simple_download()
