#!/usr/bin/env python3
"""
E2E Test for parallel_test system with all status scenarios.
"""

import os
import sys
import pandas as pd

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add parallel_test to path
parallel_test_dir = os.path.join(project_root, "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from main import MainApp


def reset_test_pos():
    """Reset specific POs to 'Pending' status for testing."""
    excel_path = "data/input/input.xlsx"
    
    try:
        # Read Excel file
        df = pd.read_excel(excel_path)
        
        # Reset specific test POs to 'Pending'
        test_pos = ["PO16518898", "PO16229343", "PO16928033"]
        for po in test_pos:
            if po in df['PO_NUMBER'].values:
                df.loc[df['PO_NUMBER'] == po, 'STATUS'] = 'Pending'
                print(f"   🔄 Reset {po} to Pending")
        
        # Save back to Excel
        df.to_excel(excel_path, index=False)
        print(f"   ✅ Excel file updated")
        
    except Exception as e:
        print(f"   ❌ Error resetting POs: {e}")


def test_e2e_all_scenarios():
    """Test E2E with all status scenarios."""
    print("🧪 E2E Test - All Status Scenarios")
    print("=" * 50)
    
    # Reset test POs
    print("\n🔄 Resetting test POs...")
    reset_test_pos()
    
    # Initialize the main app
    app = MainApp()
    
    print("\n📊 Test Scenarios:")
    print("1. Success: PO16518898 (has attachments)")
    print("2. Success: PO16229343 (has attachments)")
    print("3. No Attachment: PO16928033 (no attachments)")
    
    print("\n🚀 Starting E2E test...")
    
    try:
        # Run the main app
        app.run()
        
        print("\n✅ E2E test completed!")
        
        # Show final results
        print("\n📁 Final folder structure:")
        base_folder = "/Users/juliocezar/Downloads/CoupaDownloads"
        if os.path.exists(base_folder):
            for root, dirs, files in os.walk(base_folder):
                level = root.replace(base_folder, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}📁 {os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    print(f"{subindent}📄 {file}")
        
        print("\n📊 CSV Results:")
        csv_path = "data/control/download_control_parallel.csv"
        if os.path.exists(csv_path):
            with open(csv_path, 'r') as f:
                print(f.read())
        
    except Exception as e:
        print(f"❌ E2E test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_e2e_all_scenarios()
