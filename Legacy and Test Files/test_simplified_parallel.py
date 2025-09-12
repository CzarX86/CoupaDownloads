#!/usr/bin/env python3
"""
Test script for parallel processing with simplified system.
"""

import os
import sys

# Set environment variables for testing
os.environ['RANDOM_SAMPLE_POS'] = '3'  # Test with 3 POs

def test_parallel_system():
    """Test the simplified parallel processing system."""
    print("🧪 Testing Simplified Parallel Processing System")
    print("=" * 60)
    
    try:
        # Import and run the simplified main
        from src.utils.parallel_test.main import MainApp
        
        app = MainApp()
        app.run()
        
        print("\n✅ Parallel processing test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during parallel processing test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parallel_system()
