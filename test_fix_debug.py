#!/usr/bin/env python3
"""
Debug script to test the element click interception fix.
Tests with a small sample of POs to verify the fix works.
"""

import os
import sys
from src.core.browser import BrowserManager
from src.core.downloader import Downloader
from src.core.config import Config

def test_fix():
    """Test the downloader fix with a few sample POs."""
    browser_manager = BrowserManager()
    
    # Initialize the driver first
    try:
        browser_manager.initialize_driver()
        downloader = Downloader(browser_manager.driver, browser_manager)
    except Exception as e:
        print(f"Failed to initialize browser: {e}")
        return
    
    # Test with a few POs that had the click interception issue
    test_pos = [
        "PO16518898",  # Had 2 attachments, failed due to click interception
        "PO16229343",  # Had 4 attachments, failed due to click interception
        "PO16221175",  # Had 1 attachment, failed due to click interception
    ]
    
    try:
        for po_number in test_pos:
            print(f"\n{'='*60}")
            print(f"Testing fix with {po_number}")
            print(f"{'='*60}")
            
            success, message = downloader.download_attachments_for_po(po_number)
            
            print(f"\nResult for {po_number}:")
            print(f"Success: {success}")
            print(f"Message: {message}")
            
            # Small delay between tests
            import time
            time.sleep(2)
            
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        browser_manager.cleanup()

if __name__ == "__main__":
    test_fix()
