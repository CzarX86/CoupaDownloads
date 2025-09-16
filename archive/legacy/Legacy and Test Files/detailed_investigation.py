#!/usr/bin/env python3
"""
Detailed investigation of PO16928033 attachment structure.
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

def detailed_investigation():
    """Detailed investigation of PO16928033 attachment structure."""
    print("🔍 Detailed investigation of PO16928033...")
    
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
        
        # Wait longer for dynamic content
        print("⏳ Waiting for dynamic content to load...")
        time.sleep(5)
        
        # Find all div elements with 'attachment' in class
        attachment_divs = driver.find_elements(By.CSS_SELECTOR, "div[class*='attachment']")
        print(f"📁 Found {len(attachment_divs)} div elements with 'attachment' in class")
        
        for i, div in enumerate(attachment_divs):
            print(f"\n📄 Attachment div {i+1}:")
            print(f"   Class: '{div.get_attribute('class')}'")
            print(f"   Text: '{div.text[:200]}...'")
            
            # Look for <a> tags inside this div
            links = div.find_elements(By.TAG_NAME, "a")
            print(f"   Links found: {len(links)}")
            
            for j, link in enumerate(links):
                print(f"     Link {j+1}:")
                print(f"       Text: '{link.text}'")
                print(f"       Href: '{link.get_attribute('href')}'")
                print(f"       Class: '{link.get_attribute('class')}'")
                print(f"       Aria-label: '{link.get_attribute('aria-label')}'")
                print(f"       Title: '{link.get_attribute('title')}'")
                
                # Check if this link is clickable
                try:
                    if link.is_displayed() and link.is_enabled():
                        print(f"       ✅ Clickable")
                    else:
                        print(f"       ❌ Not clickable (displayed: {link.is_displayed()}, enabled: {link.is_enabled()})")
                except Exception as e:
                    print(f"       ❌ Error checking clickability: {e}")
        
        # Try to find the specific PDF links directly
        print(f"\n🔍 Looking for PDF links directly...")
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(text(), '.pdf')]")
        print(f"📎 Found {len(pdf_links)} PDF links directly")
        
        for i, link in enumerate(pdf_links):
            print(f"   PDF Link {i+1}: '{link.text}'")
            print(f"     Parent: {link.find_element(By.XPATH, '..').tag_name}")
            print(f"     Parent class: '{link.find_element(By.XPATH, '..').get_attribute('class')}'")
        
        # Try different selectors
        print(f"\n🔍 Testing different selectors...")
        
        selectors_to_test = [
            "div[class*='attachment'] a",
            "div.attachments a",
            "div.attachmentsField a",
            "a[href*='download']",
            "a[href*='.pdf']",
            "a[href*='.docx']",
            "a[href*='.msg']",
            "a:contains('.pdf')",
            "a:contains('.docx')",
            "a:contains('.msg')"
        ]
        
        for selector in selectors_to_test:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"   '{selector}': {len(elements)} elements")
            except Exception as e:
                print(f"   '{selector}': Error - {e}")
        
        # Check if elements are in shadow DOM or iframes
        print(f"\n🔍 Checking for shadow DOM or iframes...")
        
        # Check for shadow DOM
        shadow_hosts = driver.find_elements(By.CSS_SELECTOR, "*")
        shadow_count = 0
        for host in shadow_hosts:
            try:
                shadow_root = driver.execute_script("return arguments[0].shadowRoot", host)
                if shadow_root:
                    shadow_count += 1
                    print(f"   Found shadow DOM in {host.tag_name}")
            except:
                pass
        
        if shadow_count == 0:
            print("   No shadow DOM found")
        
        # Check for iframes
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"   Found {len(iframes)} iframes")
        
        for i, iframe in enumerate(iframes):
            try:
                driver.switch_to.frame(iframe)
                iframe_links = driver.find_elements(By.TAG_NAME, "a")
                iframe_pdf_links = [link for link in iframe_links if '.pdf' in link.text.lower()]
                print(f"     Iframe {i+1}: {len(iframe_links)} links, {len(iframe_pdf_links)} PDF links")
                driver.switch_to.default_content()
            except Exception as e:
                print(f"     Iframe {i+1}: Error - {e}")
                driver.switch_to.default_content()
        
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    detailed_investigation()
