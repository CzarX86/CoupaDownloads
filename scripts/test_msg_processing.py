#!/usr/bin/env python3
"""
Test script to demonstrate MSG file processing feature.
This script shows how the system handles MSG files with automatic conversion and attachment extraction.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.msg_processor import msg_processor
from core.config import Config


def test_msg_processing():
    """Test the MSG processing functionality."""
    
    print("🧪 Testing MSG File Processing Feature")
    print("=" * 50)
    
    # Create a test directory
    test_dir = os.path.join(Config.DOWNLOAD_FOLDER, "test_msg_processing")
    os.makedirs(test_dir, exist_ok=True)
    
    print(f"📁 Test directory: {test_dir}")
    print()
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Sample Email with Attachments",
            "msg_filename": "PO123456_sample_email.msg",
            "po_number": "123456",
            "supplier_folder": test_dir
        },
        {
            "name": "Simple Email without Attachments", 
            "msg_filename": "PO789012_simple_email.msg",
            "po_number": "789012",
            "supplier_folder": test_dir
        }
    ]
    
    for scenario in test_scenarios:
        print(f"📧 Testing: {scenario['name']}")
        print(f"   MSG File: {scenario['msg_filename']}")
        print(f"   PO Number: {scenario['po_number']}")
        
        # Create a dummy MSG file for testing
        msg_path = os.path.join(test_dir, scenario['msg_filename'])
        
        # For testing purposes, create a simple text file as MSG
        # In real usage, this would be an actual MSG file
        with open(msg_path, 'w') as f:
            f.write("This is a test MSG file content.\n")
            f.write("Subject: Test Email\n")
            f.write("From: sender@example.com\n")
            f.write("To: recipient@example.com\n")
        
        print(f"   ✅ Created test MSG file")
        
        # Test MSG processing
        try:
            success = msg_processor.process_msg_file(
                msg_path, 
                scenario['po_number'], 
                scenario['supplier_folder']
            )
            
            if success:
                print(f"   ✅ MSG processing completed successfully")
            else:
                print(f"   ❌ MSG processing failed")
                
        except Exception as e:
            print(f"   ❌ MSG processing error: {e}")
        
        print()
    
    # Show what would happen in real usage
    print("📋 Real Usage Example")
    print("=" * 30)
    print("When MSG processing is enabled:")
    print("1. User downloads MSG files from Coupa")
    print("2. System automatically detects .msg files")
    print("3. For each MSG file:")
    print("   • Creates subfolder: PO123456_email_name/")
    print("   • Converts MSG to PDF: PO123456_email_name.pdf")
    print("   • Extracts attachments to subfolder")
    print("   • Moves original MSG to subfolder")
    print("4. Result: Organized email content with attachments")
    
    print("\n🔧 Configuration")
    print("=" * 20)
    print("• MSG processing is enabled via user prompt")
    print("• Requires: extract-msg, weasyprint, or LibreOffice")
    print("• Fallback: HTML conversion if PDF tools unavailable")
    print("• Attachments: Automatically extracted and renamed")
    
    print("\n📁 Folder Structure Example")
    print("=" * 30)
    print("Supplier_Folder/")
    print("├── PO123456_original_msg.msg")
    print("├── PO123456_email_name/")
    print("│   ├── PO123456_email_name.pdf")
    print("│   ├── PO123456_attachment1.pdf")
    print("│   ├── PO123456_attachment2.xlsx")
    print("│   └── PO123456_original_msg.msg")
    print("└── other_files.pdf")
    
    return True


def show_installation_instructions():
    """Show installation instructions for MSG processing dependencies."""
    
    print("\n📦 Installation Instructions")
    print("=" * 35)
    print("To enable full MSG processing, install these dependencies:")
    print()
    print("1. Python libraries:")
    print("   pip install extract-msg weasyprint pdfkit")
    print()
    print("2. System dependencies (optional):")
    print("   • LibreOffice: For MSG to PDF conversion")
    print("   • wkhtmltopdf: For HTML to PDF conversion")
    print()
    print("3. Verify installation:")
    print("   python scripts/test_msg_processing.py")
    print()
    print("Note: The system will work with limited functionality")
    print("even if some dependencies are missing.")


if __name__ == "__main__":
    try:
        success = test_msg_processing()
        show_installation_instructions()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1) 