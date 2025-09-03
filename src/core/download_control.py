import os
import csv
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path

from .config import Config


@dataclass
class DownloadRecord:
    """Record for tracking individual file downloads."""
    po_number: str
    tab_id: str
    file_name: str
    status: str = "PENDING"  # PENDING, DOWNLOADING, COMPLETED, ERROR
    download_start_time: Optional[str] = None
    download_complete_time: Optional[str] = None
    target_folder: Optional[str] = None
    error_message: Optional[str] = None


class DownloadControlManager:
    """Manages download tracking via CSV file."""
    
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            # Create data/control directory if it doesn't exist
            control_dir = Path("data/control")
            control_dir.mkdir(parents=True, exist_ok=True)
            self.csv_path = str(control_dir / "download_control.csv")
        else:
            self.csv_path = csv_path
        
        self.downloads: Dict[str, DownloadRecord] = {}
        self._clear_csv_file()
        print(f"🧹 Initialized download control: {os.path.abspath(self.csv_path)}")
    
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
    
    def _save_to_csv(self):
        """Save all download records to CSV."""
        try:
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
                fieldnames = ['po_number', 'tab_id', 'file_name', 'status', 'download_start_time', 'download_complete_time', 'target_folder', 'error_message']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                
                for record in self.downloads.values():
                    writer.writerow(asdict(record))
            
            print(f"✅ CSV updated: {os.path.abspath(self.csv_path)}")
            
        except Exception as e:
            print(f"❌ Error saving to CSV: {e}")
    
    def register_download(self, po_number: str, tab_id: str, file_name: str, target_folder: str, index: int = 0) -> str:
        """Register a new download for tracking."""
        # Create unique key using index to handle duplicate filenames
        file_key = f"{po_number}_{file_name}_{index}"
        
        record = DownloadRecord(
            po_number=po_number,
            tab_id=tab_id,
            file_name=file_name,
            target_folder=target_folder,
            download_start_time=datetime.now().isoformat()
        )
        
        self.downloads[file_key] = record
        self._save_to_csv()
        print(f"   📝 Registered: {file_name} for PO {po_number} (index {index+1})")
        return file_key
    
    def update_download_status(self, file_key: str, status: str, error_message: str = None):
        """Update download status and handle completion."""
        if file_key in self.downloads:
            record = self.downloads[file_key]
            record.status = status
            
            if status == "DOWNLOADING":
                record.download_start_time = datetime.now().isoformat()
            elif status == "COMPLETED":
                record.download_complete_time = datetime.now().isoformat()
            elif status == "ERROR":
                record.error_message = error_message
            
            print(f"📊 Updated: {file_key} -> {status}")
            self._save_to_csv()
    
    def get_tab_downloads(self, tab_id: str) -> List[DownloadRecord]:
        """Get all downloads for a specific tab."""
        return [record for record in self.downloads.values() if record.tab_id == tab_id]
    
    def is_tab_complete(self, tab_id: str) -> bool:
        """Check if all downloads for a tab are completed."""
        tab_downloads = self.get_tab_downloads(tab_id)
        if not tab_downloads:
            return True  # No downloads means tab is complete
        
        return all(record.status in ["COMPLETED", "ERROR"] for record in tab_downloads)
    
    def cleanup_tab(self, tab_id: str):
        """Remove all records for a specific tab."""
        keys_to_remove = [key for key, record in self.downloads.items() if record.tab_id == tab_id]
        for key in keys_to_remove:
            del self.downloads[key]
        
        if keys_to_remove:
            print(f"🧹 Cleaned up {len(keys_to_remove)} records for tab {tab_id}")
            self._save_to_csv()
    
    def get_csv_path(self) -> str:
        """Get the CSV file path."""
        return self.csv_path
    
    def is_po_complete(self, po_number: str) -> bool:
        """Check if all downloads for a PO are completed."""
        po_downloads = [record for record in self.downloads.values() if record.po_number == po_number]
        if not po_downloads:
            return True  # No downloads means PO is complete
        
        return all(record.status in ["COMPLETED", "ERROR"] for record in po_downloads)
    
    def get_po_downloads(self, po_number: str) -> List[DownloadRecord]:
        """Get all downloads for a specific PO."""
        return [record for record in self.downloads.values() if record.po_number == po_number]
    
    def move_completed_po_files(self, po_number: str, final_status: str = "Success") -> bool:
        """Move all completed files for a PO to their final hierarchical folders."""
        po_downloads = self.get_po_downloads(po_number)
        
        if not po_downloads:
            print(f"   ℹ️ No downloads found for PO {po_number}")
            return True
        
        if not self.is_po_complete(po_number):
            print(f"   ⚠️ PO {po_number} downloads not complete yet")
            return False
        
        print(f"   📦 Moving files for PO {po_number} to final folders...")
        
        moved_count = 0
        for record in po_downloads:
            if record.status == "COMPLETED":
                try:
                    # Create final folder path with status suffix
                    final_folder = f"{record.target_folder}_{final_status}"
                    os.makedirs(final_folder, exist_ok=True)
                    
                    # Find the downloaded file in the temporary folder
                    temp_folder = record.target_folder
                    filename = record.file_name
                    
                    # Look for the file in the temp folder
                    temp_file_path = os.path.join(temp_folder, filename)
                    if os.path.exists(temp_file_path):
                        final_file_path = os.path.join(final_folder, filename)
                        os.rename(temp_file_path, final_file_path)
                        print(f"      ✅ Moved: {filename} to {final_folder}")
                        moved_count += 1
                    else:
                        print(f"      ⚠️ File not found: {temp_file_path}")
                        
                except Exception as e:
                    print(f"      ❌ Error moving {record.file_name}: {e}")
        
        print(f"   📦 Moved {moved_count} files for PO {po_number}")
        return moved_count > 0
