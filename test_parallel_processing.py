#!/usr/bin/env python3
"""
Test script to verify parallel processing with browser tabs.
"""

import os
import sys
from src.main import MainApp

def test_parallel_processing():
    """Test parallel processing with a small sample of POs."""
    print("🧪 Testing Parallel Processing with Browser Tabs")
    print("=" * 60)
    
    # Set environment variable to limit POs for testing
    os.environ['RANDOM_SAMPLE_POS'] = '5'
    
    try:
        app = MainApp()
        app.run()
        print("\n✅ Parallel processing test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during parallel processing test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Cleaning up...")
        try:
            app.close()
        except:
            pass

if __name__ == "__main__":
    test_parallel_processing()
