#!/usr/bin/env python3
"""
Test script for the simplified enhanced download control system.
"""

import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add the parallel_test directory to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from simple_enhanced_main import SimpleMainApp

def test_simple_enhanced_system():
    """Test the simplified enhanced download control system."""
    print("🧪 Testing Simplified Enhanced Download Control System")
    print("=" * 60)
    
    try:
        # Reset some POs to Pending for testing
        import pandas as pd
        df = pd.read_excel('data/input/input.xlsx', sheet_name='PO_Data')
        
        # Reset first 2 POs to Pending
        df.loc[df.index[:2], 'STATUS'] = 'Pending'
        df.to_excel('data/input/input.xlsx', sheet_name='PO_Data', index=False)
        print("✅ Reset first 2 POs to Pending")
        
        # Run the simplified system
        app = SimpleMainApp()
        app.run()
        
        print("\n✅ Simplified system test completed!")
        
        # Show the download control CSV
        csv_path = "data/control/download_control.csv"
        if os.path.exists(csv_path):
            print(f"\n📊 Download Control CSV saved at: {os.path.abspath(csv_path)}")
            print("📄 CSV Contents:")
            with open(csv_path, 'r') as f:
                print(f.read())
        else:
            print(f"\n❌ No download control CSV found at: {os.path.abspath(csv_path)}")
            
    except Exception as e:
        print(f"\n❌ Error during simplified system test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_enhanced_system()
