#!/usr/bin/env python3
"""
Test script to check if different POs have different attachments.
"""

import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add parallel_test to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from browser import BrowserManager
from downloader import Downloader


def test_po_attachments():
    """Test if different POs have different attachments."""
    print("🧪 Testing PO Attachments")
    print("=" * 50)
    
    # Initialize browser
    print("🚀 Initializing browser...")
    browser_manager = BrowserManager()
    browser_manager.initialize_driver()
    
    # Test POs
    test_pos = ["PO16928033", "PO16518898", "PO16229343"]
    
    for po_number in test_pos:
        print(f"\n📋 Testing PO: {po_number}")
        
        # Create downloader
        downloader = Downloader(browser_manager.driver, browser_manager)
        
        # Navigate to PO page
        order_number = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
        url = f"https://unilever.coupahost.com/order_headers/{order_number}"
        print(f"   🌐 Navigating to: {url}")
        
        browser_manager.driver.get(url)
        
        # Find attachments
        attachments = downloader._find_attachments()
        
        if attachments:
            print(f"   📎 Found {len(attachments)} attachments:")
            for i, attachment in enumerate(attachments):
                filename = downloader._extract_filename_from_element(attachment)
                if filename:
                    print(f"      {i+1}. {filename}")
                else:
                    print(f"      {i+1}. <filename not found>")
        else:
            print("   ❌ No attachments found")
        
        # Wait a bit between POs
        import time
        time.sleep(2)
    
    # Keep browser open for inspection
    print("\n🌐 Browser will remain open for inspection...")
    browser_manager.keep_browser_open()


if __name__ == "__main__":
    test_po_attachments()
