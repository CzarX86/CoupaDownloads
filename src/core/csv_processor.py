"""
CSV processor module for Coupa Downloads automation.
Handles CSV file reading and PO number processing.
"""

import csv
import os
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from .config import Config


class CSVProcessor:
    """Handles reading PO numbers from CSV and updating progress."""

    @staticmethod
    def get_csv_file_path() -> str:
        """Get the full path to the input CSV file."""
        # Navigate from src/core/ to project root, then to data/input/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        return os.path.join(project_root, "CoupaDownloads", "data", "input", "input.csv")

    @staticmethod
    def read_po_numbers_from_csv(csv_file_path: str) -> List[Dict[str, Any]]:
        """
        Read PO numbers from CSV file and return enhanced data structure.
        
        Returns:
            List of dictionaries with PO data and status information
        """
        po_entries = []
        
        try:
            with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                # Detect if file has headers
                sample = csvfile.read(1024)
                csvfile.seek(0)
                
                # Check if file has the new enhanced format
                has_enhanced_headers = 'STATUS' in sample.upper()
                
                if has_enhanced_headers:
                    # Read enhanced CSV format
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        po_entries.append({
                            'po_number': (row.get('PO_NUMBER') or '').strip(),
                            'status': (row.get('STATUS') or 'PENDING').strip(),
                            'supplier': (row.get('SUPPLIER') or '').strip(),
                            'attachments_found': int(row.get('ATTACHMENTS_FOUND') or 0),
                            'attachments_downloaded': int(row.get('ATTACHMENTS_DOWNLOADED') or 0),
                            'last_processed': (row.get('LAST_PROCESSED') or '').strip(),
                            'error_message': (row.get('ERROR_MESSAGE') or '').strip(),
                            'download_folder': (row.get('DOWNLOAD_FOLDER') or '').strip(),
                            'coupa_url': (row.get('COUPA_URL') or '').strip()
                        })
                else:
                    # Read simple CSV format and convert to enhanced
                    reader = csv.reader(csvfile)
                    headers = next(reader, [])  # Skip header row
                    
                    for row in reader:
                        if row and len(row) > 0 and (row[0] or '').strip():  # Skip empty rows
                            po_entries.append({
                                'po_number': (row[0] or '').strip(),
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
            print(f"❌ CSV file not found: {csv_file_path}")
            return []
        except Exception as e:
            print(f"❌ Error reading CSV file: {e}")
            return []

        print(f"📊 Read {len(po_entries)} PO entries from CSV")
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
            
            if not po_number:
                continue
                
            # Skip already completed POs unless forced reprocessing
            if status == 'COMPLETED':
                print(f"  ⏭️ Skipping {po_number} (already completed)")
                skipped_count += 1
                continue
            
            # Clean PO number (remove PO or PM prefix if present; case-insensitive)
            display_po = po_number
            up = (po_number or '').upper()
            clean_po = po_number[2:] if up.startswith(("PO", "PM")) else po_number
            
            # Validate PO number format
            if clean_po.isdigit() and len(clean_po) >= 6:
                valid_entries.append((display_po, clean_po))
                print(f"  ✅ {display_po} → Will process")
            else:
                print(f"  ❌ Invalid PO format: {po_number}")
                # Update status to FAILED
                # Generate URL even for invalid PO for reference
                up = (po_number or '').upper()
                clean_po_attempt = po_number[2:] if up.startswith(("PO", "PM")) else po_number
                invalid_url = Config.BASE_URL.format(clean_po_attempt)
                CSVProcessor.update_po_status(po_number, 'FAILED', error_message='Invalid PO format', coupa_url=invalid_url)
        
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
        Update the status of a specific PO in the CSV file.
        
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
        csv_file_path = CSVProcessor.get_csv_file_path()
        
        try:
            # Read all entries
            po_entries = CSVProcessor.read_po_numbers_from_csv(csv_file_path)
            
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
                print(f"⚠️ PO {po_number} not found in CSV for status update")
                return
            
            # Write back to CSV
            CSVProcessor.write_enhanced_csv(csv_file_path, po_entries)
            
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
    def write_enhanced_csv(csv_file_path: str, po_entries: List[Dict[str, Any]]) -> None:
        """
        Write the enhanced CSV format with all tracking columns.
        
        Args:
            csv_file_path: Path to CSV file
            po_entries: List of PO entry dictionaries
        """
        headers = [
            'PO_NUMBER', 'STATUS', 'SUPPLIER', 'ATTACHMENTS_FOUND', 
            'ATTACHMENTS_DOWNLOADED', 'LAST_PROCESSED', 'ERROR_MESSAGE', 'DOWNLOAD_FOLDER', 'COUPA_URL'
        ]
        
        try:
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                for entry in po_entries:
                    writer.writerow({
                        'PO_NUMBER': entry['po_number'],
                        'STATUS': entry['status'],
                        'SUPPLIER': entry['supplier'],
                        'ATTACHMENTS_FOUND': entry['attachments_found'],
                        'ATTACHMENTS_DOWNLOADED': entry['attachments_downloaded'],
                        'LAST_PROCESSED': entry['last_processed'],
                        'ERROR_MESSAGE': entry['error_message'],
                        'DOWNLOAD_FOLDER': entry['download_folder'],
                        'COUPA_URL': entry['coupa_url']
                    })
                    
        except Exception as e:
            print(f"❌ Error writing enhanced CSV: {e}")

    @staticmethod
    def generate_summary_report(csv_file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a summary report of processing results.
        
        Returns:
            Dictionary with summary statistics
        """
        if csv_file_path is None:
            csv_file_path = CSVProcessor.get_csv_file_path()
            
        po_entries = CSVProcessor.read_po_numbers_from_csv(csv_file_path)
        
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
        report = CSVProcessor.generate_summary_report()
        
        print("\n" + "="*60)
        print("📊 PROCESSING SUMMARY REPORT")
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
    def backup_csv() -> str:
        """
        Create a backup of the current CSV file.
        
        Returns:
            Path to backup file
        """
        csv_file_path = CSVProcessor.get_csv_file_path()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create backups directory if it doesn't exist
        backups_dir = os.path.join(os.path.dirname(csv_file_path), 'backups')
        os.makedirs(backups_dir, exist_ok=True)
        
        # Create backup filename and path
        backup_filename = f'input_backup_{timestamp}.csv'
        backup_path = os.path.join(backups_dir, backup_filename)
        
        try:
            import shutil
            shutil.copy2(csv_file_path, backup_path)
            print(f"💾 CSV backup created: {backup_filename}")
            return backup_path
        except Exception as e:
            print(f"⚠️ Could not create CSV backup: {e}")
            return "" 
