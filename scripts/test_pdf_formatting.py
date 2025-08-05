#!/usr/bin/env python3
"""
Test script to demonstrate improved PDF formatting with proper paragraphs.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.msg_processor import msg_processor


def test_pdf_formatting():
    """Test the improved PDF formatting with proper paragraphs."""
    
    print("🧪 Testing Improved PDF Formatting")
    print("=" * 40)
    
    # Test email body with proper formatting
    test_email_body = """Dear Team,

I hope this email finds you well. I am writing to inform you about the recent approval of your purchase order request.

The following items have been approved:
- Item 1: Office supplies
- Item 2: Computer equipment
- Item 3: Software licenses

Please note that the delivery will be scheduled for next week. You will receive a confirmation email with the exact delivery date and time.

If you have any questions or concerns, please don't hesitate to contact us.

Best regards,
Procurement Team

---
This is an automated message. Please do not reply to this email."""
    
    print("📧 Original Email Body:")
    print("-" * 30)
    print(test_email_body)
    print()
    
    print("📄 Formatted HTML Output:")
    print("-" * 30)
    formatted_html = msg_processor._format_email_body(test_email_body)
    print(formatted_html)
    print()
    
    # Test edge cases
    test_cases = [
        {
            "name": "Empty body",
            "body": "",
            "expected": "No body content"
        },
        {
            "name": "Single paragraph",
            "body": "This is a single paragraph email.",
            "expected": "<p>This is a single paragraph email.</p>"
        },
        {
            "name": "Multiple paragraphs",
            "body": "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3.",
            "expected": "3 paragraphs"
        },
        {
            "name": "Mixed line breaks",
            "body": "Line 1\nLine 2\n\nParagraph 2\nLine 3\nLine 4",
            "expected": "2 paragraphs with internal line breaks"
        }
    ]
    
    print("🔍 Testing Edge Cases:")
    print("-" * 30)
    
    for test_case in test_cases:
        print(f"\n📧 {test_case['name']}:")
        print(f"   Input: {repr(test_case['body'])}")
        
        formatted = msg_processor._format_email_body(test_case['body'])
        print(f"   Output: {formatted}")
        
        if formatted:
            print(f"   ✅ Formatted successfully")
        else:
            print(f"   ⚠️ Empty result")


if __name__ == "__main__":
    test_pdf_formatting() 