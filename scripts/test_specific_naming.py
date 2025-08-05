#!/usr/bin/env python3
"""
Test script for the specific naming case: PO15345517_PO15345517_Your_demand_is_approved
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.msg_processor import msg_processor


def test_specific_naming_case():
    """Test the specific naming case mentioned by the user."""
    
    print("🧪 Testing Specific Naming Case")
    print("=" * 40)
    
    # The specific case mentioned by the user
    test_cases = [
        {
            "filename": "PO15345517_PO15345517_Your_demand_is_approved.msg",
            "po_number": "15345517",
            "expected_clean": "Your_demand_is_approved",
            "expected_pdf": "PO15345517_MSG_Your_demand_is_approved.pdf",
            "expected_subfolder": "PO15345517_MSG_Your_demand_is_approved"
        },
        {
            "filename": "PO15345517_Your_demand_is_approved.msg",
            "po_number": "15345517", 
            "expected_clean": "Your_demand_is_approved",
            "expected_pdf": "PO15345517_MSG_Your_demand_is_approved.pdf",
            "expected_subfolder": "PO15345517_MSG_Your_demand_is_approved"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📧 Test Case {i}: {test_case['filename']}")
        print(f"   PO Number: {test_case['po_number']}")
        
        # Extract filename without extension
        msg_filename = test_case['filename']
        msg_name_without_ext = os.path.splitext(msg_filename)[0]
        
        # Apply the same logic as in the processor
        clean_msg_name = msg_processor._remove_po_prefixes(msg_name_without_ext)
        
        # Generate expected names with MSG prefix
        expected_pdf = f"PO{test_case['po_number']}_MSG_{clean_msg_name}.pdf"
        expected_subfolder = f"PO{test_case['po_number']}_MSG_{clean_msg_name}"
        
        print(f"   Original: {msg_name_without_ext}")
        print(f"   Cleaned: {clean_msg_name}")
        print(f"   PDF: {expected_pdf}")
        print(f"   Subfolder: {expected_subfolder}")
        
        # Check if results match expectations
        pdf_match = expected_pdf == test_case['expected_pdf']
        subfolder_match = expected_subfolder == test_case['expected_subfolder']
        
        print(f"   PDF Match: {'✅' if pdf_match else '❌'}")
        print(f"   Subfolder Match: {'✅' if subfolder_match else '❌'}")
        
        if not pdf_match or not subfolder_match:
            print(f"   Expected PDF: {test_case['expected_pdf']}")
            print(f"   Expected Subfolder: {test_case['expected_subfolder']}")
            print(f"   ❌ ISSUE: Duplicate PO prefix detected!")


if __name__ == "__main__":
    test_specific_naming_case() 