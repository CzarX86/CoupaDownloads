import os
import csv
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path

from config import Config


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
    tab_state: str = "OPEN"  # OPEN, CLOSED


class DownloadControlManager:
    """Manages download tracking via CSV file."""
    
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            # Create data/control directory if it doesn't exist
            control_dir = Path("data/control")
            control_dir.mkdir(parents=True, exist_ok=True)
            self.csv_path = str(control_dir / "download_control_parallel.csv")
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
                fieldnames = ['po_number', 'tab_id', 'file_name', 'status', 'download_start_time', 'download_complete_time', 'target_folder', 'error_message', 'tab_state']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
            
            print(f"   📄 Created empty CSV with headers")
            
        except Exception as e:
            print(f"   ⚠️ Warning: Could not clear CSV file: {e}")
    
    def _save_to_csv(self):
        """Save all download records to CSV."""
        try:
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
                fieldnames = ['po_number', 'tab_id', 'file_name', 'status', 'download_start_time', 'download_complete_time', 'target_folder', 'error_message', 'tab_state']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                
                for record in self.downloads.values():
                    writer.writerow(asdict(record))
            
            print(f"✅ CSV updated: {os.path.abspath(self.csv_path)}")
            
        except Exception as e:
            print(f"❌ Error saving to CSV: {e}")
    
    def register_download(self, po_number: str, tab_id: str, file_name: str, target_folder: str, index: int = 0, error_message: str = None) -> str:
        """Register a new download for tracking."""
        # Create unique key using index to handle duplicate filenames
        file_key = f"{po_number}_{file_name}_{index}"
        
        record = DownloadRecord(
            po_number=po_number,
            tab_id=tab_id,
            file_name=file_name,
            target_folder=target_folder,  # This is the final hierarchical folder
            download_start_time=datetime.now().isoformat(),
            error_message=error_message
        )
        
        self.downloads[file_key] = record
        self._save_to_csv()
        print(f"   📝 Registered: {file_name} for PO {po_number} (index {index+1}) - Final folder: {target_folder}")
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
    
    def update_download_filename(self, file_key: str, actual_filename: str):
        """Update the filename with the actual name saved by the browser."""
        if file_key in self.downloads:
            record = self.downloads[file_key]
            record.file_name = actual_filename
            print(f"📝 Updated filename: {file_key} -> {actual_filename}")
            self._save_to_csv()
    
    def get_tab_downloads(self, tab_id: str) -> List[DownloadRecord]:
        """Get all downloads for a specific tab."""
        return [record for record in self.downloads.values() if record.tab_id == tab_id]
    
    def is_tab_complete(self, tab_id: str) -> bool:
        """Check if all downloads for a tab are completed."""
        tab_downloads = self.get_tab_downloads(tab_id)
        if not tab_downloads:
            return True  # No downloads means tab is complete
        
        # Check if all downloads are in final states
        completed_downloads = sum(1 for record in tab_downloads if record.status in ["COMPLETED", "ERROR"])
        total_downloads = len(tab_downloads)
        
        if completed_downloads == total_downloads:
            print(f"   📊 Tab {tab_id}: {completed_downloads}/{total_downloads} downloads completed")
            return True
        else:
            downloading_downloads = sum(1 for record in tab_downloads if record.status == "DOWNLOADING")
            print(f"   📊 Tab {tab_id}: {completed_downloads}/{total_downloads} completed, {downloading_downloads} downloading")
            return False
    
    def is_po_complete(self, po_number: str) -> bool:
        """Check if all downloads for a PO are completed."""
        po_downloads = [record for record in self.downloads.values() if record.po_number == po_number]
        if not po_downloads:
            return True  # No downloads means PO is complete
        
        return all(record.status in ["COMPLETED", "ERROR"] for record in po_downloads)
    
    def get_po_downloads(self, po_number: str) -> List[DownloadRecord]:
        """Get all downloads for a specific PO."""
        return [record for record in self.downloads.values() if record.po_number == po_number]
    
    def move_completed_po_files(self, po_number: str, excel_processor=None, base_download_dir=None) -> bool:
        """Move all completed files for a PO to their final hierarchical folders."""
        po_downloads = self.get_po_downloads(po_number)

        if not po_downloads:
            print(f"   ℹ️ No downloads found for PO {po_number}")
            return True

        # Determine final status based on download results
        final_status = self.get_po_final_status(po_number)
        print(f"   📊 PO {po_number} final status: {final_status}")

        # Get hierarchical folder from Excel if available
        hierarchical_folder = None
        if excel_processor:
            try:
                # Read Excel to get PO hierarchy
                excel_path = excel_processor.get_excel_file_path()
                po_entries, original_cols, hierarchy_cols, has_hierarchy_data = excel_processor.read_po_numbers_from_excel(excel_path)
                
                # Find this PO in the data
                po_data = None
                for entry in po_entries:
                    if entry.get('po_number') == po_number:
                        po_data = entry
                        break
                
                if po_data and has_hierarchy_data:
                    # Create hierarchical folder path with final status
                    from folder_hierarchy import FolderHierarchyManager
                    folder_manager = FolderHierarchyManager(base_download_dir)
                    hierarchical_folder = folder_manager.create_folder_path(po_data, hierarchy_cols, True, final_status)
                    print(f"   📁 Using hierarchical folder: {hierarchical_folder}")
                else:
                    # Fallback to simple folder with final status
                    if base_download_dir:
                        hierarchical_folder = os.path.join(base_download_dir, "CoupaDownloads", f"{po_number}_{final_status}")
                    else:
                        hierarchical_folder = f"/Users/juliocezar/Downloads/CoupaDownloads/{po_number}_{final_status}"
                    print(f"   📁 Using fallback folder: {hierarchical_folder}")
                    
            except Exception as e:
                print(f"   ⚠️ Error reading Excel hierarchy: {e}")
                hierarchical_folder = f"/Users/juliocezar/Downloads/CoupaDownloads/{po_number}"
        else:
            # No Excel processor, use simple folder
            if base_download_dir:
                hierarchical_folder = os.path.join(base_download_dir, "CoupaDownloads", po_number)
            else:
                hierarchical_folder = f"/Users/juliocezar/Downloads/CoupaDownloads/{po_number}"

        print(f"   📦 Moving files for PO {po_number} to final folders...")

        moved_count = 0
        
        # Group files by original filename to handle duplicates properly
        files_by_name = {}
        for record in po_downloads:
            if record.status == "COMPLETED":
                if record.file_name not in files_by_name:
                    files_by_name[record.file_name] = []
                files_by_name[record.file_name].append(record)
        
        # Process each unique filename
        for original_filename, records in files_by_name.items():
            try:
                # Create final folder path (status already included in hierarchical_folder)
                final_folder = hierarchical_folder
                os.makedirs(final_folder, exist_ok=True)
                
                # Process each record (each download gets its own file)
                for i, record in enumerate(records):
                    # Use the actual filename from the record (may include (1), (2), etc.)
                    actual_filename = record.file_name
                    # Add PO prefix to filename (PO#_actual_filename)
                    new_filename = f"{po_number}_{actual_filename}"
                    
                    # Look for the file in the temporary download folder
                    if base_download_dir:
                        temp_file_path = os.path.join(base_download_dir, "CoupaDownloads", "Temp", actual_filename)
                    else:
                        temp_file_path = os.path.join(Config.DOWNLOAD_FOLDER, actual_filename)
                    
                    if os.path.exists(temp_file_path):
                        final_file_path = os.path.join(final_folder, new_filename)
                        
                        # Handle duplicate filenames in final folder
                        counter = 1
                        while os.path.exists(final_file_path):
                            name, ext = os.path.splitext(new_filename)
                            final_file_path = os.path.join(final_folder, f"{name} ({counter}){ext}")
                            counter += 1
                        
                        os.rename(temp_file_path, final_file_path)
                        print(f"      ✅ Moved: {actual_filename} → {os.path.basename(final_file_path)} to {final_folder}")
                        moved_count += 1
                        
                        # Delete the original file from temp folder after successful move
                        try:
                            if os.path.exists(temp_file_path):
                                os.remove(temp_file_path)
                                print(f"      🗑️ Deleted original file from temp: {actual_filename}")
                        except Exception as e:
                            print(f"      ⚠️ Warning: Could not delete original file {actual_filename}: {e}")
                    else:
                        print(f"      ⚠️ File not found in temp folder: {temp_file_path}")
                        # List files in temp folder for debugging
                        if base_download_dir:
                            temp_folder = os.path.join(base_download_dir, "CoupaDownloads", "Temp")
                        else:
                            temp_folder = Config.DOWNLOAD_FOLDER
                        
                        if os.path.exists(temp_folder):
                            files_in_temp = os.listdir(temp_folder)
                            print(f"         📁 Files in temp folder: {files_in_temp[:5]}...")
                        
            except Exception as e:
                print(f"      ❌ Error moving {original_filename}: {e}")
        
        print(f"   📦 Moved {moved_count} files for PO {po_number}")
        return moved_count > 0
    
    def cleanup_tab(self, tab_id: str):
        """Remove all records for a specific tab."""
        keys_to_remove = [key for key, record in self.downloads.items() if record.tab_id == tab_id]
        for key in keys_to_remove:
            del self.downloads[key]
        
        if keys_to_remove:
            print(f"🧹 Cleaned up {len(keys_to_remove)} records for tab {tab_id}")
            self._save_to_csv()
    
    def update_tab_state(self, tab_id: str, state: str):
        """Update tab state (OPEN/CLOSED) for all records of a specific tab."""
        updated_count = 0
        for record in self.downloads.values():
            if record.tab_id == tab_id:
                record.tab_state = state
                updated_count += 1
        
        if updated_count > 0:
            print(f"📊 Updated tab {tab_id} state to: {state}")
            self._save_to_csv()
    
    def get_open_tabs(self) -> List[str]:
        """Get list of all open tab IDs."""
        open_tabs = set()
        for record in self.downloads.values():
            if record.tab_state == "OPEN":
                open_tabs.add(record.tab_id)
        return list(open_tabs)
    
    def get_closed_tabs(self) -> List[str]:
        """Get list of all closed tab IDs."""
        closed_tabs = set()
        for record in self.downloads.values():
            if record.tab_state == "CLOSED":
                closed_tabs.add(record.tab_id)
        return list(closed_tabs)
    
    def is_tab_open(self, tab_id: str) -> bool:
        """Check if a specific tab is open."""
        for record in self.downloads.values():
            if record.tab_id == tab_id:
                return record.tab_state == "OPEN"
        return False
    
    def get_csv_path(self) -> str:
        """Get the CSV file path."""
        return self.csv_path

    def get_po_final_status(self, po_number: str) -> str:
        """Determine final status of PO based on download results."""
        po_downloads = self.get_po_downloads(po_number)
        
        if not po_downloads:
            return "Failed"  # No downloads registered
        
        # Check for access issues (error messages)
        has_access_issue = any(
            record.error_message and any(keyword in record.error_message.lower() 
                                        for keyword in ['not found', 'access', 'error', 'page error'])
            for record in po_downloads
        )
        
        if has_access_issue:
            return "Access_Issue"
        
        # Count completed vs total downloads
        total_downloads = len(po_downloads)
        completed_downloads = len([r for r in po_downloads if r.status == "COMPLETED"])
        error_downloads = len([r for r in po_downloads if r.status == "ERROR"])
        
        if completed_downloads == total_downloads:
            return "Success"
        elif completed_downloads > 0:
            return "Partial"
        else:
            return "Failed"
