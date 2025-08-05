#!/usr/bin/env python3
"""
Test script to verify MSG naming logic.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.msg_processor import msg_processor


def test_naming_logic():
    """Test the naming logic for MSG files."""
    
    print("🧪 Testing MSG Naming Logic")
    print("=" * 40)
    
    # Test cases
    test_cases = [
        {
            "filename": "PO123456_sample_email.msg",
            "po_number": "123456",
            "expected_clean": "sample_email",
            "expected_pdf": "PO123456_sample_email.pdf",
            "expected_subfolder": "PO123456_sample_email"
        },
        {
            "filename": "sample_email.msg",
            "po_number": "123456",
            "expected_clean": "sample_email",
            "expected_pdf": "PO123456_sample_email.pdf",
            "expected_subfolder": "PO123456_sample_email"
        },
        {
            "filename": "PO789012_complex_email.msg",
            "po_number": "789012",
            "expected_clean": "complex_email",
            "expected_pdf": "PO789012_complex_email.pdf",
            "expected_subfolder": "PO789012_complex_email"
        },
        {
            "filename": "email_with_attachments.msg",
            "po_number": "456789",
            "expected_clean": "email_with_attachments",
            "expected_pdf": "PO456789_email_with_attachments.pdf",
            "expected_subfolder": "PO456789_email_with_attachments"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📧 Test Case {i}: {test_case['filename']}")
        print(f"   PO Number: {test_case['po_number']}")
        
        # Extract filename without extension
        msg_filename = test_case['filename']
        msg_name_without_ext = os.path.splitext(msg_filename)[0]
        
        # Apply the same logic as in the processor
        clean_msg_name = msg_name_without_ext
        
        # Handle cases where filename already has PO prefix
        if clean_msg_name.upper().startswith('PO'):
            # Split by underscore to check for PO + numbers pattern
            parts = clean_msg_name.split('_', 1)
            if len(parts) > 1 and parts[0].upper().startswith('PO') and parts[0][2:].isdigit():
                # Remove the PO + numbers part, keep the rest
                clean_msg_name = parts[1]
            else:
                # Just remove "PO" prefix
                clean_msg_name = clean_msg_name[2:]
        
        # Generate expected names
        expected_pdf = f"PO{test_case['po_number']}_{clean_msg_name}.pdf"
        expected_subfolder = f"PO{test_case['po_number']}_{clean_msg_name}"
        
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


if __name__ == "__main__":
    test_naming_logic() 