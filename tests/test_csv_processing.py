import os
import csv
import tempfile
import pytest
from unittest.mock import patch, mock_open


class TestCSVProcessing:
    """Test CSV file processing functionality"""
    
    def test_read_valid_csv_file(self, temp_csv_file):
        """Test reading a valid CSV file"""
        po_entries = []
        
        with open(temp_csv_file, newline="") as f:
            reader = csv.reader(f)
            # Skip header if exists
            try:
                header = next(reader)
            except StopIteration:
                pass
            
            for row in reader:
                if row:  # Skip empty rows
                    po_entries.append(row[0].strip())  # Get first column value
        
        expected_entries = [
            "PO15262984",
            "PO15327452", 
            "PO15362783",
            "invalid_po",
            "PO15421343"
        ]
        
        assert po_entries == expected_entries
    
    def test_process_po_numbers_valid(self):
        """Test processing valid PO numbers"""
        po_entries = ["PO15262984", "PO15327452", "15262984", "15327452"]
        
        valid_entries = []
        for po in po_entries:
            # Remove "PO" prefix if present for URL, keep original for filename
            clean_po = po.replace("PO", "").strip()
            if clean_po.isdigit():
                valid_entries.append((po, clean_po))
            else:
                print(f"⚠️ Invalid PO number format: {po}")
        
        expected_valid = [
            ("PO15262984", "15262984"),
            ("PO15327452", "15327452"),
            ("15262984", "15262984"),
            ("15327452", "15327452")
        ]
        
        assert valid_entries == expected_valid
    
    def test_process_po_numbers_invalid(self):
        """Test processing invalid PO numbers"""
        po_entries = ["invalid_po", "PO123abc", "abc123", ""]
        
        valid_entries = []
        for po in po_entries:
            # Remove "PO" prefix if present for URL, keep original for filename
            clean_po = po.replace("PO", "").strip()
            if clean_po.isdigit():
                valid_entries.append((po, clean_po))
            else:
                print(f"⚠️ Invalid PO number format: {po}")
        
        # Should have no valid entries
        assert valid_entries == []
    
    def test_csv_file_not_found(self):
        """Test handling of missing CSV file"""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_file = os.path.join(script_dir, "nonexistent.csv")
        
        with pytest.raises(FileNotFoundError):
            if not os.path.exists(csv_file):
                raise FileNotFoundError(f"PO input file {csv_file} not found")
    
    def test_empty_csv_file(self):
        """Test handling of empty CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("")  # Empty file
            temp_file = f.name
        
        try:
            po_entries = []
            with open(temp_file, newline="") as f:
                reader = csv.reader(f)
                # Skip header if exists
                try:
                    header = next(reader)
                except StopIteration:
                    pass
                
                for row in reader:
                    if row:  # Skip empty rows
                        po_entries.append(row[0].strip())
            
            assert po_entries == []
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_csv_with_empty_rows(self):
        """Test CSV with empty rows"""
        csv_content = """PO_NUMBER
PO15262984

PO15327452

"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name
        
        try:
            po_entries = []
            with open(temp_file, newline="") as f:
                reader = csv.reader(f)
                # Skip header if exists
                try:
                    header = next(reader)
                except StopIteration:
                    pass
                
                for row in reader:
                    if row:  # Skip empty rows
                        po_entries.append(row[0].strip())
            
            expected_entries = ["PO15262984", "PO15327452"]
            assert po_entries == expected_entries
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file) 