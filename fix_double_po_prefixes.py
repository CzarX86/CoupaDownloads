#!/usr/bin/env python3
"""
Utility script to fix files with double PO prefixes.
This script will find and rename files that have patterns like:
- POPO15362783_document.pdf -> PO15362783_document.pdf
- PO_PO_document.pdf -> PO_document.pdf
- PO123_PO456_document.pdf -> PO123_document.pdf
"""

import os
import re
from config import Config


def fix_double_po_prefixes(download_folder: str | None = None) -> None:
    """Fix files with double PO prefixes in the specified folder."""
    
    if download_folder is None:
        download_folder = Config.DOWNLOAD_FOLDER
    
    print(f"🔧 Fixing double PO prefixes in: {download_folder}")
    print("=" * 60)
    
    if not os.path.exists(download_folder):
        print(f"❌ Download folder does not exist: {download_folder}")
        return
    
    fixed_count = 0
    error_count = 0
    
    # Process main download folder
    print(f"\n📁 Processing main folder: {download_folder}")
    fixed, errors = process_folder(download_folder)
    fixed_count += fixed
    error_count += errors
    
    # Process supplier subfolders
    for item in os.listdir(download_folder):
        item_path = os.path.join(download_folder, item)
        if os.path.isdir(item_path):
            print(f"\n📁 Processing supplier folder: {item}")
            fixed, errors = process_folder(item_path)
            fixed_count += fixed
            error_count += errors
    
    print(f"\n📊 Summary:")
    print("=" * 60)
    print(f"✅ Files fixed: {fixed_count}")
    if error_count > 0:
        print(f"❌ Errors encountered: {error_count}")
    else:
        print(f"🎉 All files processed successfully!")


def process_folder(folder_path: str) -> tuple[int, int]:
    """Process a single folder for double PO prefixes."""
    
    fixed_count = 0
    error_count = 0
    
    try:
        for filename in os.listdir(folder_path):
            if not os.path.isfile(os.path.join(folder_path, filename)):
                continue
                
            new_filename = fix_filename(filename)
            
            if new_filename != filename:
                old_path = os.path.join(folder_path, filename)
                new_path = os.path.join(folder_path, new_filename)
                
                try:
                    os.rename(old_path, new_path)
                    print(f"  ✅ Fixed: {filename} -> {new_filename}")
                    fixed_count += 1
                except Exception as e:
                    print(f"  ❌ Error fixing {filename}: {e}")
                    error_count += 1
                    
    except Exception as e:
        print(f"  ❌ Error processing folder {folder_path}: {e}")
        error_count += 1
    
    return fixed_count, error_count


def fix_filename(filename: str) -> str:
    """Fix a single filename by removing double PO prefixes."""
    
    # Pattern 1: POPO123456_document.pdf -> PO123456_document.pdf
    if filename.startswith("POPO"):
        return filename[2:]  # Remove first "PO"
    
    # Pattern 2: PO_PO_document.pdf -> PO_document.pdf
    if filename.startswith("PO_") and "_PO_" in filename:
        return filename.replace("_PO_", "_", 1)
    
    # Pattern 3: PO123_PO456_document.pdf -> PO123_document.pdf
    if filename.startswith("PO") and "_" in filename:
        parts = filename.split("_")
        if len(parts) >= 2 and parts[1].startswith("PO"):
            # Remove the second PO prefix
            return f"{parts[0]}_{'_'.join(parts[2:])}"
    
    # Pattern 4: Any other double PO patterns
    # Look for PO followed by numbers, then another PO
    pattern = r'^(PO\d+)_(PO\d+)_(.+)$'
    match = re.match(pattern, filename)
    if match:
        return f"{match.group(1)}_{match.group(3)}"
    
    # No changes needed
    return filename


def find_problematic_files(download_folder: str | None = None) -> None:
    """Find and list files that might have double PO prefixes."""
    
    if download_folder is None:
        download_folder = Config.DOWNLOAD_FOLDER
    
    print(f"🔍 Scanning for problematic files in: {download_folder}")
    print("=" * 60)
    
    problematic_files = []
    
    # Scan main folder
    for filename in os.listdir(download_folder):
        if os.path.isfile(os.path.join(download_folder, filename)):
            if is_problematic_filename(filename):
                problematic_files.append((download_folder, filename))
    
    # Scan supplier subfolders
    for item in os.listdir(download_folder):
        item_path = os.path.join(download_folder, item)
        if os.path.isdir(item_path):
            for filename in os.listdir(item_path):
                if os.path.isfile(os.path.join(item_path, filename)):
                    if is_problematic_filename(filename):
                        problematic_files.append((item_path, filename))
    
    if problematic_files:
        print(f"⚠️ Found {len(problematic_files)} potentially problematic files:")
        for folder, filename in problematic_files:
            print(f"  📁 {folder}/{filename}")
            print(f"     Would become: {fix_filename(filename)}")
    else:
        print("✅ No problematic files found!")


def is_problematic_filename(filename: str) -> bool:
    """Check if a filename has double PO patterns."""
    
    # Check for various double PO patterns
    patterns = [
        filename.startswith("POPO"),  # POPO123456_
        filename.startswith("PO_") and "_PO_" in filename,  # PO_PO_
        filename.startswith("PO") and "_" in filename and any(part.startswith("PO") for part in filename.split("_")[1:])  # PO123_PO456_
    ]
    
    return any(patterns)


def main():
    """Main function."""
    
    print("🔧 Double PO Prefix Fixer")
    print("=" * 60)
    print("This script will fix files with double PO prefixes like:")
    print("  • POPO15362783_document.pdf -> PO15362783_document.pdf")
    print("  • PO_PO_document.pdf -> PO_document.pdf")
    print("  • PO123_PO456_document.pdf -> PO123_document.pdf")
    print()
    
    # First, scan for problematic files
    find_problematic_files()
    
    print(f"\n" + "=" * 60)
    response = input("Do you want to fix these files? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        fix_double_po_prefixes()
    else:
        print("❌ Operation cancelled.")


if __name__ == "__main__":
    main() 