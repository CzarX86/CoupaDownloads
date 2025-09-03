#!/usr/bin/env python3
"""
Simple debug script for PO16928033 attachment detection issue.
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Add the parallel_test module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'utils', 'parallel_test'))

from config import Config

def simple_debug_po16928033():
    """Simple debug for PO16928033 attachment detection."""
    print("🔍 Simple Debugging PO16928033 attachment detection...")
    
    # Setup Edge driver
    edge_driver_path = "drivers/msedgedriver"
    service = Service(edge_driver_path)
    
    # Configure Edge options (simpler)
    edge_options = webdriver.EdgeOptions()
    edge_options.add_experimental_option("prefs", {
        "download.default_directory": Config.DOWNLOAD_FOLDER,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
    })
    
    # Use existing profile
    edge_options.add_argument(f"--user-data-dir={Config.EDGE_PROFILE_DIR}")
    edge_options.add_argument(f"--profile-directory={Config.EDGE_PROFILE_NAME}")
    
    driver = None
    try:
        driver = webdriver.Edge(service=service, options=edge_options)
        print(f"✅ Browser initialized")
        
        # Navigate to PO16928033
        po_number = "16928033"
        url = f"{Config.BASE_URL}/order_headers/{po_number}"
        print(f"🌐 Navigating to: {url}")
        
        driver.get(url)
        time.sleep(8)  # Wait for page load
        
        # Print current URL
        current_url = driver.current_url
        print(f"📍 Current URL: {current_url}")
        
        # Check page source for error messages
        page_source = driver.page_source
        if "Oops! We couldn't find what you wanted" in page_source:
            print("❌ Error page detected!")
            return
        
        # Print page title
        print(f"📄 Page title: {driver.title}")
        
        # Save page source first
        with open("po16928033_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"💾 Page source saved to po16928033_debug.html")
        
        # Test current selector from config
        print(f"\n🎯 Testing current ATTACHMENT_SELECTOR: {Config.ATTACHMENT_SELECTOR}")
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
            print(f"   Found {len(elements)} elements with current selector")
            
            if elements:
                for i, elem in enumerate(elements):
                    try:
                        href = elem.get_attribute('href')
                        text = elem.text
                        title = elem.get_attribute('title')
                        aria_label = elem.get_attribute('aria-label')
                        print(f"   Element {i+1}: href='{href}', text='{text}', title='{title}', aria-label='{aria_label}'")
                    except Exception as e:
                        print(f"   Element {i+1}: Error getting attributes: {e}")
            else:
                print("   ❌ No elements found with current selector")
        except Exception as e:
            print(f"   ❌ Error with current selector: {e}")
        
        # Test specific selectors
        print(f"\n🔍 Testing specific selectors:")
        specific_selectors = [
            "div[class*='commentAttachments'] a",
            "div[class*='attachment'] a",
            "div[class*='file'] a",
            "div[class*='download'] a",
            "a[href*='attachment_file']",
            "a[href*='download']",
            "a[href*='attachment']",
            "span[class*='attachment']",
            "button[class*='attachment']",
            "[data-testid*='attachment']",
            "[data-testid*='download']",
            "[data-testid*='file']",
            # More generic selectors
            "a[href*='file']",
            "a[href*='doc']",
            "a[href*='pdf']",
            "a[href*='msg']",
            "a[href*='xlsx']",
            "a[href*='docx']",
        ]
        
        for selector in specific_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"   ✅ {selector}: {len(elements)} elements found")
                    for i, elem in enumerate(elements[:2]):  # Show first 2
                        try:
                            href = elem.get_attribute('href')
                            text = elem.text
                            title = elem.get_attribute('title')
                            aria_label = elem.get_attribute('aria-label')
                            print(f"      Element {i+1}: href='{href}', text='{text[:30]}...', title='{title}', aria-label='{aria_label}'")
                        except Exception as e:
                            print(f"      Element {i+1}: Error getting attributes: {e}")
                else:
                    print(f"   ❌ {selector}: No elements found")
            except Exception as e:
                print(f"   ❌ {selector}: Error - {e}")
        
        # Look for any elements with 'attachment' in class or attributes
        print(f"\n🔍 Searching for any attachment-related elements:")
        try:
            # Search by class containing 'attachment'
            attachment_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='attachment']")
            print(f"   Elements with 'attachment' in class: {len(attachment_elements)}")
            
            # Search by href containing 'attachment'
            href_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='attachment']")
            print(f"   Elements with 'attachment' in href: {len(href_elements)}")
            
            # Search by aria-label containing 'attachment'
            aria_elements = driver.find_elements(By.CSS_SELECTOR, "[aria-label*='attachment']")
            print(f"   Elements with 'attachment' in aria-label: {len(aria_elements)}")
            
            # Show details of first few elements
            for i, elem in enumerate(attachment_elements[:3]):
                try:
                    class_attr = elem.get_attribute('class')
                    href = elem.get_attribute('href')
                    text = elem.text
                    print(f"   Attachment element {i+1}: class='{class_attr}', href='{href}', text='{text}'")
                except Exception as e:
                    print(f"   Attachment element {i+1}: Error getting attributes: {e}")
                    
        except Exception as e:
            print(f"   ❌ Error searching for attachment elements: {e}")
        
        # Simple JavaScript analysis
        print(f"\n🔧 Simple JavaScript analysis:")
        try:
            # Count all links
            all_links = driver.execute_script("return document.querySelectorAll('a').length;")
            print(f"   Total links on page: {all_links}")
            
            # Count links with href containing 'attachment'
            attachment_links = driver.execute_script("return document.querySelectorAll('a[href*=\"attachment\"]').length;")
            print(f"   Links with 'attachment' in href: {attachment_links}")
            
            # Count links with href containing 'download'
            download_links = driver.execute_script("return document.querySelectorAll('a[href*=\"download\"]').length;")
            print(f"   Links with 'download' in href: {download_links}")
            
            # Count elements with 'attachment' in class
            attachment_class_elements = driver.execute_script("return document.querySelectorAll('[class*=\"attachment\"]').length;")
            print(f"   Elements with 'attachment' in class: {attachment_class_elements}")
            
            # Get first few links with attachment in href
            attachment_href_details = driver.execute_script("""
                const links = document.querySelectorAll('a[href*="attachment"]');
                const results = [];
                for (let i = 0; i < Math.min(links.length, 5); i++) {
                    const link = links[i];
                    results.push({
                        href: link.href,
                        text: link.textContent.trim(),
                        title: link.title,
                        ariaLabel: link.getAttribute('aria-label')
                    });
                }
                return results;
            """)
            
            if attachment_href_details:
                print(f"   📎 First {len(attachment_href_details)} links with 'attachment' in href:")
                for i, link in enumerate(attachment_href_details):
                    print(f"      Link {i+1}: href='{link['href']}', text='{link['text'][:50]}...'")
            
        except Exception as e:
            print(f"   ❌ Error during JavaScript analysis: {e}")
        
        print(f"\n✅ Debug analysis completed!")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
    finally:
        if driver:
            driver.quit()
            print("🔒 Browser closed")

if __name__ == "__main__":
    simple_debug_po16928033()
