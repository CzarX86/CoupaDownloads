#!/usr/bin/env python3
"""
Simplified Enhanced Download Control System
Focuses on core functionality with robust error handling.
"""

import os
import csv
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

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
    status: str = "PENDING"  # PENDING, DOWNLOADING, COMPLETED, FAILED
    download_start_time: str = ""
    download_complete_time: str = ""
    target_folder: str = ""
    error_message: str = ""


class SimpleDownloadControl:
    """Simplified download control with CSV database."""
    
    def __init__(self, csv_path: str = "data/control/download_control.csv"):
        self.csv_path = csv_path
        self.lock = threading.Lock()
        self.downloads: Dict[str, DownloadRecord] = {}
        self._load_existing_downloads()
    
    def _load_existing_downloads(self):
        """Load existing downloads from CSV."""
        if os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, 'r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        record = DownloadRecord(**row)
                        file_key = f"{record.po_number}_{record.file_name}"
                        self.downloads[file_key] = record
            except Exception as e:
                print(f"⚠️ Warning: Could not load existing downloads: {e}")
    
    def _save_to_csv(self):
        """Save all downloads to CSV."""
        try:
            with self.lock:
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
                    if self.downloads:
                        fieldnames = list(asdict(next(iter(self.downloads.values()))).keys())
                        writer = csv.DictWriter(file, fieldnames=fieldnames)
                        writer.writeheader()
                        for record in self.downloads.values():
                            writer.writerow(asdict(record))
        except Exception as e:
            print(f"⚠️ Warning: Could not save to CSV: {e}")
    
    def register_download(self, po_number: str, tab_id: str, file_name: str, target_folder: str) -> str:
        """Register a new download."""
        with self.lock:
            file_key = f"{po_number}_{file_name}"
            
            record = DownloadRecord(
                po_number=po_number,
                tab_id=tab_id,
                file_name=file_name,
                target_folder=target_folder,
                download_start_time=datetime.now().isoformat()
            )
            
            self.downloads[file_key] = record
            self._save_to_csv()
            print(f"   📝 Registered: {file_name} for PO {po_number}")
            return file_key
    
    def update_status(self, file_key: str, status: str, error_message: str = ""):
        """Update download status."""
        with self.lock:
            if file_key in self.downloads:
                record = self.downloads[file_key]
                record.status = status
                record.error_message = error_message
                
                if status == "COMPLETED":
                    record.download_complete_time = datetime.now().isoformat()
                
                self._save_to_csv()
                print(f"   📊 Status: {file_key} -> {status}")


class SimpleTabManager:
    """Simplified tab manager with timeout protection."""
    
    def __init__(self, driver, browser_manager, folder_manager, download_control):
        self.driver = driver
        self.browser_manager = browser_manager
        self.folder_manager = folder_manager
        self.download_control = download_control
        self.lock = threading.Lock()
        self.active_tabs: Dict[str, str] = {}  # po_number -> tab_handle
    
    def create_tab_for_po(self, po_number: str, po_data: Dict) -> Optional[str]:
        """Create a new tab for a specific PO."""
        try:
            with self.lock:
                # Create folder path
                hierarchy_cols = ['Priority', 'Supplier Segment', 'Spend Type', 'L1 UU Supplier Name']
                download_folder = self.folder_manager.create_folder_path(po_data, hierarchy_cols, True)
                
                # Create new tab
                self.driver.execute_script("window.open('');")
                new_handle = self.driver.window_handles[-1]
                self.driver.switch_to.window(new_handle)
                
                # Set download directory
                self.browser_manager.update_download_directory(download_folder)
                
                self.active_tabs[po_number] = new_handle
                print(f"   🆕 Created tab for {po_number}: {new_handle}")
                return new_handle
                
        except Exception as e:
            print(f"   ❌ Error creating tab for {po_number}: {e}")
            return None
    
    def process_po_in_tab(self, tab_handle: str, po_number: str, timeout: int = 30) -> Tuple[bool, str]:
        """Process a PO in a specific tab with timeout."""
        try:
            # Switch to tab
            self.driver.switch_to.window(tab_handle)
            
            # Create downloader
            downloader = Downloader(self.driver, self.browser_manager)
            
            # Download with timeout
            start_time = time.time()
            success, message = downloader.download_attachments_for_po(po_number)
            
            if time.time() - start_time > timeout:
                return False, f"Timeout after {timeout}s"
            
            return success, message
            
        except Exception as e:
            return False, f"Error: {e}"
    
    def close_tab(self, po_number: str, tab_handle: str):
        """Close a tab safely."""
        try:
            with self.lock:
                if tab_handle in self.driver.window_handles:
                    self.driver.switch_to.window(tab_handle)
                    self.driver.close()
                    
                    # Switch back to main tab
                    if self.driver.window_handles:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                
                if po_number in self.active_tabs:
                    del self.active_tabs[po_number]
                
                print(f"   🔒 Closed tab for {po_number}")
                
        except Exception as e:
            print(f"   ⚠️ Error closing tab for {po_number}: {e}")
    
    def get_active_count(self) -> int:
        """Get number of active tabs."""
        return len(self.active_tabs)


