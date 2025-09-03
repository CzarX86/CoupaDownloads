#!/usr/bin/env python3
"""
Simple test for CSV control system with a known PO.
"""

import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.core.browser import BrowserManager
from src.core.downloader import Downloader
from src.core.download_control import DownloadControlManager


def test_simple_csv_control():
    """Test CSV control with a known PO that has attachments."""
    print("🧪 Simple CSV Control Test")
    print("=" * 50)
    
    # Initialize components
    print("🚀 Initializing components...")
    browser_manager = BrowserManager()
    download_control = DownloadControlManager()
    
    try:
        # Initialize browser
        print("🌐 Initializing browser...")
        browser_manager.initialize_driver()
        
        # Create downloader with CSV control
        downloader = Downloader(browser_manager.driver, browser_manager, download_control)
        
        # Test with a known PO that has attachments
        po_number = "PO16518898"
        print(f"📋 Testing with PO: {po_number}")
        
        # Process the PO
        success, message = downloader.download_attachments_for_po(po_number, "TAB_TEST")
        
        print(f"✅ Result: {success} - {message}")
        
        # Show CSV results
        print("\n📊 CSV Control Results:")
        csv_path = download_control.get_csv_path()
        print(f"📄 CSV file: {os.path.abspath(csv_path)}")
        
        # Read and display CSV contents
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                content = file.read()
                print("\n📄 CSV Contents:")
                print("-" * 80)
                print(content)
                print("-" * 80)
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
        
        # Keep browser open for inspection
        print("\n🌐 Browser will remain open for inspection...")
        browser_manager.keep_browser_open()
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to clean up
        try:
            browser_manager.cleanup()
        except:
            pass


if __name__ == "__main__":
    test_simple_csv_control()
