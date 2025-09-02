"""
Excel processor module for Coupa Downloads automation.
Handles Excel file reading and PO number processing.
"""

import os
import pandas as pd
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from .config import Config


class ExcelProcessor:
    """Handles reading PO numbers from Excel and updating progress."""

    @staticmethod
    def get_excel_file_path() -> str:
        """Get the full path to the input Excel file."""
        # Navigate from src/core/ to project root, then to data/input/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        return os.path.join(project_root, "CoupaDownloads", "data", "input", "input.xlsx")

    @staticmethod
    def read_po_numbers_from_excel(excel_file_path: str) -> List[Dict[str, Any]]:
        """
        Read PO numbers from Excel file and return enhanced data structure.
        
        Returns:
            List of dictionaries with PO data and status information
        """
        po_entries = []
        
        try:
            # Read Excel file using pandas
            df = pd.read_excel(excel_file_path, engine='openpyxl')
            
            # Fill NaN values with appropriate defaults
            df = df.fillna({
                'STATUS': 'PENDING',
                'SUPPLIER': '',
                'ATTACHMENTS_FOUND': 0,
                'ATTACHMENTS_DOWNLOADED': 0,
                'LAST_PROCESSED': '',
                'ERROR_MESSAGE': '',
                'DOWNLOAD_FOLDER': '',
                'COUPA_URL': ''
            })
            
            # Check if file has the enhanced format with STATUS column
            has_enhanced_headers = 'STATUS' in df.columns
            
            if has_enhanced_headers:
                # Read enhanced Excel format
                for _, row in df.iterrows():
                    po_number = str(row.get('PO_NUMBER', '')).strip()
                    if not po_number or po_number == 'nan':
                        continue
                        
                    po_entries.append({
                        'po_number': po_number,
                        'status': str(row.get('STATUS', 'PENDING')).strip(),
                        'supplier': str(row.get('SUPPLIER', '')).strip(),
                        'attachments_found': int(row.get('ATTACHMENTS_FOUND', 0)),
                        'attachments_downloaded': int(row.get('ATTACHMENTS_DOWNLOADED', 0)),
                        'last_processed': str(row.get('LAST_PROCESSED', '')).strip(),
                        'error_message': str(row.get('ERROR_MESSAGE', '')).strip(),
                        'download_folder': str(row.get('DOWNLOAD_FOLDER', '')).strip(),
                        'coupa_url': str(row.get('COUPA_URL', '')).strip()
                    })
            else:
                # Read simple Excel format and convert to enhanced
                # Assume first column contains PO numbers
                po_column = df.columns[0] if len(df.columns) > 0 else 'PO_NUMBER'
                
                for _, row in df.iterrows():
                    po_number = str(row.get(po_column, '')).strip()
                    if po_number and po_number != 'nan' and po_number:  # Skip empty rows
                        po_entries.append({
                            'po_number': po_number,
                            'status': 'PENDING',
                            'supplier': '',
                            'attachments_found': 0,
                            'attachments_downloaded': 0,
                            'last_processed': '',
                            'error_message': '',
                            'download_folder': '',
                            'coupa_url': ''
                        })
                            
        except FileNotFoundError:
            print(f"❌ Excel file not found: {excel_file_path}")
            return []
        except Exception as e:
            print(f"❌ Error reading Excel file: {e}")
            return []

        print(f"📊 Read {len(po_entries)} PO entries from Excel")
        return po_entries

    @staticmethod
    def process_po_numbers(po_entries: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
        """
        Process and validate PO numbers, filtering out already completed ones.
        
        Returns:
            List of tuples: (display_po, clean_po) for processing
        """
        valid_entries = []
        skipped_count = 0
        
        for entry in po_entries:
            po_number = entry['po_number']
            status = entry['status']
            
            if not po_number or po_number == 'nan':
                continue
                
            # Skip already completed POs unless forced reprocessing
            if status == 'COMPLETED':
                print(f"  ⏭️ Skipping {po_number} (already completed)")
                skipped_count += 1
                continue
            
            # Clean PO number (remove PO prefix if present)
            display_po = po_number
            clean_po = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
            
            # Validate PO number format
            if clean_po.isdigit() and len(clean_po) >= 6:
                valid_entries.append((display_po, clean_po))
                print(f"  ✅ {display_po} → Will process")
            else:
                print(f"  ❌ Invalid PO format: {po_number}")
                # Update status to FAILED
                # Generate URL even for invalid PO for reference
                clean_po_attempt = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
                invalid_url = Config.BASE_URL.format(clean_po_attempt)
                ExcelProcessor.update_po_status(po_number, 'FAILED', error_message='Invalid PO format', coupa_url=invalid_url)
        
        if skipped_count > 0:
            print(f"📊 Skipped {skipped_count} already completed POs")
            
        print(f"📊 {len(valid_entries)} POs ready for processing")
        return valid_entries

    @staticmethod
    def update_po_status(po_number: str, status: str, supplier: str = '', 
                        attachments_found: int = 0, attachments_downloaded: int = 0,
                        error_message: str = '', download_folder: str = '', 
                        coupa_url: str = '') -> None:
        """
        Update the status of a specific PO in the Excel file.
        
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
        excel_file_path = ExcelProcessor.get_excel_file_path()
        
        try:
            # Read all entries
            po_entries = ExcelProcessor.read_po_numbers_from_excel(excel_file_path)
            
            # Find and update the specific PO
            updated = False
            for entry in po_entries:
                if entry['po_number'] == po_number:
                    entry['status'] = status
                    entry['supplier'] = supplier
                    entry['attachments_found'] = attachments_found
                    entry['attachments_downloaded'] = attachments_downloaded
                    entry['last_processed'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    entry['error_message'] = error_message
                    entry['download_folder'] = download_folder
                    entry['coupa_url'] = coupa_url
                    updated = True
                    break
            
            if not updated:
                print(f"⚠️ PO {po_number} not found in Excel for status update")
                return
            
            # Write back to Excel
            ExcelProcessor.write_enhanced_excel(excel_file_path, po_entries)
            
            # Print status update
            status_emoji = {
                'COMPLETED': '✅',
                'FAILED': '❌', 
                'PARTIAL': '⚠️',
                'PENDING': '⏳',
                'SKIPPED': '⏭️',
                'NO_ATTACHMENTS': '📭'
            }.get(status, '📋')
            
            print(f"  {status_emoji} Updated {po_number}: {status}")
            
        except Exception as e:
            print(f"❌ Error updating PO status: {e}")

    @staticmethod
    def write_enhanced_excel(excel_file_path: str, po_entries: List[Dict[str, Any]]) -> None:
        """
        Write the enhanced Excel format with all tracking columns.
        
        Args:
            excel_file_path: Path to Excel file
            po_entries: List of PO entry dictionaries
        """
        try:
            # Create DataFrame
            df = pd.DataFrame([
                {
                    'PO_NUMBER': entry['po_number'],
                    'STATUS': entry['status'],
                    'SUPPLIER': entry['supplier'],
                    'ATTACHMENTS_FOUND': entry['attachments_found'],
                    'ATTACHMENTS_DOWNLOADED': entry['attachments_downloaded'],
                    'LAST_PROCESSED': entry['last_processed'],
                    'ERROR_MESSAGE': entry['error_message'],
                    'DOWNLOAD_FOLDER': entry['download_folder'],
                    'COUPA_URL': entry['coupa_url']
                }
                for entry in po_entries
            ])
            
            # Write to Excel with formatting
            with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='PO_Data', index=False)
                
                # Apply formatting
                ExcelProcessor._apply_excel_formatting(writer, df)
                    
        except Exception as e:
            print(f"❌ Error writing enhanced Excel: {e}")

    @staticmethod
    def _apply_excel_formatting(writer: pd.ExcelWriter, df: pd.DataFrame) -> None:
        """Apply professional formatting to Excel file."""
        try:
            from openpyxl import load_workbook
            from openpyxl.styles import PatternFill, Font, Alignment
            from openpyxl.utils.dataframe import dataframe_to_rows
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['PO_Data']
            
            # Style header row
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
            
            # Conditional formatting for status column
            green_fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')
            red_fill = PatternFill(start_color='FFB6C1', end_color='FFB6C1', fill_type='solid')
            yellow_fill = PatternFill(start_color='FFFF99', end_color='FFFF99', fill_type='solid')
            
            # Apply conditional formatting to status column (column B)
            status_col = 'B'
            for row in range(2, worksheet.max_row + 1):
                cell = worksheet[f'{status_col}{row}']
                if cell.value == 'COMPLETED':
                    cell.fill = green_fill
                elif cell.value == 'FAILED':
                    cell.fill = red_fill
                elif cell.value == 'PENDING':
                    cell.fill = yellow_fill
                    
        except ImportError:
            print("⚠️ openpyxl not available - skipping formatting")
        except Exception as e:
            print(f"⚠️ Error applying formatting: {e}")

    @staticmethod
    def generate_summary_report(excel_file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a summary report of processing results.
        
        Returns:
            Dictionary with summary statistics
        """
        if excel_file_path is None:
            excel_file_path = ExcelProcessor.get_excel_file_path()
            
        po_entries = ExcelProcessor.read_po_numbers_from_excel(excel_file_path)
        
        # Count by status
        status_counts = {}
        total_attachments_found = 0
        total_attachments_downloaded = 0
        suppliers = set()
        
        for entry in po_entries:
            status = entry['status']
            status_counts[status] = status_counts.get(status, 0) + 1
            total_attachments_found += entry['attachments_found']
            total_attachments_downloaded += entry['attachments_downloaded']
            
            if entry['supplier']:
                suppliers.add(entry['supplier'])
        
        return {
            'total_pos': len(po_entries),
            'status_counts': status_counts,
            'total_attachments_found': total_attachments_found,
            'total_attachments_downloaded': total_attachments_downloaded,
            'unique_suppliers': len(suppliers),
            'supplier_list': sorted(list(suppliers)),
            'success_rate': round((status_counts.get('COMPLETED', 0) / len(po_entries)) * 100, 1) if po_entries else 0
        }

    @staticmethod
    def print_summary_report() -> None:
        """Print a formatted summary report to console."""
        report = ExcelProcessor.generate_summary_report()
        
        print("\n" + "="*60)
        print("📊 PROCESSING SUMMARY REPORT (Excel)")
        print("="*60)
        
        print(f"📋 Total POs: {report['total_pos']}")
        print(f"🎯 Success Rate: {report['success_rate']}%")
        
        print(f"\n📈 Status Breakdown:")
        for status, count in report['status_counts'].items():
            emoji = {
                'COMPLETED': '✅', 'FAILED': '❌', 'PARTIAL': '⚠️',
                'PENDING': '⏳', 'SKIPPED': '⏭️', 'NO_ATTACHMENTS': '📭'
            }.get(status, '📋')
            print(f"  {emoji} {status}: {count}")
        
        print(f"\n📎 Attachments:")
        print(f"  🔍 Found: {report['total_attachments_found']}")
        print(f"  💾 Downloaded: {report['total_attachments_downloaded']}")
        
        if report['unique_suppliers'] > 0:
            print(f"\n🏢 Suppliers: {report['unique_suppliers']} unique")
            for supplier in report['supplier_list'][:10]:  # Show first 10
                print(f"  📁 {supplier}")
            if len(report['supplier_list']) > 10:
                print(f"  ... and {len(report['supplier_list']) - 10} more")
        
        print("="*60)

    @staticmethod
    def backup_excel() -> str:
        """
        Create a backup of the current Excel file.
        
        Returns:
            Path to backup file
        """
        excel_file_path = ExcelProcessor.get_excel_file_path()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create backups directory if it doesn't exist
        backups_dir = os.path.join(os.path.dirname(excel_file_path), 'backups')
        os.makedirs(backups_dir, exist_ok=True)
        
        # Create backup filename and path
        backup_filename = f'input_backup_{timestamp}.xlsx'
        backup_path = os.path.join(backups_dir, backup_filename)
        
        try:
            import shutil
            shutil.copy2(excel_file_path, backup_path)
            print(f"💾 Excel backup created: {backup_filename}")
            return backup_path
        except Exception as e:
            print(f"⚠️ Could not create Excel backup: {e}")
            return ""

    @staticmethod
    def convert_csv_to_excel(csv_file_path: str, excel_file_path: str) -> None:
        """
        Convert CSV file to Excel format.
        
        Args:
            csv_file_path: Path to input CSV file
            excel_file_path: Path to output Excel file
        """
        try:
            # Read CSV using pandas
            df = pd.read_csv(csv_file_path)
            
            # Write to Excel with formatting
            with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='PO_Data', index=False)
                
                # Apply formatting
                ExcelProcessor._apply_excel_formatting(writer, df)
            
            print(f"✅ Converted CSV to Excel: {excel_file_path}")
            
        except Exception as e:
            print(f"❌ Error converting CSV to Excel: {e}") 