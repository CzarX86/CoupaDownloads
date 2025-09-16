#!/usr/bin/env python3
"""
Diagnostic script to investigate PO16928033 attachment detection issues.
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

def investigate_po16928033():
    """Investigate why PO16928033 attachments are not being detected."""
    print("🔍 Investigating PO16928033 attachment detection...")
    
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
        
        # Wait for attachments with longer timeout
        print("⏳ Waiting for attachments to load...")
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
                )
            )
            print("✅ Attachments found with original selector")
        except TimeoutException:
            print("⚠️ No attachments found with original selector, trying alternative selectors...")
        
        # Try multiple selectors
        selectors_to_try = [
            Config.ATTACHMENT_SELECTOR,
            "span[aria-label*='file attachment']",
            "span[role='button'][aria-label*='file attachment']",
            "span[title*='.pdf']",
            "span[title*='.docx']",
            "span[title*='.msg']",
            "a[href*='download']",
            "button[aria-label*='file']",
            "div[role='button'][aria-label*='file']",
            "span[class*='attachment']",
            "div[class*='attachment']",
            "a[download]",
            "span[aria-label*='download']",
            "button[aria-label*='download']"
        ]
        
        attachments_found = []
        for i, selector in enumerate(selectors_to_try):
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✅ Selector {i+1} found {len(elements)} elements: {selector}")
                    for j, elem in enumerate(elements[:3]):  # Show first 3
                        aria_label = elem.get_attribute("aria-label")
                        title = elem.get_attribute("title")
                        role = elem.get_attribute("role")
                        class_name = elem.get_attribute("class")
                        print(f"   Element {j+1}: aria-label='{aria_label}', title='{title}', role='{role}', class='{class_name}'")
                    attachments_found.extend(elements)
                else:
                    print(f"❌ Selector {i+1} found 0 elements: {selector}")
            except Exception as e:
                print(f"❌ Selector {i+1} error: {e}")
        
        # Analyze page structure
        print(f"\n📊 Page Analysis:")
        print(f"   Page title: {driver.title}")
        print(f"   Current URL: {driver.current_url}")
        
        # Look for any file-related elements
        print(f"\n🔍 Looking for any file-related elements...")
        
        # Check for common file indicators
        page_source = driver.page_source.lower()
        file_indicators = ['pdf', 'docx', 'msg', 'xlsx', 'download', 'attachment', 'file']
        for indicator in file_indicators:
            if indicator in page_source:
                print(f"   ✅ Found '{indicator}' in page source")
        
        # Try to find elements by text content
        print(f"\n🔍 Searching for elements with file-related text...")
        try:
            # Look for elements containing file extensions
            file_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '.pdf') or contains(text(), '.docx') or contains(text(), '.msg')]")
            if file_elements:
                print(f"✅ Found {len(file_elements)} elements with file extensions in text")
                for i, elem in enumerate(file_elements[:5]):  # Show first 5
                    print(f"   Element {i+1}: {elem.tag_name} - '{elem.text[:100]}...'")
        except Exception as e:
            print(f"❌ Error searching for file elements: {e}")
        
        # Check for iframes
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            print(f"\n⚠️ Found {len(iframes)} iframes - attachments might be in an iframe")
            for i, iframe in enumerate(iframes):
                try:
                    driver.switch_to.frame(iframe)
                    iframe_attachments = driver.find_elements(By.CSS_SELECTOR, "span[aria-label*='file']")
                    if iframe_attachments:
                        print(f"   ✅ Found {len(iframe_attachments)} attachments in iframe {i+1}")
                    driver.switch_to.default_content()
                except Exception as e:
                    print(f"   ❌ Error checking iframe {i+1}: {e}")
                    driver.switch_to.default_content()
        
        # Summary
        print(f"\n📋 Summary:")
        print(f"   Total attachments found: {len(attachments_found)}")
        if attachments_found:
            print(f"   ✅ Attachments detected successfully")
        else:
            print(f"   ❌ No attachments detected - page structure may have changed")
            print(f"   💡 Consider updating CSS selectors or checking if attachments are in a different location")
        
        # Take screenshot for manual inspection
        screenshot_path = "po16928033_investigation.png"
        driver.save_screenshot(screenshot_path)
        print(f"📸 Screenshot saved: {screenshot_path}")
        
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    investigate_po16928033()
