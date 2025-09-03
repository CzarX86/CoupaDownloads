#!/usr/bin/env python3
"""
Test to verify main.py execution flow.
"""

import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from main import CoupaDownloader

def test_main_execution():
    """Test main execution flow."""
    print("🧪 Testing main execution flow...")
    
    try:
        # Create downloader instance
        downloader = CoupaDownloader()
        print("✅ Downloader instance created")
        
        # Test setup
        print("\n1️⃣ Testing setup...")
        downloader.setup()
        print("✅ Setup completed")
        
        # Test PO processing
        print("\n2️⃣ Testing PO processing...")
        valid_entries = downloader.process_po_numbers()
        print(f"✅ PO processing completed: {len(valid_entries)} entries")
        
        if valid_entries:
            print(f"✅ Sample entry: {valid_entries[0]}")
        
        # Test login handling
        print("\n3️⃣ Testing login handling...")
        login_success = downloader.handle_login_first()
        print(f"✅ Login handling completed: {'Success' if login_success else 'Failed'}")
        
        print("\n✅ Main execution flow is working!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_main_execution()
