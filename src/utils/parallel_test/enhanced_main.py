#!/usr/bin/env python3
"""
Download Control System with CSV Database
Manages downloads, tabs, and file movements with granular control.
"""

import os
import csv
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from browser import BrowserManager
from config import Config
from downloader import Downloader
from excel_processor import ExcelProcessor
from folder_hierarchy import FolderHierarchyManager


@dataclass
class DownloadRecord:
    """Represents a single download record."""
    po_number: str
    tab_id: str
    file_name: str
    file_size: int = 0
    status: str = "PENDING"  # PENDING, DOWNLOADING, COMPLETED, FAILED
    download_start_time: str = ""
    download_complete_time: str = ""
    target_folder: str = ""
    error_message: str = ""
    temp_location: str = ""
    final_location: str = ""


class DownloadControlManager:
    """Manages download control with CSV database."""
    
    def __init__(self, csv_path: str = "data/control/download_control.csv"):
        self.csv_path = csv_path
        self.lock = threading.Lock()
        self.downloads: Dict[str, DownloadRecord] = {}  # file_key -> DownloadRecord
        self.tab_downloads: Dict[str, List[str]] = {}  # tab_id -> [file_keys]
        self._load_existing_downloads()
    
    def _load_existing_downloads(self):
        """Load existing downloads from CSV."""
        if os.path.exists(self.csv_path):
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    record = DownloadRecord(**row)
                    file_key = f"{record.po_number}_{record.file_name}"
                    self.downloads[file_key] = record
                    
                    if record.tab_id not in self.tab_downloads:
                        self.tab_downloads[record.tab_id] = []
                    self.tab_downloads[record.tab_id].append(file_key)
    
    def _save_to_csv(self):
        """Save all downloads to CSV."""
        with self.lock:
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
                if self.downloads:
                    fieldnames = list(asdict(next(iter(self.downloads.values()))).keys())
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    for record in self.downloads.values():
                        writer.writerow(asdict(record))
    
    def register_download(self, po_number: str, tab_id: str, file_name: str, target_folder: str) -> str:
        """Register a new download."""
        with self.lock:
            file_key = f"{po_number}_{file_name}"
            
            record = DownloadRecord(
                po_number=po_number,
                tab_id=tab_id,
                file_name=file_name,
                target_folder=target_folder,
                download_start_time=datetime.now().isoformat(),
                temp_location=os.path.join(Config.DOWNLOAD_FOLDER, file_name)
            )
            
            self.downloads[file_key] = record
            
            if tab_id not in self.tab_downloads:
                self.tab_downloads[tab_id] = []
            self.tab_downloads[tab_id].append(file_key)
            
            self._save_to_csv()
            print(f"   📝 Registered download: {file_name} for PO {po_number}")
            return file_key
    
    def update_download_status(self, file_key: str, status: str, error_message: str = ""):
        """Update download status."""
        with self.lock:
            if file_key in self.downloads:
                record = self.downloads[file_key]
                record.status = status
                record.error_message = error_message
                
                if status == "COMPLETED":
                    record.download_complete_time = datetime.now().isoformat()
                    # Move file to target folder
                    self._move_file_to_target(record)
                
                self._save_to_csv()
                print(f"   📊 Updated status: {file_key} -> {status}")
    
    def _move_file_to_target(self, record: DownloadRecord):
        """Move completed file to target folder."""
        try:
            temp_path = record.temp_location
            final_path = os.path.join(record.target_folder, record.file_name)
            
            if os.path.exists(temp_path):
                # Ensure target folder exists
                os.makedirs(record.target_folder, exist_ok=True)
                
                # Move file
                import shutil
                shutil.move(temp_path, final_path)
                record.final_location = final_path
                
                print(f"   📁 Moved file: {record.file_name} -> {record.target_folder}")
            else:
                print(f"   ⚠️ File not found: {temp_path}")
                
        except Exception as e:
            print(f"   ❌ Error moving file {record.file_name}: {e}")
            record.error_message = str(e)
    
    def get_tab_downloads(self, tab_id: str) -> List[DownloadRecord]:
        """Get all downloads for a specific tab."""
        with self.lock:
            file_keys = self.tab_downloads.get(tab_id, [])
            return [self.downloads[key] for key in file_keys if key in self.downloads]
    
    def is_tab_complete(self, tab_id: str) -> bool:
        """Check if all downloads for a tab are complete."""
        downloads = self.get_tab_downloads(tab_id)
        if not downloads:
            return True
        
        return all(d.status in ["COMPLETED", "FAILED"] for d in downloads)
    
    def get_pending_downloads(self, tab_id: str) -> List[DownloadRecord]:
        """Get pending downloads for a tab."""
        downloads = self.get_tab_downloads(tab_id)
        return [d for d in downloads if d.status == "PENDING"]
    
    def cleanup_tab(self, tab_id: str):
        """Clean up tab records."""
        with self.lock:
            if tab_id in self.tab_downloads:
                del self.tab_downloads[tab_id]
                # Remove associated downloads
                keys_to_remove = [k for k, v in self.downloads.items() if v.tab_id == tab_id]
                for key in keys_to_remove:
                    del self.downloads[key]
                self._save_to_csv()
                print(f"   🧹 Cleaned up tab: {tab_id}")


