#!/usr/bin/env python3
"""
Test script to verify status writing and timing issues.
"""

import time
from datetime import datetime

def test_status_writing():
    """Test if status writing to Excel is working."""
    print("🧪 Testing status writing to Excel...")
    
    # Simulate the status update call
    from src.core.excel_processor import ExcelProcessor
    
    test_po = "PO16518898"
    test_status = "TEST_STATUS"
    
    try:
        ExcelProcessor.update_po_status(
            po_number=test_po,
            status=test_status,
            supplier="Test Supplier",
            attachments_found=2,
            attachments_downloaded=2,
            error_message="Test error message",
            download_folder="/test/folder",
            coupa_url="https://test.coupa.com",
            attachment_names="test_file.pdf;test_file2.pdf"
        )
        print(f"✅ Status writing test completed for {test_po}")
    except Exception as e:
        print(f"❌ Status writing test failed: {e}")

def test_timing_analysis():
    """Analyze current timing settings."""
    print("\n⏱️ Analyzing current timing settings...")
    
    from src.core.config import Config
    
    print(f"📊 Current timing configuration:")
    print(f"   PAGE_LOAD_TIMEOUT: {Config.PAGE_LOAD_TIMEOUT} seconds")
    print(f"   ATTACHMENT_WAIT_TIMEOUT: {Config.ATTACHMENT_WAIT_TIMEOUT} seconds")
    print(f"   DOWNLOAD_WAIT_TIMEOUT: {Config.DOWNLOAD_WAIT_TIMEOUT} seconds")
    print(f"   PAGE_DELAY: {Config.PAGE_DELAY} seconds")
    
    print(f"\n🔍 Timing analysis:")
    print(f"   ✅ Page load timeout: {Config.PAGE_LOAD_TIMEOUT}s (seems reasonable)")
    print(f"   ⚠️ Attachment wait timeout: {Config.ATTACHMENT_WAIT_TIMEOUT}s (might be too short)")
    print(f"   ✅ Download wait timeout: {Config.DOWNLOAD_WAIT_TIMEOUT}s (seems reasonable)")
    print(f"   ⚠️ Page delay: {Config.PAGE_DELAY}s (no delay between POs!)")
    
    print(f"\n💡 Recommendations:")
    print(f"   • Increase ATTACHMENT_WAIT_TIMEOUT to 15-20 seconds")
    print(f"   • Add PAGE_DELAY of 2-3 seconds between POs")
    print(f"   • Add explicit wait for attachments to load")

if __name__ == "__main__":
    test_status_writing()
    test_timing_analysis()
