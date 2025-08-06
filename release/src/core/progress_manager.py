"""
Progress Manager
Handles enhanced progress feedback with percentages, time tracking, and status indicators.
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
        self.completed_pos = 0
        self.failed_pos = 0
        
    def start_processing(self, total_pos: int) -> None:
        """Start processing with total PO count."""
        self.start_time = time.time()
        self.total_pos = total_pos
        self.current_po_index = 0
        self.completed_pos = 0
        self.failed_pos = 0
        print(f"🚀 Starting processing of {total_pos} POs...")
        
    def start_po(self, po_number: str) -> None:
        """Start processing a specific PO."""
        self.current_po_index += 1
        self.current_po = po_number
        self.current_attachments = 0
        self.downloaded_attachments = 0
        
        # Calculate time-based overall progress
        elapsed_time = self.get_elapsed_time()
        estimated_total = self._estimate_total_time()
        
        if estimated_total > 0:
            time_progress = min(100, (elapsed_time / estimated_total) * 100)
            estimated_remaining = max(0, estimated_total - elapsed_time)
        else:
            time_progress = 0
            estimated_remaining = 0
        
        # Format time strings
        elapsed_str = self._format_time(elapsed_time)
        remaining_str = self._format_time(estimated_remaining)
        
        print(f"📋 PO{po_number}{'.' * (15 - len(po_number))}{time_progress:.0f}% | {elapsed_str} elapsed | ~{remaining_str} remaining")
        
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
            
    def attachment_downloaded(self, filename: str, bytes_downloaded: int, total_bytes: int) -> None:
        """Report successful attachment download with size-based progress."""
        self.downloaded_attachments += 1
        
        # Calculate size-based progress
        if total_bytes > 0:
            size_progress = (bytes_downloaded / total_bytes) * 100
            size_str = f"{self._format_file_size(bytes_downloaded)}/{self._format_file_size(total_bytes)}"
        else:
            size_progress = 100
            size_str = "completed"
        
        # Truncate filename if too long
        display_name = filename[:30] + "..." if len(filename) > 30 else filename
        
        print(f"   ✅ {display_name} {size_str} ({size_progress:.0f}%)")
        
    def _format_file_size(self, bytes_size: int) -> str:
        """Format file size in human-readable format."""
        if bytes_size < 1024:
            return f"{bytes_size}B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f}KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size / (1024 * 1024):.1f}MB"
        else:
            return f"{bytes_size / (1024 * 1024 * 1024):.1f}GB"
        
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
            self.completed_pos += 1
            print(f"   ✅ PO{self.current_po} completed: {success_count}/{total_count} files")
        elif status == 'PARTIAL':
            self.completed_pos += 1
            print(f"   ⚠️ PO{self.current_po} partial: {success_count}/{total_count} files")
        elif status == 'FAILED':
            self.failed_pos += 1
            print(f"   ❌ PO{self.current_po} failed")
        elif status == 'NO_ATTACHMENTS':
            self.completed_pos += 1
            print(f"   📭 PO{self.current_po} no attachments")
            
    def processing_completed(self) -> None:
        """Report overall processing completion."""
        if self.start_time:
            elapsed_time = time.time() - self.start_time
            elapsed_str = self._format_time(elapsed_time)
            print(f"\n🎉 Processing completed in {elapsed_str}")
            print(f"📊 Summary: {self.completed_pos} completed, {self.failed_pos} failed, {self.total_pos} total")
            
    def _estimate_total_time(self) -> float:
        """Estimate total processing time based on current progress."""
        if self.current_po_index <= 1:
            # Use a default estimate for the first PO
            return self.total_pos * 30  # 30 seconds per PO as default
        
        elapsed_time = self.get_elapsed_time()
        if elapsed_time <= 0:
            return 0
            
        # Calculate average time per PO and estimate total
        avg_time_per_po = elapsed_time / self.current_po_index
        return avg_time_per_po * self.total_pos
        
    def _format_time(self, seconds: float) -> str:
        """Format time in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
            
    def get_elapsed_time(self) -> float:
        """Get elapsed time since start."""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0


# Global progress manager instance
progress_manager = ProgressManager() 