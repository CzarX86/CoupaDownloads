#!/usr/bin/env python3
"""
Test script to verify folder hierarchy functionality.
"""

import os
import sys
from src.core.excel_processor import ExcelProcessor
from src.core.folder_hierarchy import FolderHierarchyManager

def test_hierarchy():
    """Test the folder hierarchy functionality."""
    print("🧪 Testing Folder Hierarchy Functionality")
    print("=" * 50)
    
    # Initialize components
    excel_processor = ExcelProcessor()
    folder_hierarchy = FolderHierarchyManager()
    
    try:
        # Read Excel file
        excel_path = excel_processor.get_excel_file_path()
        po_entries, original_cols, hierarchy_cols, has_hierarchy_data = excel_processor.read_po_numbers_from_excel(excel_path)
        
        print(f"📊 Excel Analysis Results:")
        print(f"   Original columns: {original_cols}")
        print(f"   Hierarchy columns: {hierarchy_cols}")
        print(f"   Has hierarchy data: {has_hierarchy_data}")
        print()
        
        # Test with first few POs
        test_pos = po_entries[:5]
        
        for i, po_data in enumerate(test_pos):
            print(f"🔍 Testing PO {i+1}: {po_data.get('po_number', 'Unknown')}")
            
            try:
                # Create folder path
                folder_path = folder_hierarchy.create_folder_path(
                    po_data, hierarchy_cols, has_hierarchy_data
                )
                
                print(f"   ✅ Created folder: {folder_path}")
                
                # Check if folder exists
                if os.path.exists(folder_path):
                    print(f"   ✅ Folder exists: {folder_path}")
                else:
                    print(f"   ❌ Folder does not exist: {folder_path}")
                
                # Get hierarchy summary
                summary = folder_hierarchy.get_hierarchy_summary(po_data, hierarchy_cols, has_hierarchy_data)
                print(f"   📋 Summary: {summary}")
                
            except Exception as e:
                print(f"   ❌ Error creating folder: {e}")
            
            print()
        
        print("✅ Hierarchy test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hierarchy()
