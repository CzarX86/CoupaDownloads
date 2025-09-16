#!/usr/bin/env python3
"""
Test script for the enhanced main system with CSV control.
"""

import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.core.excel_processor import ExcelProcessor
from src.main import MainApp


def test_enhanced_main():
    """Test the enhanced main system with CSV control."""
    print("🧪 Testing Enhanced Main System with CSV Control")
    print("=" * 60)
    
    # Reset POs to 'Pending' status
    print("📋 Resetting POs to 'Pending' status...")
    import pandas as pd
    df = pd.read_excel('data/input/input.xlsx', sheet_name='PO_Data')
    
    # Reset first 3 POs to Pending
    df.loc[df.index[:3], 'STATUS'] = 'Pending'
    df.to_excel('data/input/input.xlsx', sheet_name='PO_Data', index=False)
    print("✅ Reset first 3 POs to Pending")
    
    # Run the enhanced main system
    print("\n🚀 Running Enhanced Main System...")
    main_app = MainApp()
    main_app.run()
    
    # Show CSV control results
    print("\n📊 CSV Control Results:")
    csv_path = main_app.download_control.get_csv_path()
    print(f"📄 CSV file: {os.path.abspath(csv_path)}")
    
    # Read and display CSV contents
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            content = file.read()
            print("\n📄 CSV Contents:")
            print("-" * 80)
            print(content)
            print("-" * 80)
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")


if __name__ == "__main__":
    test_enhanced_main()
