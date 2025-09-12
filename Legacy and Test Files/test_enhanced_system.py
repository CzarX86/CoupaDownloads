#!/usr/bin/env python3
"""
Test script for the enhanced download control system.
"""

import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add the parallel_test directory to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from enhanced_main import EnhancedMainApp

def test_enhanced_system():
    """Test the enhanced download control system."""
    print("🧪 Testing Enhanced Download Control System")
    print("=" * 60)
    
    try:
        # Reset some POs to Pending for testing
        import pandas as pd
        df = pd.read_excel('data/input/input.xlsx', sheet_name='PO_Data')
        
        # Reset first 2 POs to Pending
        df.loc[df.index[:2], 'STATUS'] = 'Pending'
        df.to_excel('data/input/input.xlsx', sheet_name='PO_Data', index=False)
        print("✅ Reset first 2 POs to Pending")
        
        # Run the enhanced system
        app = EnhancedMainApp()
        app.run()
        
        print("\n✅ Enhanced system test completed!")
        
        # Show the download control CSV
        if os.path.exists("download_control.csv"):
            print("\n📊 Download Control CSV Contents:")
            with open("download_control.csv", 'r') as f:
                print(f.read())
        else:
            print("\n❌ No download control CSV found")
            
    except Exception as e:
        print(f"\n❌ Error during enhanced system test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_system()
