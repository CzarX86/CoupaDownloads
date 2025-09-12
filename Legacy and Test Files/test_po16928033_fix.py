#!/usr/bin/env python3
"""
Test script to verify the PO16928033 fix.
"""

import os
import sys
import time
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

def test_po16928033_fix():
    """Test the fix for PO16928033 attachment detection."""
    print("🧪 Testing PO16928033 fix...")
    
    # Setup browser
    driver_manager = DriverManager()
    browser_manager = BrowserManager()
    
    try:
        # Initialize driver
        driver = browser_manager.initialize_driver()
        print("✅ Browser initialized")
        
        # Navigate to PO page
        po_url = Config.BASE_URL.format("16928033")
        print(f"🌐 Navigating to: {po_url}")
        driver.get(po_url)
        
        # Wait for page to load
        WebDriverWait(driver, Config.PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("✅ Page loaded")
        
        # Check for login redirect
        if "login" in driver.current_url.lower() or "sign_in" in driver.current_url.lower():
            print("🔐 Login required - please log in manually and press Enter to continue...")
            input()
        
        # Test the updated selector
        updated_selector = "div[class*='attachment'] a, span[aria-label*='file attachment'], span[role='button'][aria-label*='file attachment'], span[title*='.pdf'], span[title*='.docx'], span[title*='.msg']"
        
        print(f"🔍 Testing updated selector: {updated_selector}")
        
        # Wait for attachments
        try:
            WebDriverWait(driver, Config.ATTACHMENT_WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, updated_selector))
            )
            print("✅ Attachments found with updated selector")
        except TimeoutException:
            print("⚠️ No attachments found with updated selector")
        
        # Find attachments with updated selector
        attachments = driver.find_elements(By.CSS_SELECTOR, updated_selector)
        print(f"📎 Found {len(attachments)} attachments")
        
        # Test filename extraction for each attachment
        for i, attachment in enumerate(attachments):
            try:
                # Try different methods to get filename
                aria_label = attachment.get_attribute("aria-label")
                text_content = attachment.text
                title = attachment.get_attribute("title")
                href = attachment.get_attribute("href")
                
                print(f"\n📄 Attachment {i+1}:")
                print(f"   Tag: {attachment.tag_name}")
                print(f"   Text: '{text_content}'")
                print(f"   Aria-label: '{aria_label}'")
                print(f"   Title: '{title}'")
                print(f"   Href: '{href}'")
                
                # Determine the best filename source
                filename = None
                if text_content and text_content.strip():
                    filename = text_content.strip()
                elif aria_label and "file attachment" in aria_label:
                    filename = aria_label.split("file attachment")[0].strip()
                elif title:
                    filename = title
                elif href:
                    filename = os.path.basename(href)
                
                if filename:
                    print(f"   ✅ Extracted filename: '{filename}'")
                else:
                    print(f"   ❌ Could not extract filename")
                    
            except Exception as e:
                print(f"   ❌ Error processing attachment {i+1}: {e}")
        
        print(f"\n📋 Test Summary:")
        print(f"   Total attachments found: {len(attachments)}")
        if len(attachments) >= 2:
            print(f"   ✅ Successfully detected PO16928033 attachments")
        else:
            print(f"   ❌ Still missing attachments")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    test_po16928033_fix()
