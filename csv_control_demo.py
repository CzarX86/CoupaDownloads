#!/usr/bin/env python3
"""
Basic CSV Control System Demo
Demonstrates the concept without browser complexity.
"""

import os
import csv
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List

# Import control configuration
import sys
sys.path.append('src/utils/parallel_test')
from control_config import DOWNLOAD_CONTROL_DEMO_CSV


@dataclass
class DownloadRecord:
    """Represents a single download record."""
    po_number: str
    tab_id: str
    file_name: str
    status: str = "PENDING"  # PENDING, DOWNLOADING, COMPLETED, FAILED
    download_start_time: str = ""
    download_complete_time: str = ""
    target_folder: str = ""
    error_message: str = ""


class CSVControlDemo:
    """Demo of CSV control system."""
    
    def __init__(self, csv_path: str = str(DOWNLOAD_CONTROL_DEMO_CSV)):
        self.csv_path = csv_path
        self.downloads: Dict[str, DownloadRecord] = {}
        self._clear_csv_file()  # Clear CSV before starting
        print(f"🧹 Cleared CSV file: {os.path.abspath(self.csv_path)}")
    
    def _clear_csv_file(self):
        """Clear the CSV file before starting execution."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            
            # Clear the file content
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
                # Write only header
                fieldnames = ['po_number', 'tab_id', 'file_name', 'status', 'download_start_time', 'download_complete_time', 'target_folder', 'error_message']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
            
            print(f"   📄 Created empty CSV with headers")
            
        except Exception as e:
            print(f"   ⚠️ Warning: Could not clear CSV file: {e}")
    
    def _create_sample_data(self):
        """Create sample download records."""
        sample_data = [
            {
                "po_number": "PO16518898",
                "tab_id": "TAB_001",
                "file_name": "2025_TG_CAT_Enhancements_01Jan-31Mar_SoW.pdf",
                "status": "DOWNLOADING",
                "download_start_time": datetime.now().isoformat(),
                "target_folder": "/Users/juliocezar/Downloads/CoupaDownloads/P2/Others/Trade/THOROGOOD_ASSOCIATES_LIMITED/PO16518898_Success"
            },
            {
                "po_number": "PO16518898",
                "tab_id": "TAB_001", 
                "file_name": "2025_TG_CAT_Enhancements_01Jan-31Mar_SoW (1).pdf",
                "status": "COMPLETED",
                "download_start_time": "2024-09-03T00:56:12",
                "download_complete_time": "2024-09-03T00:56:15",
                "target_folder": "/Users/juliocezar/Downloads/CoupaDownloads/P2/Others/Trade/THOROGOOD_ASSOCIATES_LIMITED/PO16518898_Success"
            },
            {
                "po_number": "PO16928033",
                "tab_id": "TAB_002",
                "file_name": "contract_document.pdf",
                "status": "PENDING",
                "target_folder": "/Users/juliocezar/Downloads/CoupaDownloads/P2/Others/Trade/EQT_Sonora_Topco_BV/PO16928033_Success"
            }
        ]
        
        for data in sample_data:
            record = DownloadRecord(**data)
            file_key = f"{record.po_number}_{record.file_name}"
            self.downloads[file_key] = record
    
    def save_to_csv(self):
        """Save downloads to CSV."""
        try:
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
                if self.downloads:
                    fieldnames = list(asdict(next(iter(self.downloads.values()))).keys())
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    for record in self.downloads.values():
                        writer.writerow(asdict(record))
            
            print(f"✅ CSV saved to: {os.path.abspath(self.csv_path)}")
            return True
        except Exception as e:
            print(f"❌ Error saving CSV: {e}")
            return False
    
    def register_download(self, po_number: str, tab_id: str, file_name: str, target_folder: str) -> str:
        """Register a new download."""
        file_key = f"{po_number}_{file_name}"
        
        record = DownloadRecord(
            po_number=po_number,
            tab_id=tab_id,
            file_name=file_name,
            target_folder=target_folder,
            download_start_time=datetime.now().isoformat()
        )
        
        self.downloads[file_key] = record
        self.save_to_csv()
        print(f"   📝 Registered: {file_name} for PO {po_number}")
        return file_key
    
    def update_status(self, file_key: str, status: str):
        """Update download status."""
        if file_key in self.downloads:
            record = self.downloads[file_key]
            record.status = status
            
            if status == "COMPLETED":
                record.download_complete_time = datetime.now().isoformat()
            
            print(f"📊 Updated: {file_key} -> {status}")
            self.save_to_csv()
    
    def get_tab_downloads(self, tab_id: str) -> List[DownloadRecord]:
        """Get all downloads for a specific tab."""
        return [record for record in self.downloads.values() if record.tab_id == tab_id]
    
    def is_tab_complete(self, tab_id: str) -> bool:
        """Check if all downloads for a tab are complete."""
        downloads = self.get_tab_downloads(tab_id)
        if not downloads:
            return True
        return all(d.status in ["COMPLETED", "FAILED"] for d in downloads)
    
    def show_csv_contents(self):
        """Show CSV contents."""
        if os.path.exists(self.csv_path):
            print(f"\n📄 CSV Contents of {os.path.abspath(self.csv_path)}:")
            print("-" * 80)
            with open(self.csv_path, 'r') as f:
                print(f.read())
        else:
            print(f"\n❌ CSV file not found: {os.path.abspath(self.csv_path)}")


def demo_csv_control():
    """Demonstrate CSV control system."""
    print("🧪 CSV Control System Demo")
    print("=" * 50)
    
    # Create demo instance (this will clear the CSV)
    demo = CSVControlDemo()
    
    # Show initial empty state
    print("\n📊 Initial Empty State:")
    demo.show_csv_contents()
    
    # Simulate real execution data
    print("\n🔄 Simulating Real Execution Data:")
    
    # Simulate finding attachments on a page
    print("   🔍 Scanning PO16518898 page for attachments...")
    demo.register_download("PO16518898", "TAB_001", "2025_TG_CAT_Enhancements_01Jan-31Mar_SoW.pdf", "/Users/juliocezar/Downloads/CoupaDownloads/P2/Others/Trade/THOROGOOD_ASSOCIATES_LIMITED/PO16518898_Success")
    demo.register_download("PO16518898", "TAB_001", "2025_TG_CAT_Enhancements_01Jan-31Mar_SoW (1).pdf", "/Users/juliocezar/Downloads/CoupaDownloads/P2/Others/Trade/THOROGOOD_ASSOCIATES_LIMITED/PO16518898_Success")
    
    print("   🔍 Scanning PO16928033 page for attachments...")
    demo.register_download("PO16928033", "TAB_002", "contract_document.pdf", "/Users/juliocezar/Downloads/CoupaDownloads/P2/Others/Trade/EQT_Sonora_Topco_BV/PO16928033_Success")
    
    # Show state after registration
    print("\n📊 State After Registration:")
    demo.show_csv_contents()
    
    # Simulate download progress
    print("\n🔄 Simulating Download Progress:")
    
    # Start downloads
    demo.update_status("PO16518898_2025_TG_CAT_Enhancements_01Jan-31Mar_SoW.pdf", "DOWNLOADING")
    demo.update_status("PO16518898_2025_TG_CAT_Enhancements_01Jan-31Mar_SoW (1).pdf", "DOWNLOADING")
    demo.update_status("PO16928033_contract_document.pdf", "DOWNLOADING")
    
    # Complete some downloads
    demo.update_status("PO16518898_2025_TG_CAT_Enhancements_01Jan-31Mar_SoW (1).pdf", "COMPLETED")
    demo.update_status("PO16928033_contract_document.pdf", "COMPLETED")
    
    # Check tab completion
    print(f"\n📋 Tab TAB_001 complete: {demo.is_tab_complete('TAB_001')}")
    print(f"📋 Tab TAB_002 complete: {demo.is_tab_complete('TAB_002')}")
    
    # Show final state
    print("\n📊 Final State (Ready for Audit):")
    demo.show_csv_contents()
    
    print("\n✅ CSV Control Demo completed!")
    print("📄 CSV file preserved for audit at:", os.path.abspath(demo.csv_path))


if __name__ == "__main__":
    demo_csv_control()
