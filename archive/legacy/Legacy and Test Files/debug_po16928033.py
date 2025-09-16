#!/usr/bin/env python3
"""
Debug script for PO16928033 attachment detection issue.
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

def debug_po16928033():
    """Debug PO16928033 attachment detection."""
    print("🔍 Debugging PO16928033 attachment detection...")
    
    # Setup Edge driver
    edge_driver_path = "drivers/msedgedriver"
    service = Service(edge_driver_path)
    
    # Configure Edge options
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
    
    # Enable DevTools
    edge_options.add_argument("--auto-open-devtools-for-tabs")
    edge_options.add_argument("--disable-web-security")
    edge_options.add_argument("--allow-running-insecure-content")
    
    driver = None
    try:
        driver = webdriver.Edge(service=service, options=edge_options)
        print(f"✅ Browser initialized")
        
        # Navigate to PO16928033
        po_number = "16928033"
        url = f"{Config.BASE_URL}/order_headers/{po_number}"
        print(f"🌐 Navigating to: {url}")
        
        driver.get(url)
        time.sleep(5)  # Wait for page load
        
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
        
        # Wait longer for page to fully load
        print("⏳ Waiting for page to fully load...")
        time.sleep(10)
        
        # Check if page is still loading
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            print("✅ Page fully loaded")
        except TimeoutException:
            print("⚠️ Page load timeout, continuing anyway...")
        
        # Test different selectors
        selectors_to_test = [
            "div[class*='attachment'] a[href*='attachment_file']",
            "div[class*='attachment'] a[href*='download']", 
            "div[class*='attachment'] a[href*='attachment']",
            "span[aria-label*='file attachment']",
            "span[role='button'][aria-label*='file attachment']",
            "span[title*='.pdf']",
            "span[title*='.docx']",
            "span[title*='.msg']",
            # More specific selectors
            "div[class*='commentAttachments'] a",
            "div[class*='attachment'] a",
            "a[href*='attachment_file']",
            "a[href*='download']",
            # Generic attachment elements
            "div[class*='attachment']",
            "[class*='attachment']",
        ]
        
        print("\n🔍 Testing different selectors:")
        for i, selector in enumerate(selectors_to_test, 1):
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"   {i:2d}. {selector}: {len(elements)} elements found")
                
                if elements:
                    for j, elem in enumerate(elements[:3]):  # Show first 3
                        try:
                            href = elem.get_attribute('href')
                            text = elem.text
                            title = elem.get_attribute('title')
                            aria_label = elem.get_attribute('aria-label')
                            print(f"      Element {j+1}: href='{href}', text='{text}', title='{title}', aria-label='{aria_label}'")
                        except Exception as e:
                            print(f"      Element {j+1}: Error getting attributes: {e}")
            except Exception as e:
                print(f"   {i:2d}. {selector}: Error - {e}")
        
        # Test the current selector from config
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
        
        # Save page source for manual inspection
        with open("po16928033_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"\n💾 Page source saved to po16928033_debug.html for manual inspection")
        
        # Advanced DOM analysis using JavaScript
        print(f"\n🔍 Advanced DOM Analysis:")
        
        # Execute JavaScript to find all elements with attachment-related attributes
        js_analysis = """
        function analyzePage() {
            const results = {
                elementsWithAttachmentClass: [],
                elementsWithAttachmentHref: [],
                elementsWithAttachmentAriaLabel: [],
                elementsWithAttachmentTitle: [],
                allLinks: [],
                allButtons: [],
                allSpans: [],
                allDivs: []
            };
            
            // Find elements with 'attachment' in class
            const attachmentClassElements = document.querySelectorAll('[class*="attachment"]');
            attachmentClassElements.forEach((el, index) => {
                results.elementsWithAttachmentClass.push({
                    tagName: el.tagName,
                    className: el.className,
                    href: el.href || null,
                    text: el.textContent?.trim() || '',
                    title: el.title || null,
                    ariaLabel: el.getAttribute('aria-label') || null,
                    id: el.id || null,
                    index: index
                });
            });
            
            // Find elements with 'attachment' in href
            const attachmentHrefElements = document.querySelectorAll('a[href*="attachment"]');
            attachmentHrefElements.forEach((el, index) => {
                results.elementsWithAttachmentHref.push({
                    tagName: el.tagName,
                    className: el.className,
                    href: el.href,
                    text: el.textContent?.trim() || '',
                    title: el.title || null,
                    ariaLabel: el.getAttribute('aria-label') || null,
                    id: el.id || null,
                    index: index
                });
            });
            
            // Find elements with 'attachment' in aria-label
            const attachmentAriaElements = document.querySelectorAll('[aria-label*="attachment"]');
            attachmentAriaElements.forEach((el, index) => {
                results.elementsWithAttachmentAriaLabel.push({
                    tagName: el.tagName,
                    className: el.className,
                    href: el.href || null,
                    text: el.textContent?.trim() || '',
                    title: el.title || null,
                    ariaLabel: el.getAttribute('aria-label'),
                    id: el.id || null,
                    index: index
                });
            });
            
            // Find elements with 'attachment' in title
            const attachmentTitleElements = document.querySelectorAll('[title*="attachment"]');
            attachmentTitleElements.forEach((el, index) => {
                results.elementsWithAttachmentTitle.push({
                    tagName: el.tagName,
                    className: el.className,
                    href: el.href || null,
                    text: el.textContent?.trim() || '',
                    title: el.title,
                    ariaLabel: el.getAttribute('aria-label') || null,
                    id: el.id || null,
                    index: index
                });
            });
            
            // Find all links
            const allLinks = document.querySelectorAll('a');
            allLinks.forEach((el, index) => {
                if (el.href && el.href.includes('download') || el.href.includes('attachment')) {
                    results.allLinks.push({
                        tagName: el.tagName,
                        className: el.className,
                        href: el.href,
                        text: el.textContent?.trim() || '',
                        title: el.title || null,
                        ariaLabel: el.getAttribute('aria-label') || null,
                        id: el.id || null,
                        index: index
                    });
                }
            });
            
            // Find all buttons
            const allButtons = document.querySelectorAll('button');
            allButtons.forEach((el, index) => {
                if (el.textContent?.includes('download') || el.textContent?.includes('attachment') || 
                    el.getAttribute('aria-label')?.includes('attachment') || el.title?.includes('attachment')) {
                    results.allButtons.push({
                        tagName: el.tagName,
                        className: el.className,
                        text: el.textContent?.trim() || '',
                        title: el.title || null,
                        ariaLabel: el.getAttribute('aria-label') || null,
                        id: el.id || null,
                        index: index
                    });
                }
            });
            
            // Find all spans
            const allSpans = document.querySelectorAll('span');
            allSpans.forEach((el, index) => {
                if (el.textContent?.includes('download') || el.textContent?.includes('attachment') || 
                    el.getAttribute('aria-label')?.includes('attachment') || el.title?.includes('attachment')) {
                    results.allSpans.push({
                        tagName: el.tagName,
                        className: el.className,
                        text: el.textContent?.trim() || '',
                        title: el.title || null,
                        ariaLabel: el.getAttribute('aria-label') || null,
                        id: el.id || null,
                        index: index
                    });
                }
            });
            
            // Find all divs with attachment-related content
            const allDivs = document.querySelectorAll('div');
            allDivs.forEach((el, index) => {
                if (el.textContent?.includes('download') || el.textContent?.includes('attachment') || 
                    el.className?.includes('attachment')) {
                    results.allDivs.push({
                        tagName: el.tagName,
                        className: el.className,
                        text: el.textContent?.trim() || '',
                        title: el.title || null,
                        ariaLabel: el.getAttribute('aria-label') || null,
                        id: el.id || null,
                        index: index
                    });
                }
            });
            
            return results;
        }
        return analyzePage();
        """
        
        try:
            analysis_results = driver.execute_script(js_analysis)
            
            print(f"   📎 Elements with 'attachment' in class: {len(analysis_results['elementsWithAttachmentClass'])}")
            for elem in analysis_results['elementsWithAttachmentClass'][:5]:  # Show first 5
                print(f"      - {elem['tagName']}: class='{elem['className']}', href='{elem['href']}', text='{elem['text'][:50]}...'")
            
            print(f"   🔗 Elements with 'attachment' in href: {len(analysis_results['elementsWithAttachmentHref'])}")
            for elem in analysis_results['elementsWithAttachmentHref'][:5]:
                print(f"      - {elem['tagName']}: href='{elem['href']}', text='{elem['text'][:50]}...'")
            
            print(f"   🏷️ Elements with 'attachment' in aria-label: {len(analysis_results['elementsWithAttachmentAriaLabel'])}")
            for elem in analysis_results['elementsWithAttachmentAriaLabel'][:5]:
                print(f"      - {elem['tagName']}: aria-label='{elem['ariaLabel']}', text='{elem['text'][:50]}...'")
            
            print(f"   📄 Elements with 'attachment' in title: {len(analysis_results['elementsWithAttachmentTitle'])}")
            for elem in analysis_results['elementsWithAttachmentTitle'][:5]:
                print(f"      - {elem['tagName']}: title='{elem['title']}', text='{elem['text'][:50]}...'")
            
            print(f"   🔗 All links with download/attachment: {len(analysis_results['allLinks'])}")
            for elem in analysis_results['allLinks'][:5]:
                print(f"      - {elem['tagName']}: href='{elem['href']}', text='{elem['text'][:50]}...'")
            
            print(f"   🔘 Buttons with attachment-related content: {len(analysis_results['allButtons'])}")
            for elem in analysis_results['allButtons'][:5]:
                print(f"      - {elem['tagName']}: text='{elem['text'][:50]}...', aria-label='{elem['ariaLabel']}'")
            
            print(f"   📝 Spans with attachment-related content: {len(analysis_results['allSpans'])}")
            for elem in analysis_results['allSpans'][:5]:
                print(f"      - {elem['tagName']}: text='{elem['text'][:50]}...', aria-label='{elem['ariaLabel']}'")
            
            print(f"   📦 Divs with attachment-related content: {len(analysis_results['allDivs'])}")
            for elem in analysis_results['allDivs'][:5]:
                print(f"      - {elem['tagName']}: class='{elem['className']}', text='{elem['text'][:50]}...'")
            
            # Save detailed analysis to JSON file
            import json
            with open("po16928033_analysis.json", "w", encoding="utf-8") as f:
                json.dump(analysis_results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Detailed analysis saved to po16928033_analysis.json")
            
        except Exception as e:
            print(f"   ❌ Error during JavaScript analysis: {e}")
        
        # Test specific selectors that might work
        print(f"\n🎯 Testing specific selectors for PO16928033:")
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
        ]
        
        for selector in specific_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"   ✅ {selector}: {len(elements)} elements found")
                    for i, elem in enumerate(elements[:3]):
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
        
        # Execute JavaScript to analyze page structure
        print(f"\n🔧 Executing JavaScript analysis...")
        js_analysis = driver.execute_script("""
            // Find all elements with 'attachment' in their attributes
            const attachmentElements = [];
            
            // Search by class name
            const classElements = document.querySelectorAll('[class*="attachment"]');
            classElements.forEach(el => {
                attachmentElements.push({
                    tag: el.tagName,
                    class: el.className,
                    href: el.href || '',
                    text: el.textContent?.trim() || '',
                    title: el.title || '',
                    'aria-label': el.getAttribute('aria-label') || '',
                    id: el.id || '',
                    'data-testid': el.getAttribute('data-testid') || ''
                });
            });
            
            // Search by href
            const hrefElements = document.querySelectorAll('a[href*="attachment"]');
            hrefElements.forEach(el => {
                if (!attachmentElements.find(item => item.href === el.href)) {
                    attachmentElements.push({
                        tag: el.tagName,
                        class: el.className,
                        href: el.href || '',
                        text: el.textContent?.trim() || '',
                        title: el.title || '',
                        'aria-label': el.getAttribute('aria-label') || '',
                        id: el.id || '',
                        'data-testid': el.getAttribute('data-testid') || ''
                    });
                }
            });
            
            // Search by aria-label
            const ariaElements = document.querySelectorAll('[aria-label*="attachment"]');
            ariaElements.forEach(el => {
                if (!attachmentElements.find(item => item.href === el.href)) {
                    attachmentElements.push({
                        tag: el.tagName,
                        class: el.className,
                        href: el.href || '',
                        text: el.textContent?.trim() || '',
                        title: el.title || '',
                        'aria-label': el.getAttribute('aria-label') || '',
                        id: el.id || '',
                        'data-testid': el.getAttribute('data-testid') || ''
                    });
                }
            });
            
            // Search by text content containing file extensions
            const fileElements = document.querySelectorAll('a[href*=".pdf"], a[href*=".docx"], a[href*=".msg"], a[href*=".xlsx"]');
            fileElements.forEach(el => {
                if (!attachmentElements.find(item => item.href === el.href)) {
                    attachmentElements.push({
                        tag: el.tagName,
                        class: el.className,
                        href: el.href || '',
                        text: el.textContent?.trim() || '',
                        title: el.title || '',
                        'aria-label': el.getAttribute('aria-label') || '',
                        id: el.id || '',
                        'data-testid': el.getAttribute('data-testid') || ''
                    });
                }
            });
            
            return {
                totalElements: attachmentElements.length,
                elements: attachmentElements,
                pageTitle: document.title,
                url: window.location.href,
                bodyClasses: document.body.className,
                // Get all script tags to see if there's dynamic content
                scriptCount: document.querySelectorAll('script').length,
                // Check for any iframes
                iframeCount: document.querySelectorAll('iframe').length,
                // Check for any shadow roots
                shadowRoots: Array.from(document.querySelectorAll('*')).filter(el => el.shadowRoot).length
            };
        """)
        
        print(f"📊 JavaScript Analysis Results:")
        print(f"   Total attachment-related elements: {js_analysis['totalElements']}")
        print(f"   Script tags: {js_analysis['scriptCount']}")
        print(f"   Iframes: {js_analysis['iframeCount']}")
        print(f"   Shadow roots: {js_analysis['shadowRoots']}")
        print(f"   Body classes: {js_analysis['bodyClasses']}")
        
        if js_analysis['elements']:
            print(f"\n📎 Found attachment elements:")
            for i, elem in enumerate(js_analysis['elements'][:10]):  # Show first 10
                print(f"   {i+1:2d}. {elem['tag']} | class='{elem['class']}' | href='{elem['href']}' | text='{elem['text']}' | aria-label='{elem['aria-label']}'")
        else:
            print(f"   ❌ No attachment elements found via JavaScript")
        
        # Wait for manual inspection
        print(f"\n⏸️  Browser will stay open for 60 seconds for manual inspection...")
        print(f"   💡 You can now use DevTools to inspect the page manually")
        print(f"   💡 Look for elements with 'attachment' in class names or href attributes")
        print(f"   💡 Check the Console tab for any JavaScript errors")
        print(f"   💡 Check the Elements tab to inspect the DOM structure")
        
        time.sleep(60)  # Keep browser open for 60 seconds
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
    finally:
        if driver:
            driver.quit()
            print("🔒 Browser closed")

if __name__ == "__main__":
    debug_po16928033()
