#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '/Users/juliocezar/Dev/work/CoupaDownloads')

os.environ['ENABLE_INTERACTIVE_UI'] = 'false'
os.environ['HEADLESS'] = 'true'
os.environ['USE_PROCESS_POOL'] = 'false'
os.environ['PROC_WORKERS'] = '2'
os.environ['EXCEL_FILE_PATH'] = '/Users/juliocezar/Dev/work/CoupaDownloads/data/input/test_parallel_simple.csv'

print("=== Test Configuration ===")
print(f"CSV file: {os.environ['EXCEL_FILE_PATH']}")
print(f"Process pool: {os.environ['USE_PROCESS_POOL']}")
print(f"Workers: {os.environ['PROC_WORKERS']}")
print(f"Headless: {os.environ['HEADLESS']}")

# Test CSV reading first
print("\n=== Testing CSV Reading ===")
try:
    from EXPERIMENTAL.corelib.excel_processor import ExcelProcessor
    ep = ExcelProcessor()
    entries, cols, hier_cols, has_hier = ep.read_po_numbers_from_excel(os.environ['EXCEL_FILE_PATH'])
    print(f"Entries read: {len(entries)}")
    print(f"First 3 entries: {entries[:3] if entries else None}")
    
    valid_entries = ep.process_po_numbers(entries)
    print(f"Valid entries: {len(valid_entries)}")
    print(f"First 3 valid: {valid_entries[:3] if valid_entries else None}")
    
except Exception as e:
    print(f"CSV reading failed: {e}")
    sys.exit(1)

print("\n=== Starting Main App ===")
try:
    from EXPERIMENTAL.core.main import main
    main()
except KeyboardInterrupt:
    print("\nInterrupted by user")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()