#!/usr/bin/env python3
"""
Debug version - step by step driver download test
"""

import sys
import os
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def step_pause(step_num, description, seconds=3):
    """Pause between steps with countdown"""
    print(f"\n{'='*60}")
    print(f"🔍 STEP {step_num}: {description}")
    print(f"{'='*60}")
    
    for i in range(seconds, 0, -1):
        print(f"⏳ Starting in {i}s...", end='\r')
        time.sleep(1)
    print("▶️  Executing...        ")

def main():
    print("🧪 EdgeDriver Download Test - Debug Mode")
    print("🐌 Slow execution with step-by-step debugging")
    
    try:
        step_pause(1, "Importing DriverManager", 2)
        from core.driver_manager import DriverManager
        print("✅ Import successful")
        
        step_pause(2, "Initializing DriverManager", 2)
        dm = DriverManager()
        print(f"✅ Platform: {dm.platform}")
        print(f"📁 Project: {dm.project_root}")
        print(f"📁 Drivers: {dm.drivers_dir}")
        
        step_pause(3, "Checking temp directory", 2)
        temp_dir = Path(dm.drivers_dir) / "tmp"
        print(f"📍 Temp path: {temp_dir}")
        print(f"📂 Exists: {temp_dir.exists()}")
        
        if temp_dir.exists():
            contents = list(temp_dir.iterdir())
            print(f"📋 Current files: {len(contents)}")
            for item in contents[:3]:
                print(f"   - {item.name}")
        
        step_pause(4, "Detecting Edge version", 2)
        edge_version = dm.get_edge_version()
        print(f"✅ Edge version: {edge_version}")
        
        if edge_version:
            step_pause(5, "Finding compatible driver version", 2)
            driver_version = dm.get_compatible_driver_version(edge_version)
            print(f"✅ Driver version: {driver_version}")
            
            step_pause(6, "Starting download (this may take a moment)", 3)
            print("📥 Downloading EdgeDriver...")
            start_time = time.time()
            
            zip_path = dm.download_driver(driver_version)
            
            download_time = time.time() - start_time
            print(f"✅ Downloaded in {download_time:.2f}s")
            print(f"📍 Location: {zip_path}")
            
            step_pause(7, "Extracting driver binary", 2)
            driver_path = dm.extract_driver(zip_path)
            print(f"✅ Extracted to: {driver_path}")
            
            step_pause(8, "Analyzing results", 2)
            driver_dir = Path(driver_path).parent
            files = list(driver_dir.iterdir())
            
            print(f"📁 Files in temp dir: {len(files)}")
            for f in files:
                size = f.stat().st_size
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.1f} MB"
                else:
                    size_str = f"{size/1024:.1f} KB"
                print(f"   - {f.name} ({size_str})")
            
            driver_files = [f for f in files if "msedgedriver" in f.name and not f.name.endswith('.zip')]
            
            if len(driver_files) == 1:
                print(f"✅ SUCCESS: Exactly 1 driver binary extracted!")
            else:
                print(f"⚠️  Found {len(driver_files)} driver files")
            
            step_pause(9, "Testing driver functionality", 2)
            if dm.verify_driver(driver_path):
                print("✅ Driver verification PASSED")
            else:
                print("❌ Driver verification FAILED")
            
            step_pause(10, "Cleanup demonstration", 2)
            zip_files = [f for f in files if f.name.endswith('.zip')]
            for zip_file in zip_files:
                try:
                    size_mb = zip_file.stat().st_size / (1024*1024)
                    os.remove(zip_file)
                    print(f"🧹 Removed {zip_file.name} ({size_mb:.1f} MB)")
                except Exception as e:
                    print(f"⚠️  Could not remove {zip_file.name}: {e}")
            
            print(f"\n🎉 TEST COMPLETED SUCCESSFULLY!")
            print(f"📊 Summary:")
            print(f"   Platform: {dm.platform}")
            print(f"   Edge: {edge_version}")
            print(f"   Driver: {driver_version}")
            print(f"   Location: {driver_path}")
            print(f"   Download time: {download_time:.2f}s")
            
        else:
            print("❌ Could not detect Edge version")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()