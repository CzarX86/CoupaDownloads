#!/usr/bin/env python3
"""
Demo script for enhanced progress feedback system.
Shows how the new progress manager provides detailed progress tracking.
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.progress_manager import progress_manager


def demo_progress_system():
    """Demonstrate the enhanced progress feedback system."""
    
    print("🚀 Enhanced Progress Feedback Demo")
    print("=" * 50)
    
    # Simulate processing 10 POs
    total_pos = 10
    progress_manager.start_processing(total_pos)
    
    # Simulate different scenarios
    scenarios = [
        ("PO123456", 3, "COMPLETED"),      # 3 files, all downloaded
        ("PO234567", 0, "NO_ATTACHMENTS"), # No attachments
        ("PO345678", 2, "PARTIAL"),        # 2 files, 1 downloaded
        ("PO456789", 1, "FAILED"),         # 1 file, failed
        ("PO567890", 4, "COMPLETED"),      # 4 files, all downloaded
        ("PO678901", 0, "NO_ATTACHMENTS"), # No attachments
        ("PO789012", 2, "COMPLETED"),      # 2 files, all downloaded
        ("PO890123", 1, "FAILED"),         # 1 file, failed
        ("PO901234", 3, "PARTIAL"),        # 3 files, 2 downloaded
        ("PO012345", 1, "COMPLETED"),      # 1 file, downloaded
    ]
    
    for po_number, attachment_count, expected_status in scenarios:
        # Start PO processing
        progress_manager.start_po(po_number)
        time.sleep(0.5)  # Simulate processing time
        
        # Report found attachments
        progress_manager.found_attachments(attachment_count)
        time.sleep(0.3)
        
        if attachment_count > 0:
            # Start download
            progress_manager.start_download(attachment_count)
            time.sleep(0.3)
            
            # Simulate file downloads
            if expected_status == "COMPLETED":
                for i in range(attachment_count):
                    filename = f"file_{i+1}.pdf"
                    progress_manager.attachment_downloaded(filename, i+1, attachment_count)
                    time.sleep(0.2)
                progress_manager.download_completed(attachment_count, attachment_count)
                progress_manager.po_completed("COMPLETED", attachment_count, attachment_count)
                
            elif expected_status == "PARTIAL":
                for i in range(attachment_count):
                    filename = f"file_{i+1}.pdf"
                    if i < attachment_count - 1:  # Skip last file
                        progress_manager.attachment_downloaded(filename, i+1, attachment_count)
                    else:
                        progress_manager.attachment_skipped(filename, "download failed")
                    time.sleep(0.2)
                progress_manager.download_completed(attachment_count - 1, attachment_count)
                progress_manager.po_completed("PARTIAL", attachment_count - 1, attachment_count)
                
            elif expected_status == "FAILED":
                for i in range(attachment_count):
                    filename = f"file_{i+1}.pdf"
                    progress_manager.attachment_skipped(filename, "download failed")
                    time.sleep(0.2)
                progress_manager.download_completed(0, attachment_count)
                progress_manager.po_completed("FAILED")
        else:
            # No attachments
            progress_manager.po_completed("NO_ATTACHMENTS")
        
        time.sleep(0.5)  # Pause between POs
    
    # Complete processing
    progress_manager.processing_completed()
    
    print("\n" + "=" * 50)
    print("✅ Demo completed! The enhanced progress system provides:")
    print("   • Overall progress percentage")
    print("   • Time elapsed and estimated remaining")
    print("   • Individual file download progress")
    print("   • Clear status indicators")
    print("   • Summary statistics")


if __name__ == "__main__":
    demo_progress_system() 