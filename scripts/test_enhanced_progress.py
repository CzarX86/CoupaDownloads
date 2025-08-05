#!/usr/bin/env python3
"""
Test script for enhanced progress feedback system with real PO processing.
Uses a small sample to demonstrate the new progress tracking.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import CoupaDownloader


def test_enhanced_progress():
    """Test the enhanced progress system with a small sample."""
    
    print("🧪 Testing Enhanced Progress System")
    print("=" * 50)
    
    try:
        # Initialize the downloader
        downloader = CoupaDownloader()
        
        # Test with just 3 POs to demonstrate the progress system
        test_pos = ["PO15363269", "PO15826591", "PO16277411"]
        
        print(f"📋 Testing with {len(test_pos)} POs: {test_pos}")
        print()
        
        # Process the test POs
        downloader.download_attachments(test_pos)
        
        print("\n" + "=" * 50)
        print("✅ Enhanced progress system test completed!")
        print("   The new system provides:")
        print("   • Overall progress percentage")
        print("   • Time elapsed and estimated remaining")
        print("   • Individual file download progress")
        print("   • Clear status indicators")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = test_enhanced_progress()
    sys.exit(0 if success else 1) 