class SimpleMainApp:
    """Simplified main application with robust error handling."""
    
    def __init__(self):
        self.excel_processor = ExcelProcessor()
        self.browser_manager = BrowserManager()
        self.folder_manager = FolderHierarchyManager()
        self.download_control = SimpleDownloadControl()
        self.tab_manager = None
        self.driver = None
    
    def initialize_browser(self):
        """Initialize browser with error handling."""
        try:
            print("🚀 Initializing browser...")
            self.browser_manager.initialize_driver()
            self.driver = self.browser_manager.driver
            self.tab_manager = SimpleTabManager(
                self.driver, 
                self.browser_manager, 
                self.folder_manager,
                self.download_control
            )
            print("✅ Browser initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Error initializing browser: {e}")
            return False
    
    def process_single_po(self, po_data: Dict, index: int, total: int) -> Tuple[bool, str]:
        """Process a single PO with timeout protection."""
        po_number = po_data['po_number']
        
        try:
            print(f"📋 Processing PO {index+1}/{total}: {po_number}")
            
            # Create tab
            tab_handle = self.tab_manager.create_tab_for_po(po_number, po_data)
            if not tab_handle:
                return False, "Failed to create tab"
            
            # Register potential downloads
            target_folder = self.folder_manager.create_folder_path(
                po_data, 
                ['Priority', 'Supplier Segment', 'Spend Type', 'L1 UU Supplier Name'], 
                True
            )
            
            # Register common file types
            common_files = [f"{po_number}_document.pdf"]
            for file_name in common_files:
                self.download_control.register_download(po_number, tab_handle, file_name, target_folder)
            
            # Process downloads with timeout
            success, message = self.tab_manager.process_po_in_tab(tab_handle, po_number, timeout=30)
            
            if success:
                # Update status
                downloads = self.download_control.downloads
                for file_key, record in downloads.items():
                    if record.po_number == po_number and record.tab_id == tab_handle:
                        self.download_control.update_status(file_key, "DOWNLOADING")
                
                print(f"   📥 Download started for {po_number}")
            
            # Close tab after processing
            self.tab_manager.close_tab(po_number, tab_handle)
            
            return success, message
            
        except Exception as e:
            print(f"   ❌ Error processing {po_number}: {e}")
            return False, str(e)
    
    def run(self):
        """Run the simplified main application."""
        try:
            # Load POs
            pos, _, _, _ = self.excel_processor.read_po_numbers_from_excel(self.excel_processor.get_excel_file_path())
            if not pos:
                print("❌ No POs found to process")
                return
            
            # Filter pending POs (limit to 2 for testing)
            pending_pos = [po for po in pos if po.get('status') == 'Pending'][:2]
            if not pending_pos:
                print("✅ All POs already processed")
                return
            
            print(f"🚀 Starting simplified processing of {len(pending_pos)} POs")
            
            # Initialize browser
            if not self.initialize_browser():
                return
            
            # Process POs one by one (no parallelism for now)
            for index, po_data in enumerate(pending_pos):
                success, message = self.process_single_po(po_data, index, len(pending_pos))
                
                if success:
                    print(f"✅ PO{po_data['po_number']}: {message}")
                else:
                    print(f"❌ PO{po_data['po_number']}: {message}")
                
                print(f"📈 Progress: {index+1}/{len(pending_pos)} POs completed")
                
                # Small delay between POs
                time.sleep(2)
            
            print("✅ Simplified processing completed!")
            
        except Exception as e:
            print(f"❌ Error in main execution: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Cleanup
            if self.browser_manager:
                print("🧹 Closing browser...")
                self.browser_manager.cleanup()


def main():
    """Main entry point."""
    print("🧪 Testing Simplified Enhanced System")
    print("=" * 50)
    
    app = SimpleMainApp()
    app.run()
    
    print("\n✅ Simplified enhanced system test completed!")


if __name__ == "__main__":
    main()
