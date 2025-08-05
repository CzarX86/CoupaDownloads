#!/usr/bin/env python3
"""
Test Excel compatibility for the Coupa Downloads project.
Verifies that the system can handle Excel input files.
"""

import os
import sys
import tempfile
import pandas as pd
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.unified_processor import UnifiedProcessor
from core.excel_processor import ExcelProcessor
from core.csv_processor import CSVProcessor


class TestExcelCompatibility:
    """Test Excel input file compatibility."""
    
    def test_excel_processor_creation(self):
        """Test that ExcelProcessor can be instantiated."""
        assert ExcelProcessor is not None
        print("✅ ExcelProcessor class exists")
    
    def test_unified_processor_creation(self):
        """Test that UnifiedProcessor can be instantiated."""
        assert UnifiedProcessor is not None
        print("✅ UnifiedProcessor class exists")
    
    def test_file_type_detection(self):
        """Test file type detection."""
        assert UnifiedProcessor.get_file_type("test.csv") == "csv"
        assert UnifiedProcessor.get_file_type("test.xlsx") == "excel"
        assert UnifiedProcessor.get_file_type("test.xls") == "excel"
        print("✅ File type detection works correctly")
    
    def test_excel_file_creation(self):
        """Test creating an Excel file with sample data."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Create sample data
            data = [
                {'PO_NUMBER': 'PO15826591', 'STATUS': 'PENDING'},
                {'PO_NUMBER': 'PO15873456', 'STATUS': 'COMPLETED'},
                {'PO_NUMBER': 'PO15891234', 'STATUS': 'FAILED'}
            ]
            
            df = pd.DataFrame(data)
            df.to_excel(tmp_file.name, index=False)
            
            # Verify file was created
            assert os.path.exists(tmp_file.name)
            file_size = os.path.getsize(tmp_file.name)
            assert file_size > 0
            
            print(f"✅ Excel file created: {tmp_file.name} ({file_size} bytes)")
            
            # Cleanup
            os.unlink(tmp_file.name)
    
    def test_excel_reading(self):
        """Test reading PO numbers from Excel file."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Create sample data
            data = [
                {'PO_NUMBER': 'PO15826591', 'STATUS': 'PENDING'},
                {'PO_NUMBER': 'PO15873456', 'STATUS': 'COMPLETED'},
                {'PO_NUMBER': 'PO15891234', 'STATUS': 'FAILED'}
            ]
            
            df = pd.DataFrame(data)
            df.to_excel(tmp_file.name, index=False)
            
            # Read using ExcelProcessor
            po_entries = ExcelProcessor.read_po_numbers_from_excel(tmp_file.name)
            
            assert len(po_entries) == 3
            assert po_entries[0]['po_number'] == 'PO15826591'
            assert po_entries[0]['status'] == 'PENDING'
            assert po_entries[1]['po_number'] == 'PO15873456'
            assert po_entries[1]['status'] == 'COMPLETED'
            
            print(f"✅ Excel reading works: {len(po_entries)} entries read")
            
            # Cleanup
            os.unlink(tmp_file.name)
    
    def test_excel_processing(self):
        """Test processing PO numbers from Excel file."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Create sample data
            data = [
                {'PO_NUMBER': 'PO15826591', 'STATUS': 'PENDING'},
                {'PO_NUMBER': 'PO15873456', 'STATUS': 'COMPLETED'},  # Should be skipped
                {'PO_NUMBER': 'PO15891234', 'STATUS': 'PENDING'}
            ]
            
            df = pd.DataFrame(data)
            df.to_excel(tmp_file.name, index=False)
            
            # Read and process
            po_entries = ExcelProcessor.read_po_numbers_from_excel(tmp_file.name)
            valid_entries = ExcelProcessor.process_po_numbers(po_entries)
            
            # Should have 2 valid entries (skipping completed)
            assert len(valid_entries) == 2
            assert valid_entries[0][0] == 'PO15826591'  # display_po
            assert valid_entries[0][1] == '15826591'    # clean_po
            assert valid_entries[1][0] == 'PO15891234'  # display_po
            assert valid_entries[1][1] == '15891234'    # clean_po
            
            print(f"✅ Excel processing works: {len(valid_entries)} valid entries")
            
            # Cleanup
            os.unlink(tmp_file.name)
    
    def test_unified_processor_excel(self):
        """Test UnifiedProcessor with Excel file."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Create sample data
            data = [
                {'PO_NUMBER': 'PO15826591', 'STATUS': 'PENDING'},
                {'PO_NUMBER': 'PO15873456', 'STATUS': 'PENDING'}
            ]
            
            df = pd.DataFrame(data)
            df.to_excel(tmp_file.name, index=False)
            
            # Test unified processor
            file_type = UnifiedProcessor.get_file_type(tmp_file.name)
            assert file_type == 'excel'
            
            po_entries = UnifiedProcessor.read_po_numbers(tmp_file.name)
            assert len(po_entries) == 2
            
            valid_entries = UnifiedProcessor.process_po_numbers(tmp_file.name)
            assert len(valid_entries) == 2
            
            print(f"✅ UnifiedProcessor works with Excel files")
            
            # Cleanup
            os.unlink(tmp_file.name)
    
    def test_csv_to_excel_conversion(self):
        """Test converting CSV to Excel format."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as csv_file:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
                # Create sample CSV
                csv_data = "PO_NUMBER,STATUS\nPO15826591,PENDING\nPO15873456,COMPLETED"
                csv_file.write(csv_data.encode('utf-8'))
                csv_file.flush()
                
                # Convert to Excel
                ExcelProcessor.convert_csv_to_excel(csv_file.name, excel_file.name)
                
                # Verify Excel file was created
                assert os.path.exists(excel_file.name)
                file_size = os.path.getsize(excel_file.name)
                assert file_size > 0
                
                # Read back and verify
                df = pd.read_excel(excel_file.name)
                assert len(df) == 2
                assert df.iloc[0]['PO_NUMBER'] == 'PO15826591'
                assert df.iloc[1]['PO_NUMBER'] == 'PO15873456'
                
                print(f"✅ CSV to Excel conversion works")
                
                # Cleanup
                os.unlink(csv_file.name)
                os.unlink(excel_file.name)
    
    def test_excel_formatting(self):
        """Test Excel formatting capabilities."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Create sample data
            data = [
                {'PO_NUMBER': 'PO15826591', 'STATUS': 'PENDING'},
                {'PO_NUMBER': 'PO15873456', 'STATUS': 'COMPLETED'},
                {'PO_NUMBER': 'PO15891234', 'STATUS': 'FAILED'}
            ]
            
            df = pd.DataFrame(data)
            
            # Write with formatting
            with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='PO_Data', index=False)
                ExcelProcessor._apply_excel_formatting(writer, df)
            
            # Verify file was created with formatting
            assert os.path.exists(tmp_file.name)
            file_size = os.path.getsize(tmp_file.name)
            assert file_size > 0
            
            print(f"✅ Excel formatting works: {file_size} bytes")
            
            # Cleanup
            os.unlink(tmp_file.name)
    
    def test_excel_summary_report(self):
        """Test Excel summary report generation."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Create sample data
            data = [
                {'PO_NUMBER': 'PO15826591', 'STATUS': 'PENDING'},
                {'PO_NUMBER': 'PO15873456', 'STATUS': 'COMPLETED'},
                {'PO_NUMBER': 'PO15891234', 'STATUS': 'FAILED'}
            ]
            
            df = pd.DataFrame(data)
            df.to_excel(tmp_file.name, index=False)
            
            # Generate summary report
            report = ExcelProcessor.generate_summary_report(tmp_file.name)
            
            assert report['total_pos'] == 3
            assert report['status_counts']['PENDING'] == 1
            assert report['status_counts']['COMPLETED'] == 1
            assert report['status_counts']['FAILED'] == 1
            assert report['success_rate'] == 33.3  # 1/3 * 100
            
            print(f"✅ Excel summary report works: {report['total_pos']} POs")
            
            # Cleanup
            os.unlink(tmp_file.name)


def main():
    """Run all Excel compatibility tests."""
    print("🧪 Testing Excel Compatibility")
    print("=" * 50)
    
    test_instance = TestExcelCompatibility()
    
    tests = [
        test_instance.test_excel_processor_creation,
        test_instance.test_unified_processor_creation,
        test_instance.test_file_type_detection,
        test_instance.test_excel_file_creation,
        test_instance.test_excel_reading,
        test_instance.test_excel_processing,
        test_instance.test_unified_processor_excel,
        test_instance.test_csv_to_excel_conversion,
        test_instance.test_excel_formatting,
        test_instance.test_excel_summary_report
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All Excel compatibility tests passed!")
        print("✅ The project is now compatible with Excel input files")
    else:
        print("⚠️ Some tests failed - Excel compatibility may have issues")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 