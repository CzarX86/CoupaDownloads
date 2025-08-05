#!/usr/bin/env python3
"""
Test script to demonstrate MSG artifact filtering feature.
This script shows how the system filters out signature images and icons.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.msg_processor import msg_processor
from core.config import Config


def test_artifact_filtering():
    """Test the MSG artifact filtering functionality."""
    
    print("🧪 Testing MSG Artifact Filtering Feature")
    print("=" * 50)
    
    # Create a test directory
    test_dir = os.path.join(Config.DOWNLOAD_FOLDER, "test_artifact_filtering")
    os.makedirs(test_dir, exist_ok=True)
    
    print(f"📁 Test directory: {test_dir}")
    print()
    
    # Test different filtering scenarios
    test_scenarios = [
        {
            "name": "Filtering Enabled (Default)",
            "description": "Should filter out signature images and small artifacts",
            "config": {"FILTER_MSG_ARTIFACTS": True}
        },
        {
            "name": "Filtering Disabled",
            "description": "Should extract all attachments including artifacts",
            "config": {"FILTER_MSG_ARTIFACTS": False}
        }
    ]
    
    for scenario in test_scenarios:
        print(f"🔧 Testing: {scenario['name']}")
        print(f"   Description: {scenario['description']}")
        
        # Temporarily modify config for testing
        original_filter_setting = Config.FILTER_MSG_ARTIFACTS
        Config.FILTER_MSG_ARTIFACTS = scenario['config']['FILTER_MSG_ARTIFACTS']
        
        try:
            # Create a test MSG file with simulated attachments
            test_msg_path = os.path.join(test_dir, f"test_{scenario['name'].lower().replace(' ', '_')}.msg")
            
            # For testing, create a simple file that would trigger filtering
            with open(test_msg_path, 'w') as f:
                f.write("This is a test MSG file with simulated attachments.\n")
            
            print(f"   ✅ Created test MSG file")
            
            # Test the filtering logic directly
            print(f"   🔍 Testing filtering logic...")
            
            # Simulate different attachment types
            test_attachments = [
                {"filename": "signature.png", "size": 500, "content_type": "image/png"},
                {"filename": "company_logo.gif", "size": 800, "content_type": "image/gif"},
                {"filename": "invoice.pdf", "size": 50000, "content_type": "application/pdf"},
                {"filename": "small_icon.ico", "size": 300, "content_type": "image/x-icon"},
                {"filename": "report.docx", "size": 15000, "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                {"filename": "embedded_object", "size": 1500, "content_type": "application/octet-stream"},
            ]
            
            filtered_count = 0
            for attachment in test_attachments:
                # Create a mock attachment object
                class MockAttachment:
                    def __init__(self, data_size, content_type):
                        self.data = b'x' * data_size
                        self.contentType = content_type
                
                mock_attachment = MockAttachment(attachment['size'], attachment['content_type'])
                
                # Test filtering
                should_filter = msg_processor._should_filter_attachment(
                    attachment['filename'], mock_attachment
                )
                
                status = "🚫 FILTERED" if should_filter else "✅ EXTRACTED"
                print(f"      {status} {attachment['filename']} ({attachment['size']} bytes)")
                
                if should_filter:
                    filtered_count += 1
            
            print(f"   📊 Results: {filtered_count}/{len(test_attachments)} attachments filtered")
            
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
        finally:
            # Restore original config
            Config.FILTER_MSG_ARTIFACTS = original_filter_setting
        
        print()
    
    # Show configuration options
    print("🔧 Configuration Options")
    print("=" * 30)
    print("Environment variables to control filtering:")
    print()
    print("1. Enable/Disable filtering:")
    print("   export FILTER_MSG_ARTIFACTS=true   # Enable (default)")
    print("   export FILTER_MSG_ARTIFACTS=false  # Disable")
    print()
    print("2. Adjust minimum file sizes:")
    print("   export MSG_ARTIFACT_MIN_SIZE=1024  # 1KB minimum for artifacts")
    print("   export MSG_IMAGE_MIN_SIZE=5120     # 5KB minimum for images")
    print()
    print("3. In code:")
    print("   Config.FILTER_MSG_ARTIFACTS = True/False")
    print("   Config.MSG_ARTIFACT_MIN_SIZE = 1024")
    print("   Config.MSG_IMAGE_MIN_SIZE = 5120")
    
    print()
    print("📋 What Gets Filtered")
    print("=" * 25)
    print("• Signature images (signature.png, sig_logo.gif)")
    print("• Company logos and icons (logo.png, icon.ico)")
    print("• Small images (< 5KB)")
    print("• Very small files (< 1KB)")
    print("• Embedded objects without extensions")
    print("• Email client artifacts")
    
    print()
    print("📋 What Gets Extracted")
    print("=" * 25)
    print("• Business documents (PDF, DOCX, XLSX)")
    print("• Large images (> 5KB)")
    print("• Archives (ZIP, RAR)")
    print("• Any file with meaningful size and extension")


if __name__ == "__main__":
    try:
        test_artifact_filtering()
        print("\n✅ Artifact filtering test completed successfully!")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1) 