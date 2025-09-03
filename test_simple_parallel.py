#!/usr/bin/env python3
"""
Simple test to verify tab isolation in parallel processing.
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
from download_control import DownloadControlManager


def test_simple_parallel():
    """Test simple parallel processing with specific POs."""
    print("🧪 Testing Simple Parallel Processing")
    print("=" * 50)
    
    # Initialize browser
    print("🚀 Initializing browser...")
    browser_manager = BrowserManager()
    browser_manager.initialize_driver()
    
    # Initialize download control
    download_control = DownloadControlManager()
    
    # Test POs - these should have different attachments
    test_pos = ["PO16518898", "PO16229343", "PO16928033", "PO16928034", "PO16928035"]  # More POs for testing
    
    # Store tab handles
    tab_handles = {}
    
    # Create tabs for each PO
    print("\n📋 Creating tabs for each PO...")
    for po_number in test_pos:
        # Create tab with download directory (use temp folder)
        download_folder = "/Users/juliocezar/Downloads/CoupaDownloads/Temp"
        tab_handle = browser_manager.create_tab_with_download_dir(download_folder)
        
        if tab_handle:
            tab_handles[po_number] = tab_handle
            print(f"   ✅ Created tab for {po_number}: {tab_handle}")
        else:
            print(f"   ❌ Failed to create tab for {po_number}")
    
    # Process each PO in its own tab
    print("\n🔍 Processing each PO in its own tab...")
    for po_number in test_pos:
        if po_number not in tab_handles:
            continue
            
        print(f"\n📋 Processing PO: {po_number}")
        print(f"   🔄 Switching to tab: {tab_handles[po_number]}")
        
        # Create downloader for this tab
        downloader = Downloader(browser_manager.driver, browser_manager, download_control)
        
        # Process the PO with its specific tab
        success, message = downloader.download_attachments_for_po(po_number, tab_handles[po_number], None)
        
        print(f"   📊 Result: {message}")
        
        # Wait between POs
        import time
        time.sleep(2)
    
    # Show CSV results
    print("\n📊 CSV Control Results:")
    print("=" * 30)
    
    csv_file = download_control.get_csv_path()
    if os.path.exists(csv_file):
        with open(csv_file, 'r') as f:
            content = f.read()
            print(content)
    else:
        print("❌ CSV file not found")
    
    # Keep browser open for inspection
    print("\n🌐 Browser will remain open for inspection...")
    print("Press Ctrl+C to close browser")
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Closing browser...")
        browser_manager.cleanup()


if __name__ == "__main__":
    test_simple_parallel()
