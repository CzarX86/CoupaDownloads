"""
Progress Manager
Handles enhanced progress feedback with percentages and status indicators.
"""

import time
from typing import List, Dict, Any


class ProgressManager:
    """Manages progress feedback with enhanced visual indicators."""
    
    def __init__(self):
        self.start_time = None
        self.total_pos = 0
        self.current_po_index = 0
        self.current_po = None
        self.current_attachments = 0
        self.downloaded_attachments = 0
        
    def start_processing(self, total_pos: int) -> None:
        """Start processing with total PO count."""
        self.start_time = time.time()
        self.total_pos = total_pos
        self.current_po_index = 0
        print(f"🚀 Starting processing of {total_pos} POs...")
        
    def start_po(self, po_number: str) -> None:
        """Start processing a specific PO."""
        self.current_po_index += 1
        self.current_po = po_number
        self.current_attachments = 0
        self.downloaded_attachments = 0
        
        progress = (self.current_po_index / self.total_pos) * 100
        print(f"📋 PO{po_number}{'.' * (20 - len(po_number))}{progress:.0f}%")
        
    def found_attachments(self, count: int) -> None:
        """Report found attachments."""
        self.current_attachments = count
        if count > 0:
            print(f"   📎 {count} file(s) found")
        else:
            print(f"   📭 No attachments found")
            
    def start_download(self, attachment_count: int) -> None:
        """Start downloading attachments."""
        if attachment_count > 0:
            print(f"   📥 Starting download of {attachment_count} file(s)...")
            
    def attachment_downloaded(self, filename: str, index: int, total: int) -> None:
        """Report successful attachment download."""
        self.downloaded_attachments += 1
        download_progress = (self.downloaded_attachments / total) * 100
        
        # Truncate filename if too long
        display_name = filename[:30] + "..." if len(filename) > 30 else filename
        
        print(f"   ✅ {display_name} ({self.downloaded_attachments}/{total}) {download_progress:.0f}%")
        
    def attachment_skipped(self, filename: str, reason: str) -> None:
        """Report skipped attachment."""
        display_name = filename[:30] + "..." if len(filename) > 30 else filename
        print(f"   ⏭️ {display_name} ({reason})")
        
    def download_completed(self, success_count: int, total_count: int) -> None:
        """Report download completion."""
        if total_count == 0:
            print(f"   📭 No files to download")
        elif success_count == total_count:
            print(f"   🎉 All {success_count} files downloaded successfully")
        elif success_count > 0:
            print(f"   ⚠️ Partially downloaded: {success_count}/{total_count} files")
        else:
            print(f"   ❌ Failed to download any files")
            
    def po_completed(self, status: str, success_count: int = 0, total_count: int = 0) -> None:
        """Report PO completion."""
        if status == 'COMPLETED':
            print(f"   ✅ PO{self.current_po} completed: {success_count}/{total_count} files")
        elif status == 'PARTIAL':
            print(f"   ⚠️ PO{self.current_po} partial: {success_count}/{total_count} files")
        elif status == 'FAILED':
            print(f"   ❌ PO{self.current_po} failed")
        elif status == 'NO_ATTACHMENTS':
            print(f"   📭 PO{self.current_po} no attachments")
            
    def processing_completed(self) -> None:
        """Report overall processing completion."""
        if self.start_time:
            elapsed_time = time.time() - self.start_time
            print(f"\n🎉 Processing completed in {elapsed_time:.1f} seconds")
            print(f"📊 Processed {self.total_pos} POs")
            
    def get_elapsed_time(self) -> float:
        """Get elapsed time since start."""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0


# Global progress manager instance
progress_manager = ProgressManager() 