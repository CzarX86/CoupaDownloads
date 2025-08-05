#!/usr/bin/env python3
"""
Test script to verify file type restrictions have been removed.
This script tests various file types to ensure they are now allowed.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.downloader import FileManager
from core.config import Config


def test_file_type_restrictions():
    """Test that file type restrictions have been removed."""
    
    print("🧪 Testing File Type Restrictions Removal")
    print("=" * 50)
    
    # Test various file types
    test_files = [
        # Previously allowed files
        "document.pdf",
        "email.msg", 
        "report.docx",
        
        # Previously restricted files (should now be allowed)
        "image.jpg",
        "photo.png",
        "data.xlsx",
        "spreadsheet.csv",
        "archive.zip",
        "compressed.rar",
        "text.txt",
        "config.xml",
        "presentation.pptx",
        "video.mp4",
        "audio.mp3",
        "script.py",
        "webpage.html",
        "database.db",
        "executable.exe",
        "no_extension_file"
    ]
    
    print(f"📋 Testing {len(test_files)} file types...")
    print(f"🔧 Current ALLOWED_EXTENSIONS: {Config.ALLOWED_EXTENSIONS}")
    print()
    
    all_passed = True
    
    for filename in test_files:
        is_supported = FileManager.is_supported_file(filename)
        status = "✅ ALLOWED" if is_supported else "❌ BLOCKED"
        
        print(f"   {status} {filename}")
        
        if not is_supported:
            all_passed = False
    
    print()
    print("=" * 50)
    
    if all_passed:
        print("🎉 SUCCESS: All file types are now allowed!")
        print("   File type restrictions have been successfully removed.")
        print("   The system will now download any file type found in Coupa.")
    else:
        print("❌ FAILED: Some file types are still restricted.")
        print("   Please check the configuration settings.")
    
    return all_passed


def show_configuration_options():
    """Show different configuration options for file types."""
    
    print("\n🔧 Configuration Options")
    print("=" * 30)
    
    print("1. Allow ALL file types (current setting):")
    print("   ALLOWED_EXTENSIONS: List[str] = []")
    print()
    
    print("2. Allow common file types:")
    print("   ALLOWED_EXTENSIONS: List[str] = [")
    print("       '.pdf', '.msg', '.docx', '.xlsx', '.txt', '.jpg', '.png',")
    print("       '.zip', '.rar', '.csv', '.xml', '.pptx', '.mp4', '.mp3'")
    print("   ]")
    print()
    
    print("3. Allow only specific types:")
    print("   ALLOWED_EXTENSIONS: List[str] = ['.pdf', '.docx', '.xlsx']")
    print()
    
    print("4. Block specific types (advanced):")
    print("   # Set to empty list and modify is_supported_file() method")
    print("   # to exclude specific extensions instead")


if __name__ == "__main__":
    try:
        success = test_file_type_restrictions()
        show_configuration_options()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1) 