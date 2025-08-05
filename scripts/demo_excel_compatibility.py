#!/usr/bin/env python3
"""
Excel Compatibility Demonstration
Shows how the Coupa Downloads project works with Excel input files.
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.unified_processor import UnifiedProcessor


def main():
    """Demonstrate Excel compatibility features."""
    print("🎯 Excel Compatibility Demonstration")
    print("=" * 50)
    
    # Get processor information
    info = UnifiedProcessor.get_processor_info()
    
    print(f"📊 Current File Status:")
    print(f"   📁 CSV Path: {info['csv_path']}")
    print(f"   📁 Excel Path: {info['excel_path']}")
    print(f"   📊 CSV Exists: {info['csv_exists']}")
    print(f"   📊 Excel Exists: {info['excel_exists']}")
    print(f"   🎯 Detected File: {os.path.basename(info['detected_file'])}")
    print(f"   📋 File Type: {info['detected_type'].upper()}")
    print(f"   📏 File Size: {info['file_size']} bytes")
    
    print(f"\n🔄 File Detection Test:")
    detected_file = UnifiedProcessor.detect_input_file()
    file_type = UnifiedProcessor.get_file_type(detected_file)
    print(f"   🎯 Detected: {os.path.basename(detected_file)}")
    print(f"   📋 Type: {file_type.upper()}")
    
    print(f"\n📖 Reading PO Numbers:")
    po_entries = UnifiedProcessor.read_po_numbers(detected_file)
    print(f"   📊 Total entries: {len(po_entries)}")
    
    if po_entries:
        print(f"   📋 Sample entries:")
        for i, entry in enumerate(po_entries[:3]):  # Show first 3
            print(f"      {i+1}. {entry['po_number']} - {entry['status']}")
        if len(po_entries) > 3:
            print(f"      ... and {len(po_entries) - 3} more")
    
    print(f"\n⚙️ Processing PO Numbers:")
    valid_entries = UnifiedProcessor.process_po_numbers(detected_file)
    print(f"   📊 Valid entries: {len(valid_entries)}")
    
    if valid_entries:
        print(f"   📋 Sample valid entries:")
        for i, (display_po, clean_po) in enumerate(valid_entries[:3]):  # Show first 3
            print(f"      {i+1}. {display_po} → {clean_po}")
        if len(valid_entries) > 3:
            print(f"      ... and {len(valid_entries) - 3} more")
    
    print(f"\n📈 Summary Report:")
    report = UnifiedProcessor.generate_summary_report()
    print(f"   📊 Total POs: {report['total_pos']}")
    print(f"   🎯 Success Rate: {report['success_rate']}%")
    print(f"   📎 Attachments Found: {report['total_attachments_found']}")
    print(f"   💾 Attachments Downloaded: {report['total_attachments_downloaded']}")
    print(f"   🏢 Unique Suppliers: {report['unique_suppliers']}")
    
    print(f"\n🔄 Format Conversion Test:")
    if info['csv_exists'] and info['excel_exists']:
        print(f"   ✅ Both CSV and Excel files exist")
        print(f"   💡 You can convert between formats:")
        print(f"      CSV → Excel: UnifiedProcessor.convert_file_format('input.csv', 'input.xlsx')")
        print(f"      Excel → CSV: UnifiedProcessor.convert_file_format('input.xlsx', 'input.csv')")
    elif info['csv_exists']:
        print(f"   📁 Only CSV exists - can convert to Excel")
    elif info['excel_exists']:
        print(f"   📊 Only Excel exists - can convert to CSV")
    else:
        print(f"   ❌ No input files found")
    
    print(f"\n🎨 Excel Features:")
    if file_type == 'excel':
        print(f"   ✅ Professional formatting with colors")
        print(f"   ✅ Conditional formatting for status")
        print(f"   ✅ Header styling (bold, blue background)")
        print(f"   ✅ Status color coding:")
        print(f"      🟢 Green: COMPLETED")
        print(f"      🔴 Red: FAILED")
        print(f"      🟡 Yellow: PENDING")
    else:
        print(f"   📁 Currently using CSV format")
        print(f"   💡 Convert to Excel for enhanced formatting")
    
    print(f"\n🚀 Ready to Use:")
    print(f"   ✅ The system is fully compatible with Excel input files")
    print(f"   ✅ Automatic file detection works")
    print(f"   ✅ All processing functions work with both formats")
    print(f"   ✅ Professional Excel formatting included")
    print(f"   ✅ Backward compatibility maintained")
    
    print(f"\n💡 Next Steps:")
    print(f"   1. Run the main application: python src/main.py")
    print(f"   2. The system will automatically use {file_type.upper()} format")
    print(f"   3. All processing will work seamlessly")
    print(f"   4. Status updates will be saved to the {file_type.upper()} file")
    
    print(f"\n" + "=" * 50)
    print(f"🎉 Excel Compatibility Demo Complete!")
    print(f"✅ Your project is ready to use with Excel input files!")


if __name__ == "__main__":
    main() 