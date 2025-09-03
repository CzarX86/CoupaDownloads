#!/usr/bin/env python3
"""
Simple test to verify download directory configuration.
"""

import os
import sys
import time

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add the parallel_test directory to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from browser import BrowserManager
from config import Config
from downloader import Downloader

def test_download_directory():
    """Test if download directory is being set correctly."""
    print("🧪 Testing Download Directory Configuration")
    print("=" * 50)
    
    # Create a test download directory
    test_download_dir = os.path.expanduser("~/Downloads/CoupaDownloads_TEST")
    os.makedirs(test_download_dir, exist_ok=True)
    
    print(f"📁 Test download directory: {test_download_dir}")
    
    try:
        # Initialize browser with specific download directory
        browser_manager = BrowserManager()
        driver = browser_manager.initialize_driver_with_download_dir(test_download_dir)
        
        print("✅ Browser initialized with download directory")
        
        # Navigate to a test PO
        test_po = "PO16518898"
        order_number = test_po.replace("PO", "")
        url = f"{Config.BASE_URL}/order_headers/{order_number}"
        
        print(f"🌐 Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Create downloader
        downloader = Downloader(driver, browser_manager)
        
        # Try to download attachments
        success, message = downloader.download_attachments_for_po(test_po)
        
        print(f"📥 Download result: {success} - {message}")
        
        # Wait a bit for downloads
        time.sleep(10)
        
        # Check if files were downloaded
        files = os.listdir(test_download_dir)
        print(f"📁 Files in test directory: {files}")
        
        if files:
            print("✅ Files were downloaded successfully!")
        else:
            print("❌ No files were downloaded")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        if 'driver' in locals():
            browser_manager.cleanup()
        
        # Remove test directory
        import shutil
        if os.path.exists(test_download_dir):
            shutil.rmtree(test_download_dir)
            print(f"🧹 Removed test directory: {test_download_dir}")

if __name__ == "__main__":
    test_download_directory()
