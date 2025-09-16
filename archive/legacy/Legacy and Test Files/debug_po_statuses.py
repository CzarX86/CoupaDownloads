#!/usr/bin/env python3
"""
Debug script to check PO statuses in Excel.
"""

import os
import sys

# Add the parallel_test module to path
parallel_test_dir = os.path.join(os.path.dirname(__file__), "src", "utils", "parallel_test")
sys.path.insert(0, parallel_test_dir)

from excel_processor import ExcelProcessor

def debug_po_statuses():
    """Debug PO statuses in Excel."""
    print("🔍 Debugging PO Statuses in Excel")
    print("=" * 40)
    
    # Initialize Excel processor
    excel_processor = ExcelProcessor()
    
    # Read Excel
    excel_path = excel_processor.get_excel_file_path()
    po_entries, original_cols, hierarchy_cols, has_hierarchy_data = excel_processor.read_po_numbers_from_excel(excel_path)
    
    print(f"📊 Total POs loaded: {len(po_entries)}")
    
    # Check status distribution
    status_counts = {}
    for po in po_entries:
        status = po.get('status', 'Unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n📋 Status distribution:")
    for status, count in status_counts.items():
        print(f"   {status}: {count} POs")
    
    # Show first few POs with their statuses
    print(f"\n📋 First 10 POs:")
    for i, po in enumerate(po_entries[:10]):
        print(f"   {i+1}. {po['po_number']}: {po.get('status', 'Unknown')}")
    
    # Check how many are 'Pending'
    pending_pos = [po for po in po_entries if po.get('status', 'Pending') == 'Pending']
    print(f"\n📊 POs with status 'Pending': {len(pending_pos)}")
    
    if pending_pos:
        print(f"📋 First 5 Pending POs:")
        for i, po in enumerate(pending_pos[:5]):
            print(f"   {i+1}. {po['po_number']}: {po.get('status', 'Unknown')}")
    else:
        print("❌ No POs with status 'Pending' found!")
        
        # Check what statuses exist
        print(f"\n🔍 Available statuses: {list(status_counts.keys())}")
        
        # Suggest resetting some POs to 'Pending'
        print(f"\n💡 To test the system, you can reset some POs to 'Pending' status")

if __name__ == "__main__":
    debug_po_statuses()
