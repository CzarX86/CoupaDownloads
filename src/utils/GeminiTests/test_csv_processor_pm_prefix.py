import os
import sys

# Ensure the src directory is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from src.core.csv_processor import CSVProcessor


def test_csv_processor_accepts_pm_prefix():
    entries = [
        {'po_number': 'PM15492200', 'status': 'PENDING'},
        {'po_number': 'PO123456', 'status': 'PENDING'},
    ]
    result = CSVProcessor.process_po_numbers(entries)
    assert ('PM15492200', '15492200') in result
    assert ('PO123456', '123456') in result

