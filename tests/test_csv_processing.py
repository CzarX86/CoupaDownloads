"""
CSV Processing Tests for Coupa Downloads automation.
Tests CSV file reading, processing, and status updates.
"""

import os
import csv
import tempfile
import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from core.csv_processor import CSVProcessor


class TestCSVProcessing:
    """Test CSV processing functionality"""

    def test_read_valid_csv_file(self, temp_csv_file):
        """Test reading a valid CSV file with enhanced format"""
        po_entries = CSVProcessor.read_po_numbers_from_csv(temp_csv_file)
        
        assert len(po_entries) == 3
        assert po_entries[0]['po_number'] == 'PO15826591'
        assert po_entries[0]['status'] == 'PENDING'
        assert po_entries[1]['po_number'] == 'PO15873456'
        assert po_entries[1]['status'] == 'COMPLETED'
        assert po_entries[1]['supplier'] == 'Test_Supplier_Inc'

    def test_read_simple_csv_format(self, test_data_dir):
        """Test reading simple CSV format (without enhanced headers)"""
        # Create a simple CSV file
        simple_csv = os.path.join(test_data_dir, "simple_test.csv")
        with open(simple_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['PO_NUMBER'])  # Header
            writer.writerow(['PO15826591'])
            writer.writerow(['PO15873456'])
            writer.writerow([''])  # Empty row
            writer.writerow(['PO15873457'])
        
        po_entries = CSVProcessor.read_po_numbers_from_csv(simple_csv)
        
        assert len(po_entries) == 3  # Empty row should be skipped
        assert po_entries[0]['po_number'] == 'PO15826591'
        assert po_entries[0]['status'] == 'PENDING'  # Default status
        assert po_entries[1]['po_number'] == 'PO15873456'
        assert po_entries[2]['po_number'] == 'PO15873457'

    def test_read_csv_with_missing_columns(self, test_data_dir):
        """Test reading CSV with missing columns"""
        # Create CSV with missing columns
        incomplete_csv = os.path.join(test_data_dir, "incomplete_test.csv")
        with open(incomplete_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['PO_NUMBER', 'STATUS'])  # Missing other columns
            writer.writerow(['PO15826591', 'PENDING'])
            writer.writerow(['PO15873456', 'COMPLETED'])
        
        po_entries = CSVProcessor.read_po_numbers_from_csv(incomplete_csv)
        
        assert len(po_entries) == 2
        assert po_entries[0]['po_number'] == 'PO15826591'
        assert po_entries[0]['status'] == 'PENDING'
        assert po_entries[0]['supplier'] == ''  # Should be empty string
        assert po_entries[0]['attachments_found'] == 0  # Should be 0

    def test_process_po_numbers_valid(self, sample_po_data):
        """Test processing valid PO numbers"""
        valid_entries = CSVProcessor.process_po_numbers(sample_po_data)
        
        # Should only return PENDING POs
        assert len(valid_entries) == 1
        assert valid_entries[0][0] == 'PO15826591'  # display_po
        assert valid_entries[0][1] == '15826591'   # clean_po

    def test_process_po_numbers_invalid(self, test_data_dir):
        """Test processing invalid PO numbers"""
        invalid_data = [
            {
                'po_number': 'invalid_po',
                'status': 'PENDING',
                'supplier': '',
                'attachments_found': 0,
                'attachments_downloaded': 0,
                'last_processed': '',
                'error_message': '',
                'download_folder': '',
                'coupa_url': ''
            },
            {
                'po_number': 'PO123',  # Too short
                'status': 'PENDING',
                'supplier': '',
                'attachments_found': 0,
                'attachments_downloaded': 0,
                'last_processed': '',
                'error_message': '',
                'download_folder': '',
                'coupa_url': ''
            },
            {
                'po_number': 'PO15826591',  # Valid
                'status': 'PENDING',
                'supplier': '',
                'attachments_found': 0,
                'attachments_downloaded': 0,
                'last_processed': '',
                'error_message': '',
                'download_folder': '',
                'coupa_url': ''
            }
        ]
        
        valid_entries = CSVProcessor.process_po_numbers(invalid_data)
        
        # Should only return valid POs
        assert len(valid_entries) == 1
        assert valid_entries[0][0] == 'PO15826591'

    def test_process_po_numbers_without_po_prefix(self, test_data_dir):
        """Test processing PO numbers without PO prefix"""
        data_without_prefix = [
            {
                'po_number': '15826591',  # No PO prefix
                'status': 'PENDING',
                'supplier': '',
                'attachments_found': 0,
                'attachments_downloaded': 0,
                'last_processed': '',
                'error_message': '',
                'download_folder': '',
                'coupa_url': ''
            }
        ]
        
        valid_entries = CSVProcessor.process_po_numbers(data_without_prefix)
        
        assert len(valid_entries) == 1
        assert valid_entries[0][0] == '15826591'  # display_po
        assert valid_entries[0][1] == '15826591'  # clean_po

    def test_csv_file_not_found(self):
        """Test handling of non-existent CSV file"""
        non_existent_file = "/non/existent/file.csv"
        po_entries = CSVProcessor.read_po_numbers_from_csv(non_existent_file)
        
        assert len(po_entries) == 0

    def test_empty_csv_file(self, test_data_dir):
        """Test handling of empty CSV file"""
        empty_csv = os.path.join(test_data_dir, "empty_test.csv")
        with open(empty_csv, 'w', newline='', encoding='utf-8') as f:
            pass  # Create empty file
        
        po_entries = CSVProcessor.read_po_numbers_from_csv(empty_csv)
        
        assert len(po_entries) == 0

    def test_csv_with_empty_rows(self, test_data_dir):
        """Test CSV with empty rows"""
        csv_with_empty_rows = os.path.join(test_data_dir, "empty_rows_test.csv")
        with open(csv_with_empty_rows, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['PO_NUMBER', 'STATUS'])
            writer.writerow(['PO15826591', 'PENDING'])
            writer.writerow([])  # Empty row
            writer.writerow(['', 'PENDING'])  # Empty PO number
            writer.writerow(['PO15873456', 'COMPLETED'])
        
        po_entries = CSVProcessor.read_po_numbers_from_csv(csv_with_empty_rows)
        
        # Should only include rows with valid PO numbers
        assert len(po_entries) == 2
        assert po_entries[0]['po_number'] == 'PO15826591'
        assert po_entries[1]['po_number'] == 'PO15873456'

    def test_csv_with_unicode_characters(self, test_data_dir):
        """Test CSV with Unicode characters"""
        unicode_csv = os.path.join(test_data_dir, "unicode_test.csv")
        with open(unicode_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['PO_NUMBER', 'STATUS', 'SUPPLIER'])
            writer.writerow(['PO15826591', 'PENDING', 'Testé Supplier'])
            writer.writerow(['PO15873456', 'COMPLETED', 'Café & Co.'])
        
        po_entries = CSVProcessor.read_po_numbers_from_csv(unicode_csv)
        
        assert len(po_entries) == 2
        assert po_entries[0]['supplier'] == 'Testé Supplier'
        assert po_entries[1]['supplier'] == 'Café & Co.'

    def test_csv_with_malformed_data(self, test_data_dir):
        """Test CSV with malformed data"""
        malformed_csv = os.path.join(test_data_dir, "malformed_test.csv")
        with open(malformed_csv, 'w', newline='', encoding='utf-8') as f:
            f.write("PO_NUMBER,STATUS\n")
            f.write("PO15826591,PENDING\n")
            f.write("invalid,line,with,too,many,columns\n")
            f.write("PO15873456,COMPLETED\n")
        
        po_entries = CSVProcessor.read_po_numbers_from_csv(malformed_csv)
        
        # Should handle malformed data gracefully
        assert len(po_entries) >= 2  # At least the valid entries should be read

    def test_update_po_status(self, temp_csv_file):
        """Test updating PO status in CSV"""
        # Read initial data
        po_entries = CSVProcessor.read_po_numbers_from_csv(temp_csv_file)
        
        # Update status
        CSVProcessor.update_po_status(
            'PO15826591', 'COMPLETED', 'Test_Supplier', 
            3, 3, '', 'Test_Supplier/', 'https://test.url'
        )
        
        # Read updated data
        updated_entries = CSVProcessor.read_po_numbers_from_csv(temp_csv_file)
        
        # Find the updated entry
        updated_entry = next(e for e in updated_entries if e['po_number'] == 'PO15826591')
        assert updated_entry['status'] == 'COMPLETED'
        assert updated_entry['supplier'] == 'Test_Supplier'
        assert updated_entry['attachments_found'] == 3
        assert updated_entry['attachments_downloaded'] == 3
        assert updated_entry['download_folder'] == 'Test_Supplier/'
        assert updated_entry['coupa_url'] == 'https://test.url'

    def test_update_po_status_not_found(self, temp_csv_file):
        """Test updating status for non-existent PO"""
        # Should not raise exception
        CSVProcessor.update_po_status('NON_EXISTENT_PO', 'COMPLETED')
        
        # Verify file is unchanged
        po_entries = CSVProcessor.read_po_numbers_from_csv(temp_csv_file)
        assert len(po_entries) == 3  # Should still have 3 entries

    def test_write_enhanced_csv(self, test_data_dir):
        """Test writing enhanced CSV format"""
        test_csv = os.path.join(test_data_dir, "write_test.csv")
        
        # Create sample data
        po_entries = [
            {
                'po_number': 'PO15826591',
                'status': 'PENDING',
                'supplier': '',
                'attachments_found': 0,
                'attachments_downloaded': 0,
                'last_processed': '',
                'error_message': '',
                'download_folder': '',
                'coupa_url': ''
            }
        ]
        
        # Write enhanced CSV
        CSVProcessor.write_enhanced_csv(test_csv, po_entries)
        
        # Verify file was written correctly
        assert os.path.exists(test_csv)
        
        # Read back and verify
        read_entries = CSVProcessor.read_po_numbers_from_csv(test_csv)
        assert len(read_entries) == 1
        assert read_entries[0]['po_number'] == 'PO15826591'

    def test_generate_summary_report(self, temp_csv_file):
        """Test generating summary report"""
        report = CSVProcessor.generate_summary_report(temp_csv_file)
        
        assert report['total_pos'] == 3
        assert report['status_counts']['PENDING'] == 2
        assert report['status_counts']['COMPLETED'] == 1
        assert report['total_attachments_found'] == 3
        assert report['total_attachments_downloaded'] == 3
        assert report['unique_suppliers'] == 1
        assert report['success_rate'] == pytest.approx(33.3, rel=0.1)

    def test_generate_summary_report_empty_file(self, test_data_dir):
        """Test generating summary report for empty file"""
        empty_csv = os.path.join(test_data_dir, "empty_summary_test.csv")
        with open(empty_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['PO_NUMBER', 'STATUS'])
        
        report = CSVProcessor.generate_summary_report(empty_csv)
        
        assert report['total_pos'] == 0
        assert report['success_rate'] == 0
        assert len(report['status_counts']) == 0

    def test_backup_csv(self, temp_csv_file):
        """Test CSV backup functionality"""
        backup_path = CSVProcessor.backup_csv()
        
        assert os.path.exists(backup_path)
        assert backup_path.endswith('.csv')
        assert 'backup' in backup_path.lower()
        
        # Verify backup contains same data
        original_entries = CSVProcessor.read_po_numbers_from_csv(temp_csv_file)
        backup_entries = CSVProcessor.read_po_numbers_from_csv(backup_path)
        
        assert len(original_entries) == len(backup_entries)
        
        # Cleanup
        if os.path.exists(backup_path):
            os.unlink(backup_path)

    def test_csv_encoding_handling(self, test_data_dir):
        """Test CSV encoding handling"""
        # Test with different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1']
        
        for encoding in encodings:
            test_csv = os.path.join(test_data_dir, f"encoding_test_{encoding}.csv")
            
            with open(test_csv, 'w', newline='', encoding=encoding) as f:
                writer = csv.writer(f)
                writer.writerow(['PO_NUMBER', 'STATUS'])
                writer.writerow(['PO15826591', 'PENDING'])
            
            # Should handle encoding gracefully
            po_entries = CSVProcessor.read_po_numbers_from_csv(test_csv)
            assert len(po_entries) == 1

    def test_csv_with_special_characters(self, test_data_dir):
        """Test CSV with special characters in data"""
        special_csv = os.path.join(test_data_dir, "special_chars_test.csv")
        with open(special_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['PO_NUMBER', 'STATUS', 'ERROR_MESSAGE'])
            writer.writerow(['PO15826591', 'FAILED', 'Error: "Quote" and \'apostrophe\''])
            writer.writerow(['PO15873456', 'COMPLETED', 'Success!'])
        
        po_entries = CSVProcessor.read_po_numbers_from_csv(special_csv)
        
        assert len(po_entries) == 2
        assert 'Quote' in po_entries[0]['error_message']
        assert 'apostrophe' in po_entries[0]['error_message']

    def test_csv_performance_large_file(self, test_data_dir, performance_timer):
        """Test CSV processing performance with large file"""
        large_csv = os.path.join(test_data_dir, "large_test.csv")
        
        # Create large CSV file
        with open(large_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['PO_NUMBER', 'STATUS', 'SUPPLIER'])
            
            for i in range(1000):  # 1000 rows
                writer.writerow([f'PO{15826591 + i}', 'PENDING', f'Supplier_{i % 10}'])
        
        # Measure performance
        performance_timer.start()
        po_entries = CSVProcessor.read_po_numbers_from_csv(large_csv)
        performance_timer.stop()
        
        assert len(po_entries) == 1000
        assert performance_timer.elapsed() < 5.0  # Should complete in under 5 seconds

    def test_csv_concurrent_access(self, temp_csv_file):
        """Test CSV concurrent access handling"""
        import threading
        import time
        
        results = []
        errors = []
        
        def read_csv():
            try:
                entries = CSVProcessor.read_po_numbers_from_csv(temp_csv_file)
                results.append(len(entries))
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads reading the same CSV
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=read_csv)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All threads should succeed
        assert len(errors) == 0
        assert all(count == 3 for count in results)  # All should read 3 entries 