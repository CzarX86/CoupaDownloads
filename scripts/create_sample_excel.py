#!/usr/bin/env python3
"""
Script to create a sample Excel file from the existing CSV data.
This demonstrates Excel compatibility for the Coupa Downloads project.
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.unified_processor import UnifiedProcessor


def main():
    """Create a sample Excel file from CSV data."""
    print("📊 Creating Sample Excel File")
    print("=" * 40)
    
    # Get processor info
    info = UnifiedProcessor.get_processor_info()
    
    print(f"📁 CSV Path: {info['csv_path']}")
    print(f"📁 Excel Path: {info['excel_path']}")
    print(f"📊 CSV Exists: {info['csv_exists']}")
    print(f"📊 Excel Exists: {info['excel_exists']}")
    
    if info['csv_exists']:
        print(f"\n🔄 Converting CSV to Excel...")
        excel_path = UnifiedProcessor.create_sample_excel_file()
        
        if excel_path and os.path.exists(excel_path):
            file_size = os.path.getsize(excel_path) / 1024  # KB
            print(f"\n✅ Successfully created Excel file:")
            print(f"   📁 Path: {excel_path}")
            print(f"   📊 Size: {file_size:.1f} KB")
            print(f"   📋 Format: Excel (.xlsx)")
            print(f"   🎨 Features: Professional formatting, conditional styling")
            
            # Show processor info again
            new_info = UnifiedProcessor.get_processor_info()
            print(f"\n📊 Updated File Status:")
            print(f"   📁 CSV Exists: {new_info['csv_exists']}")
            print(f"   📁 Excel Exists: {new_info['excel_exists']}")
            print(f"   🎯 Detected File: {os.path.basename(new_info['detected_file'])}")
            print(f"   📋 File Type: {new_info['detected_type'].upper()}")
            
            print(f"\n💡 You can now use either CSV or Excel as input!")
            print(f"   The system will automatically detect which file to use.")
            
        else:
            print(f"❌ Failed to create Excel file")
    else:
        print(f"❌ No CSV file found to convert")
        print(f"💡 Please create an input.csv file first")


if __name__ == "__main__":
    main() 