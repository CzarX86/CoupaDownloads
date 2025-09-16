#!/usr/bin/env python3
"""
Test script to verify tab isolation and check if different POs have different attachments.
"""

import os
import sys
import time

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add parallel_test to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from browser import BrowserManager
from downloader import Downloader


def test_po_isolation():
    """Test if different POs have different attachments and if tabs are isolated."""
    print("🧪 Testing PO Isolation and Tab Context")
    print("=" * 60)
    
    # Initialize browser
    print("🚀 Initializing browser...")
    browser_manager = BrowserManager()
    browser_manager.initialize_driver()
    
    # Test POs
    test_pos = ["PO16928033", "PO16518898", "PO16229343"]
    
    # Store tab handles
    tab_handles = {}
    
    # Create tabs for each PO
    print("\n📋 Creating tabs for each PO...")
    for po_number in test_pos:
        # Create tab with download directory
        download_folder = f"/Users/juliocezar/Downloads/CoupaDownloads/{po_number}_Test"
        tab_handle = browser_manager.create_tab_with_download_dir(download_folder)
        
        if tab_handle:
            tab_handles[po_number] = tab_handle
            print(f"   ✅ Created tab for {po_number}: {tab_handle}")
        else:
            print(f"   ❌ Failed to create tab for {po_number}")
    
    # Test each PO in its own tab
    print("\n🔍 Testing each PO in its own tab...")
    for po_number in test_pos:
        if po_number not in tab_handles:
            continue
            
        print(f"\n📋 Testing PO: {po_number}")
        print(f"   🔄 Switching to tab: {tab_handles[po_number]}")
        
        # Switch to the specific tab
        browser_manager.driver.switch_to.window(tab_handles[po_number])
        
        # Create downloader for this tab
        downloader = Downloader(browser_manager.driver, browser_manager)
        
        # Navigate to PO page
        order_number = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
        url = f"https://unilever.coupahost.com/order_headers/{order_number}"
        print(f"   🌐 Navigating to: {url}")
        
        browser_manager.driver.get(url)
        
        # Wait for page to load
        time.sleep(3)
        
        # Check current URL to verify we're on the right page
        current_url = browser_manager.driver.current_url
        print(f"   📍 Current URL: {current_url}")
        
        # Find attachments
        attachments = downloader._find_attachments()
        
        if attachments:
            print(f"   📎 Found {len(attachments)} attachments:")
            unique_filenames = set()
            for i, attachment in enumerate(attachments):
                filename = downloader._extract_filename_from_element(attachment)
                if filename:
                    unique_filenames.add(filename)
                    print(f"      {i+1}. {filename}")
                else:
                    print(f"      {i+1}. <filename not found>")
            
            print(f"   📎 Unique filenames: {list(unique_filenames)}")
        else:
            print("   ❌ No attachments found")
        
        # Wait between POs
        time.sleep(2)
    
    # Test tab isolation by checking URLs in each tab
    print("\n🔍 Verifying tab isolation...")
    for po_number in test_pos:
        if po_number not in tab_handles:
            continue
            
        print(f"\n📋 Checking tab for {po_number}:")
        
        # Switch to tab
        browser_manager.driver.switch_to.window(tab_handles[po_number])
        
        # Check URL
        current_url = browser_manager.driver.current_url
        print(f"   📍 Tab URL: {current_url}")
        
        # Check if we're on the right PO page
        expected_order = po_number.replace("PO", "")
        if expected_order in current_url:
            print(f"   ✅ Tab correctly shows {po_number}")
        else:
            print(f"   ❌ Tab shows wrong PO! Expected {po_number}, got: {current_url}")
    
    # Keep browser open for inspection
    print("\n🌐 Browser will remain open for inspection...")
    print("Press Ctrl+C to close browser")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Closing browser...")
        browser_manager.cleanup()


if __name__ == "__main__":
    test_po_isolation()
