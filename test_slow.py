#!/usr/bin/env python3
import sys
import time
from pathlib import Path

sys.path.insert(0, 'src')

print("🧪 EdgeDriver Test - Slow Motion")
print("=" * 40)

try:
    print("\n⏳ Step 1/5: Importing...")
    time.sleep(1)
    from core.driver_manager import DriverManager
    print("✅ Import OK")
    
    print("\n⏳ Step 2/5: Initializing...")
    time.sleep(1)
    dm = DriverManager()
    print(f"✅ Platform: {dm.platform}")
    
    print("\n⏳ Step 3/5: Edge detection...")
    time.sleep(1)
    edge_version = dm.get_edge_version()
    print(f"✅ Edge: {edge_version}")
    
    if edge_version:
        print("\n⏳ Step 4/5: Driver version...")
        time.sleep(1)
        driver_version = dm.get_compatible_driver_version(edge_version)
        print(f"✅ Driver: {driver_version}")
        
        print("\n⏳ Step 5/5: Download & extract...")
        print("📥 Downloading...")
        start = time.time()
        zip_path = dm.download_driver(driver_version)
        print("📤 Extracting...")
        driver_path = dm.extract_driver(zip_path)
        duration = time.time() - start
        
        print(f"\n🎉 SUCCESS!")
        print(f"⏱️  Time: {duration:.1f}s")
        print(f"📍 Location: {driver_path}")
        
        # Quick analysis
        driver_dir = Path(driver_path).parent
        files = list(driver_dir.iterdir())
        print(f"📁 Files: {len(files)}")
        for f in files:
            print(f"  - {f.name}")
        
    else:
        print("❌ No Edge detected")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n🏁 Test done!")