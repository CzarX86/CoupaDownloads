"""
Unified processor module for Coupa Downloads automation.
Automatically detects and handles both CSV and Excel input files.
"""

import os
import pandas as pd
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional, Union
from .config import Config
from .csv_processor import CSVProcessor
from .excel_processor import ExcelProcessor


class UnifiedProcessor:
    """Unified processor that handles both CSV and Excel files automatically."""

    @staticmethod
    def detect_input_file() -> str:
        """
        Detect which input file exists (CSV or Excel).
        
        Returns:
            Path to the detected input file
        """
        # Get paths for both file types
        csv_path = CSVProcessor.get_csv_file_path()
        excel_path = ExcelProcessor.get_excel_file_path()
        
        # Check which file exists
        if os.path.exists(excel_path):
            print(f"📊 Detected Excel input file: {os.path.basename(excel_path)}")
            return excel_path
        elif os.path.exists(csv_path):
            print(f"📊 Detected CSV input file: {os.path.basename(csv_path)}")
            return csv_path
        else:
            # If neither exists, default to CSV path for error handling
            print(f"❌ No input file found. Expected either:")
            print(f"   📁 {csv_path}")
            print(f"   📁 {excel_path}")
            return csv_path

    @staticmethod
    def get_file_type(file_path: str) -> str:
        """
        Determine the file type based on extension.
        
        Returns:
            'csv' or 'excel'
        """
        if file_path.lower().endswith('.xlsx') or file_path.lower().endswith('.xls'):
            return 'excel'
        else:
            return 'csv'

    @staticmethod
    def read_po_numbers(file_path: str) -> List[Dict[str, Any]]:
        """
        Read PO numbers from file (CSV or Excel) and return enhanced data structure.
        
        Args:
            file_path: Path to input file
            
        Returns:
            List of dictionaries with PO data and status information
        """
        file_type = UnifiedProcessor.get_file_type(file_path)
        
        if file_type == 'excel':
            return ExcelProcessor.read_po_numbers_from_excel(file_path)
        else:
            return CSVProcessor.read_po_numbers_from_csv(file_path)

    @staticmethod
    def process_po_numbers(file_path: str) -> List[Tuple[str, str]]:
        """
        Process and validate PO numbers from file (CSV or Excel).
        
        Args:
            file_path: Path to input file
            
        Returns:
            List of tuples: (display_po, clean_po) for processing
        """
        file_type = UnifiedProcessor.get_file_type(file_path)
        po_entries = UnifiedProcessor.read_po_numbers(file_path)
        
        if file_type == 'excel':
            return ExcelProcessor.process_po_numbers(po_entries)
        else:
            return CSVProcessor.process_po_numbers(po_entries)

    @staticmethod
    def update_po_status(po_number: str, status: str, supplier: str = '', 
                        attachments_found: int = 0, attachments_downloaded: int = 0,
                        error_message: str = '', download_folder: str = '', 
                        coupa_url: str = '') -> None:
        """
        Update the status of a specific PO in the input file.
        
        Args:
            po_number: PO number to update
            status: New status (PENDING, COMPLETED, FAILED, etc.)
            supplier: Supplier name
            attachments_found: Number of attachments found
            attachments_downloaded: Number of attachments downloaded
            error_message: Error message if applicable
            download_folder: Folder where files were saved
            coupa_url: Full URL to the PO page
        """
        file_path = UnifiedProcessor.detect_input_file()
        file_type = UnifiedProcessor.get_file_type(file_path)
        
        if file_type == 'excel':
            ExcelProcessor.update_po_status(po_number, status, supplier, 
                                          attachments_found, attachments_downloaded,
                                          error_message, download_folder, coupa_url)
        else:
            CSVProcessor.update_po_status(po_number, status, supplier, 
                                        attachments_found, attachments_downloaded,
                                        error_message, download_folder, coupa_url)

    @staticmethod
    def generate_summary_report(file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a summary report of processing results.
        
        Args:
            file_path: Optional path to input file
            
        Returns:
            Dictionary with summary statistics
        """
        if file_path is None:
            file_path = UnifiedProcessor.detect_input_file()
            
        file_type = UnifiedProcessor.get_file_type(file_path)
        
        if file_type == 'excel':
            return ExcelProcessor.generate_summary_report(file_path)
        else:
            return CSVProcessor.generate_summary_report(file_path)

    @staticmethod
    def print_summary_report() -> None:
        """Print a formatted summary report to console."""
        file_path = UnifiedProcessor.detect_input_file()
        file_type = UnifiedProcessor.get_file_type(file_path)
        
        if file_type == 'excel':
            ExcelProcessor.print_summary_report()
        else:
            CSVProcessor.print_summary_report()

    @staticmethod
    def backup_file() -> str:
        """
        Create a backup of the current input file.
        
        Returns:
            Path to backup file
        """
        file_path = UnifiedProcessor.detect_input_file()
        file_type = UnifiedProcessor.get_file_type(file_path)
        
        if file_type == 'excel':
            return ExcelProcessor.backup_excel()
        else:
            return CSVProcessor.backup_csv()

    @staticmethod
    def convert_file_format(input_path: str, output_path: str) -> None:
        """
        Convert between CSV and Excel formats.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
        """
        input_type = UnifiedProcessor.get_file_type(input_path)
        output_type = UnifiedProcessor.get_file_type(output_path)
        
        if input_type == 'csv' and output_type == 'excel':
            ExcelProcessor.convert_csv_to_excel(input_path, output_path)
        elif input_type == 'excel' and output_type == 'csv':
            # Read Excel and write to CSV
            po_entries = ExcelProcessor.read_po_numbers_from_excel(input_path)
            CSVProcessor.write_enhanced_csv(output_path, po_entries)
            print(f"✅ Converted Excel to CSV: {output_path}")
        else:
            print(f"❌ Unsupported conversion: {input_type} to {output_type}")

    @staticmethod
    def create_sample_excel_file() -> str:
        """
        Create a sample Excel file with the same data as the current CSV.
        
        Returns:
            Path to created Excel file
        """
        csv_path = CSVProcessor.get_csv_file_path()
        excel_path = ExcelProcessor.get_excel_file_path()
        
        if os.path.exists(csv_path):
            ExcelProcessor.convert_csv_to_excel(csv_path, excel_path)
            print(f"✅ Created sample Excel file: {excel_path}")
            return excel_path
        else:
            print(f"❌ No CSV file found to convert: {csv_path}")
            return ""

    @staticmethod
    def get_processor_info() -> Dict[str, Any]:
        """
        Get information about available processors and detected files.
        
        Returns:
            Dictionary with processor information
        """
        csv_path = CSVProcessor.get_csv_file_path()
        excel_path = ExcelProcessor.get_excel_file_path()
        
        csv_exists = os.path.exists(csv_path)
        excel_exists = os.path.exists(excel_path)
        
        detected_file = UnifiedProcessor.detect_input_file()
        file_type = UnifiedProcessor.get_file_type(detected_file)
        
        return {
            'csv_path': csv_path,
            'excel_path': excel_path,
            'csv_exists': csv_exists,
            'excel_exists': excel_exists,
            'detected_file': detected_file,
            'detected_type': file_type,
            'file_size': os.path.getsize(detected_file) if os.path.exists(detected_file) else 0
        } 