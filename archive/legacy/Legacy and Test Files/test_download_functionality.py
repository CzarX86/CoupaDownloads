#!/usr/bin/env python3
"""
Test script to verify download functionality with hierarchical folders.
"""

import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.utils.parallel_test.main import MainApp

def test_download_functionality():
    """Test download functionality with a few POs that have attachments."""
    print("🧪 Testing Download Functionality with Hierarchical Folders")
    print("=" * 60)
    
    # Set environment variables for testing
    os.environ['RANDOM_SAMPLE_POS'] = '3'  # Test with 3 POs
    
    try:
        # Reset some POs to Pending
        import pandas as pd
        df = pd.read_excel('data/input/input.xlsx', sheet_name='PO_Data')
        
        # Find POs that have attachments
        pos_with_attachments = df[df['ATTACHMENTS_FOUND'] > 0]['PO_NUMBER'].head(3).tolist()
        
        if pos_with_attachments:
            print(f"📋 Found POs with attachments: {pos_with_attachments}")
            
            # Reset these POs to Pending
            for po in pos_with_attachments:
                mask = df['PO_NUMBER'] == po
                df.loc[mask, 'STATUS'] = 'Pending'
            
            df.to_excel('data/input/input.xlsx', sheet_name='PO_Data', index=False)
            print("✅ Reset POs with attachments to Pending status")
        else:
            print("⚠️ No POs with attachments found, using first 3 POs")
            df.loc[df.index[:3], 'STATUS'] = 'Pending'
            df.to_excel('data/input/input.xlsx', sheet_name='PO_Data', index=False)
        
        # Run the main application
        app = MainApp()
        app.run()
        
        print("\n✅ Download functionality test completed!")
        
        # Check if files were downloaded
        print("\n🔍 Checking downloaded files...")
        import subprocess
        result = subprocess.run(['find', os.path.expanduser('~/Downloads/CoupaDownloads'), '-name', '*.pdf', '-o', '-name', '*.xlsx', '-o', '-name', '*.msg', '-o', '-name', '*.eml', '-o', '-name', '*.docx'], capture_output=True, text=True)
        
        if result.stdout.strip():
            print("📁 Files found in hierarchical folders:")
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f"   📄 {line}")
        else:
            print("❌ No files found in hierarchical folders!")
            
    except Exception as e:
        print(f"\n❌ Error during download functionality test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_download_functionality()
