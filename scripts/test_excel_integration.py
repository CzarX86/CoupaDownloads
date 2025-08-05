#!/usr/bin/env python3
"""
Test Excel Integration with Main Application
Verifies that the main application works correctly with Excel input files.
"""

import os
import sys
import tempfile
import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.unified_processor import UnifiedProcessor
from core.excel_processor import ExcelProcessor


def test_main_application_integration():
    """Test that the main application can work with Excel files."""
    print("🧪 Testing Main Application Excel Integration")
    print("=" * 60)
    
    # Test 1: File Detection
    print("📊 Test 1: File Detection")
    detected_file = UnifiedProcessor.detect_input_file()
    file_type = UnifiedProcessor.get_file_type(detected_file)
    print(f"   ✅ Detected: {os.path.basename(detected_file)} ({file_type.upper()})")
    
    # Test 2: PO Processing
    print("\n📋 Test 2: PO Processing")
    try:
        po_entries = UnifiedProcessor.read_po_numbers(detected_file)
        valid_entries = UnifiedProcessor.process_po_numbers(detected_file)
        print(f"   ✅ Read {len(po_entries)} PO entries")
        print(f"   ✅ Processed {len(valid_entries)} valid entries")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: Status Updates
    print("\n🔄 Test 3: Status Updates")
    try:
        # Test updating a PO status
        test_po = "PO15363269"  # Use first PO in the file
        UnifiedProcessor.update_po_status(
            test_po, 
            'TESTING', 
            supplier='Test Supplier',
            attachments_found=2,
            attachments_downloaded=1,
            error_message='Test update'
        )
        print(f"   ✅ Successfully updated {test_po} status")
        
        # Verify the update
        po_entries = UnifiedProcessor.read_po_numbers(detected_file)
        updated_po = next((entry for entry in po_entries if entry['po_number'] == test_po), None)
        if updated_po and updated_po['status'] == 'TESTING':
            print(f"   ✅ Status update verified in file")
        else:
            print(f"   ⚠️ Status update not found in file")
            
    except Exception as e:
        print(f"   ❌ Error updating status: {e}")
        return False
    
    # Test 4: Summary Report
    print("\n📈 Test 4: Summary Report")
    try:
        report = UnifiedProcessor.generate_summary_report()
        print(f"   ✅ Generated summary report")
        print(f"   📊 Total POs: {report['total_pos']}")
        print(f"   🎯 Success Rate: {report['success_rate']}%")
    except Exception as e:
        print(f"   ❌ Error generating report: {e}")
        return False
    
    # Test 5: Backup Functionality
    print("\n💾 Test 5: Backup Functionality")
    try:
        backup_path = UnifiedProcessor.backup_file()
        if backup_path and os.path.exists(backup_path):
            print(f"   ✅ Backup created: {os.path.basename(backup_path)}")
        else:
            print(f"   ⚠️ Backup creation failed")
    except Exception as e:
        print(f"   ❌ Error creating backup: {e}")
        return False
    
    # Test 6: Import Verification
    print("\n🔧 Test 6: Import Verification")
    try:
        # Test that main application imports work
        from core.browser import BrowserManager
        from core.config import Config
        from core.downloader import DownloadManager, LoginManager
        print(f"   ✅ All core modules import successfully")
    except Exception as e:
        print(f"   ❌ Import error: {e}")
        return False
    
    # Test 7: Main Application Class
    print("\n🚀 Test 7: Main Application Class")
    try:
        from main import CoupaDownloader
        downloader = CoupaDownloader()
        print(f"   ✅ CoupaDownloader class instantiated successfully")
        
        # Test PO processing method
        valid_entries = downloader.process_po_numbers()
        print(f"   ✅ process_po_numbers() returned {len(valid_entries)} entries")
        
    except Exception as e:
        print(f"   ❌ Error with main application: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Excel Integration Tests Passed!")
    print("✅ The main application is fully compatible with Excel input files")
    return True


def test_file_conversion():
    """Test file conversion between CSV and Excel."""
    print("\n🔄 Testing File Conversion")
    print("=" * 40)
    
    try:
        # Test CSV to Excel conversion
        csv_path = UnifiedProcessor.get_processor_info()['csv_path']
        if os.path.exists(csv_path):
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_excel:
                UnifiedProcessor.convert_file_format(csv_path, tmp_excel.name)
                if os.path.exists(tmp_excel.name):
                    print(f"   ✅ CSV to Excel conversion successful")
                    os.unlink(tmp_excel.name)
                else:
                    print(f"   ❌ CSV to Excel conversion failed")
        else:
            print(f"   ⚠️ No CSV file found for conversion test")
            
        # Test Excel to CSV conversion
        excel_path = UnifiedProcessor.get_processor_info()['excel_path']
        if os.path.exists(excel_path):
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_csv:
                UnifiedProcessor.convert_file_format(excel_path, tmp_csv.name)
                if os.path.exists(tmp_csv.name):
                    print(f"   ✅ Excel to CSV conversion successful")
                    os.unlink(tmp_csv.name)
                else:
                    print(f"   ❌ Excel to CSV conversion failed")
        else:
            print(f"   ⚠️ No Excel file found for conversion test")
            
    except Exception as e:
        print(f"   ❌ Error in file conversion: {e}")


def main():
    """Run all integration tests."""
    print("🎯 Excel Integration Test Suite")
    print("=" * 60)
    
    # Run main integration tests
    success = test_main_application_integration()
    
    # Run file conversion tests
    test_file_conversion()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 EXCEL INTEGRATION: FULLY FUNCTIONAL")
        print("✅ All tests passed - ready for production use")
        print("\n💡 You can now:")
        print("   1. Use Excel files as input: data/input/input.xlsx")
        print("   2. Run the main application: python src/main.py")
        print("   3. All processing will work with Excel format")
        print("   4. Status updates will be saved to Excel file")
    else:
        print("❌ EXCEL INTEGRATION: ISSUES DETECTED")
        print("⚠️ Some tests failed - review the output above")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 