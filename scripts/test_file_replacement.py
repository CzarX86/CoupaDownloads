#!/usr/bin/env python3
"""
Test File Replacement
Demonstrates the improved file handling that replaces duplicates instead of creating them.
"""

import os
import sys
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import Config


def create_test_files():
    """Create test files to demonstrate replacement."""
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp(prefix="file_replacement_test_")
    print(f"📁 Created test directory: {test_dir}")
    
    # Create some test files
    test_files = [
        "PO15363269_document.pdf",
        "PO15363269_invoice.pdf", 
        "PO15363269_contract.docx"
    ]
    
    for filename in test_files:
        file_path = os.path.join(test_dir, filename)
        with open(file_path, 'w') as f:
            f.write(f"Test content for {filename}")
        print(f"   📄 Created: {filename}")
    
    return test_dir


def test_file_replacement(test_dir):
    """Test the file replacement logic."""
    print(f"\n🧪 Testing File Replacement Logic")
    print("=" * 50)
    
    # Test file that would be a duplicate
    duplicate_file = "PO15363269_document.pdf"
    source_file = os.path.join(test_dir, "new_document.pdf")
    
    # Create a "new" file that would replace the existing one
    with open(source_file, 'w') as f:
        f.write("New content for document.pdf")
    
    print(f"📄 Source file: {os.path.basename(source_file)}")
    print(f"📄 Target file: {duplicate_file}")
    
    # Simulate the replacement logic
    target_path = os.path.join(test_dir, duplicate_file)
    
    if os.path.exists(target_path):
        if Config.OVERWRITE_EXISTING_FILES:
            if Config.CREATE_BACKUP_BEFORE_OVERWRITE:
                # Create backup
                backup_path = target_path + ".backup"
                shutil.copy2(target_path, backup_path)
                print(f"   💾 Created backup: {os.path.basename(backup_path)}")
            
            print(f"   🔄 Replacing existing file: {duplicate_file}")
            os.remove(target_path)  # Remove existing file
        else:
            print(f"   ⏭️ Skipping existing file: {duplicate_file}")
            return
    
    # Move the new file to replace the old one
    shutil.move(source_file, target_path)
    print(f"   ✅ File replaced successfully")
    
    # Show final state
    print(f"\n📋 Final files in directory:")
    for filename in sorted(os.listdir(test_dir)):
        file_path = os.path.join(test_dir, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            print(f"   📄 {filename}: {content}")


def test_configuration_options():
    """Test different configuration options."""
    print(f"\n⚙️ Configuration Options")
    print("=" * 50)
    
    print(f"🔧 OVERWRITE_EXISTING_FILES: {Config.OVERWRITE_EXISTING_FILES}")
    print(f"🔧 CREATE_BACKUP_BEFORE_OVERWRITE: {Config.CREATE_BACKUP_BEFORE_OVERWRITE}")
    print(f"🔧 VERBOSE_OUTPUT: {Config.VERBOSE_OUTPUT}")
    
    print(f"\n💡 Environment Variables:")
    print(f"   export OVERWRITE_EXISTING_FILES=true    # Replace duplicates (default)")
    print(f"   export OVERWRITE_EXISTING_FILES=false   # Skip duplicates")
    print(f"   export CREATE_BACKUP_BEFORE_OVERWRITE=true  # Create backups")
    print(f"   export VERBOSE_OUTPUT=true              # Show detailed messages")


def main():
    """Main test function."""
    print("🎯 File Replacement Test")
    print("=" * 50)
    
    # Test configuration
    test_configuration_options()
    
    # Create test files
    test_dir = create_test_files()
    
    try:
        # Test replacement logic
        test_file_replacement(test_dir)
        
        print(f"\n✅ Test completed successfully!")
        print(f"📁 Test directory: {test_dir}")
        print(f"💡 Check the files to see the replacement in action")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # Clean up
        if input(f"\n🗑️ Delete test directory? (y/N): ").lower() == 'y':
            shutil.rmtree(test_dir)
            print(f"🗑️ Test directory deleted")
        else:
            print(f"📁 Test directory preserved: {test_dir}")


if __name__ == "__main__":
    main() 