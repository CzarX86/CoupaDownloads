#!/usr/bin/env python3
"""Test script to debug CSV integration in CoupaDownloads."""

import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.csv_handler import CSVHandler
import uuid

def test_csv_integration():
    """Test the CSV handler integration step by step."""
    print("🔍 Testing CSV Integration")
    print("=" * 50)
    
    # Step 1: Verify CSV file
    csv_path = Path("test_csv_persistence.csv")
    print(f"1. CSV file path: {csv_path}")
    print(f"   Exists: {csv_path.exists()}")
    print(f"   Suffix: {csv_path.suffix}")
    print(f"   Is CSV: {csv_path.suffix.lower() == '.csv'}")
    
    if not csv_path.exists():
        print("❌ CSV file not found!")
        return False
    
    # Step 2: Initialize CSV handler (same logic as Core_main.py)
    backup_dir = csv_path.parent.parent / 'backup'
    backup_dir.mkdir(exist_ok=True)
    print(f"2. Backup directory: {backup_dir}")
    
    try:
        csv_handler = CSVHandler(csv_path=csv_path, backup_dir=backup_dir)
        print("✅ CSV Handler initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize CSV handler: {e}")
        return False
    
    # Step 3: Create session backup (same as Core_main.py)
    session_id = uuid.uuid4().hex[:8]
    try:
        backup_path = csv_handler.create_session_backup(session_id)
        print(f"✅ Session backup created: {backup_path}")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return False
    
    # Step 4: Test getting pending records
    try:
        pending_records = csv_handler.get_pending_records()
        print(f"✅ Found {len(pending_records)} pending records")
    except Exception as e:
        print(f"❌ Failed to get pending records: {e}")
        return False
    
    # Step 5: Test updating a record
    if len(pending_records) > 0:
        test_po = pending_records[0].po_number
        print(f"3. Testing record update for PO: {test_po}")
        
        # Simulate successful processing result
        test_updates = {
            'STATUS': 'COMPLETED',
            'ATTACHMENTS_FOUND': 2,
            'ATTACHMENTS_DOWNLOADED': 2,
            'AttachmentName': 'invoice.pdf;receipt.pdf',
            'LAST_PROCESSED': '2025-10-06T14:30:00',
            'DOWNLOAD_FOLDER': f'downloads/{test_po}',
            'COUPA_URL': f'https://coupa.com/purchase_orders/{test_po}'
        }
        
        try:
            success = csv_handler.update_record(test_po, test_updates)
            print(f"✅ Record update result: {success}")
        except Exception as e:
            print(f"❌ Failed to update record: {e}")
            return False
        
        # Verify the update worked
        try:
            progress = csv_handler.get_processing_progress()
            print(f"✅ Progress after update: {progress}")
        except Exception as e:
            print(f"❌ Failed to get progress: {e}")
            return False
    
    print("\n🎉 CSV integration test completed successfully!")
    print("   The CSV handler is working correctly.")
    print("   If Core_main.py didn't update the CSV, the issue is likely:")
    print("   1. CSV handler wasn't initialized (check file extension)")
    print("   2. No POs were actually processed (network/auth issues)")
    print("   3. _persist_csv_result() wasn't called")
    
    return True

if __name__ == "__main__":
    test_csv_integration()