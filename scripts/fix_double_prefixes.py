#!/usr/bin/env python3
"""
Utility script to fix existing files with double PO prefixes.
Run this script to clean up files like "POPO15826591_document.pdf" 
and rename them to "PO15826591_document.pdf"
"""

import os
import sys
import os
# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.downloader import FileManager
from core.config import Config


def main():
    """Fix double PO prefixes in the download folder."""
    download_folder = Config.DOWNLOAD_FOLDER
    
    if not os.path.exists(download_folder):
        print(f"Download folder does not exist: {download_folder}")
        return
    
    print(f"Scanning for double PO prefixes in: {download_folder}")
    
    # Find files with double PO prefixes
    double_po_files = []
    for filename in os.listdir(download_folder):
        if filename.startswith("POPO"):
            double_po_files.append(filename)
    
    if not double_po_files:
        print("✅ No files with double PO prefixes found.")
        return
    
    print(f"Found {len(double_po_files)} files with double PO prefixes:")
    for filename in double_po_files:
        print(f"  {filename}")
    
    # Ask for confirmation
    response = input("\nDo you want to fix these files? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Operation cancelled.")
        return
    
    # Fix the files
    print("\nFixing double PO prefixes...")
    FileManager.cleanup_double_po_prefixes(download_folder)
    
    print("✅ Double PO prefix cleanup completed!")


if __name__ == "__main__":
    main() 