class EnhancedTabManager:
    """Enhanced tab manager with download control."""
    
    def __init__(self, driver, browser_manager, folder_manager, download_control):
        self.driver = driver
        self.browser_manager = browser_manager
        self.folder_manager = folder_manager
        self.download_control = download_control
        self.lock = threading.Lock()
        self.active_tabs: Dict[str, str] = {}  # po_number -> tab_handle
        self.tab_status: Dict[str, str] = {}  # tab_handle -> status
    
    def create_tab_for_po(self, po_number: str, po_data: Dict) -> str:
        """Create a new tab for a specific PO with download directory."""
        with self.lock:
            # Create folder path for this PO
            hierarchy_cols = ['Priority', 'Supplier Segment', 'Spend Type', 'L1 UU Supplier Name']
            download_folder = self.folder_manager.create_folder_path(po_data, hierarchy_cols, True)
            
            # Create tab with specific download directory
            new_handle = self.browser_manager.create_tab_with_download_dir(download_folder)
            
            if new_handle:
                self.active_tabs[po_number] = new_handle
                self.tab_status[new_handle] = "ACTIVE"
                print(f"   🆕 Created tab for {po_number}: {new_handle}")
                return new_handle
            else:
                print(f"   ❌ Failed to create tab for {po_number}")
                return None
    
    def process_downloads_for_tab(self, tab_handle: str, po_number: str):
        """Process downloads for a specific tab."""
        try:
            # Switch to tab
            self.driver.switch_to.window(tab_handle)
            
            # Get downloader for this tab
            downloader = Downloader(self.driver, self.browser_manager)
            
            # Download attachments
            success, message = downloader.download_attachments_for_po(po_number)
            
            if success and "Initiated download" in message:
                # Parse downloaded files from message
                # This is a simplified approach - in real implementation, 
                # we'd track actual file creation events
                print(f"   📥 Downloads initiated for {po_number}")
                
                # Update status to DOWNLOADING
                downloads = self.download_control.get_tab_downloads(tab_handle)
                for download in downloads:
                    self.download_control.update_download_status(
                        f"{download.po_number}_{download.file_name}", 
                        "DOWNLOADING"
                    )
            
            return success, message
            
        except Exception as e:
            print(f"   ❌ Error processing downloads for tab {tab_handle}: {e}")
            return False, str(e)
    
    def wait_for_tab_completion(self, tab_handle: str, timeout: int = 60) -> bool:
        """Wait for all downloads in a tab to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.download_control.is_tab_complete(tab_handle):
                print(f"   ✅ All downloads completed for tab {tab_handle}")
                return True
            
            time.sleep(2)
            print(f"   ⏳ Waiting for downloads to complete... ({int(time.time() - start_time)}s)")
        
        print(f"   ⚠️ Timeout waiting for tab {tab_handle} completion")
        return False
    
    def close_tab_safely(self, po_number: str, tab_handle: str):
        """Close tab only after all downloads are complete."""
        with self.lock:
            try:
                # Wait for downloads to complete
                if self.wait_for_tab_completion(tab_handle):
                    # Close the tab
                    self.driver.switch_to.window(tab_handle)
                    self.driver.close()
                    
                    # Switch back to main tab
                    main_tab = self.driver.window_handles[0]
                    self.driver.switch_to.window(main_tab)
                    
                    # Clean up records
                    self.download_control.cleanup_tab(tab_handle)
                    
                    # Remove from tracking
                    if po_number in self.active_tabs:
                        del self.active_tabs[po_number]
                    if tab_handle in self.tab_status:
                        del self.tab_status[tab_handle]
                    
                    print(f"   🔒 Tab closed safely for {po_number}")
                else:
                    print(f"   ⚠️ Could not close tab {po_number} - downloads not complete")
                    
            except Exception as e:
                print(f"   ❌ Error closing tab for {po_number}: {e}")
    
    def get_active_tab_count(self) -> int:
        """Get number of active tabs."""
        return len(self.active_tabs)
    
    def get_remaining_pos(self) -> List[str]:
        """Get list of POs with active tabs."""
        return list(self.active_tabs.keys())


class EnhancedMainApp:
    """Enhanced main application with download control."""
    
    def __init__(self):
        # Initialize components
        self.excel_processor = ExcelProcessor()
        self.browser_manager = BrowserManager()
        self.folder_manager = FolderHierarchyManager()
        self.download_control = DownloadControlManager()
        
        self.driver = None
        self.tab_manager = None
    
    def initialize_browser_once(self):
        """Initialize browser once for all tabs."""
        print("🚀 Initializing browser for parallel processing...")
        
        try:
            self.browser_manager.initialize_driver()
            self.driver = self.browser_manager.driver
            self.tab_manager = EnhancedTabManager(
                self.driver, 
                self.browser_manager, 
                self.folder_manager,
                self.download_control
            )
            print("✅ Browser initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing browser: {e}")
            raise
    
    def process_single_po(self, po_data: Dict, index: int, total: int) -> Tuple[bool, str]:
        """Process a single PO with enhanced download control."""
        po_number = po_data['po_number']
        
        try:
            print(f"📋 Processing PO {index+1}/{total}: {po_number}")
            
            # Create tab for this PO
            tab_handle = self.tab_manager.create_tab_for_po(po_number, po_data)
            if not tab_handle:
                return False, "Failed to create tab"
            
            # Register downloads for this PO
            # In a real implementation, we'd scan the page for attachments first
            # For now, we'll register common file types
            common_files = [
                f"{po_number}_document.pdf",
                f"{po_number}_attachment.xlsx",
                f"{po_number}_contract.docx"
            ]
            
            target_folder = self.folder_manager.create_folder_path(
                po_data, 
                ['Priority', 'Supplier Segment', 'Spend Type', 'L1 UU Supplier Name'], 
                True
            )
            
            for file_name in common_files:
                self.download_control.register_download(po_number, tab_handle, file_name, target_folder)
            
            # Process downloads
            success, message = self.tab_manager.process_downloads_for_tab(tab_handle, po_number)
            
            if success:
                # Mark downloads as started
                downloads = self.download_control.get_tab_downloads(tab_handle)
                for download in downloads:
                    self.download_control.update_download_status(
                        f"{download.po_number}_{download.file_name}", 
                        "DOWNLOADING"
                    )
                
                print(f"   📥 Download started for {po_number}")
                return True, message
            else:
                return False, message
                
        except Exception as e:
            print(f"   ❌ Error processing {po_number}: {e}")
            return False, str(e)
    
    def run(self):
        """Run the enhanced main application."""
        try:
            # Load POs
            pos, original_cols, hierarchy_cols, has_hierarchy_data = self.excel_processor.read_po_numbers_from_excel(self.excel_processor.get_excel_file_path())
            if not pos:
                print("❌ No POs found to process")
                return
            
            # Filter pending POs
            pending_pos = [po for po in pos if po.get('status') == 'Pending']
            if not pending_pos:
                print("✅ All POs already processed")
                return
            
            print(f"🚀 Starting enhanced parallel processing of {len(pending_pos)} POs")
            
            # Initialize browser
            self.initialize_browser_once()
            
            # Process POs
            for index, po_data in enumerate(pending_pos):
                success, message = self.process_single_po(po_data, index, len(pending_pos))
                
                if success:
                    print(f"✅ PO{po_data['po_number']}: {message}")
                else:
                    print(f"❌ PO{po_data['po_number']}: {message}")
                
                print(f"📈 Progress: {index+1}/{len(pending_pos)} POs completed")
                print(f"📊 Active tabs: {self.tab_manager.get_active_tab_count()}")
            
            # Wait for all downloads to complete and close tabs
            print("🧹 Final cleanup - ensuring all downloads complete...")
            remaining_pos = self.tab_manager.get_remaining_pos()
            
            for po_number in remaining_pos:
                tab_handle = self.tab_manager.active_tabs[po_number]
                self.tab_manager.close_tab_safely(po_number, tab_handle)
            
            print("✅ Enhanced parallel processing completed!")
            
        except Exception as e:
            print(f"❌ Error in enhanced main execution: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Cleanup
            if self.browser_manager:
                print("🧹 Closing browser...")
                self.browser_manager.cleanup()


def main():
    """Main entry point."""
    print("🧪 Testing Enhanced Download Control System")
    print("=" * 60)
    
    app = EnhancedMainApp()
    app.run()
    
    print("\n✅ Enhanced download control test completed!")


if __name__ == "__main__":
    main()
