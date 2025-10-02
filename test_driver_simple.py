#!/usr/bin/env python3
"""
Test script for EdgeDriver download and extraction to temp directory.
With breakpoints and slow execution for debugging.
"""

import sys
import os
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def pause_with_message(message, duration=2):
    """Pause execution with a message and countdown."""
    print(f"\n⏸️  {message}")
    for i in range(duration, 0, -1):
        print(f"   Continuing in {i}s...", end="\r")
        time.sleep(1)
    print("   ✅ Continuing...      ")

def wait_for_enter(message="Press ENTER to continue"):
    """Wait for user input before continuing."""
    print(f"\n🔍 {message}")
    input("   >>> ")

def test_driver_download():
    """Test EdgeDriver download and extraction with breakpoints."""
    print("🧪 Testing EdgeDriver download and extraction...")
    print("=" * 60)
    print("🔍 This test includes breakpoints for step-by-step debugging")
    print("=" * 60)
    
    wait_for_enter("Ready to start? This will import DriverManager")
    
    try:
        # BREAKPOINT 1: Import
        print("\n📦 STEP 1: Importing DriverManager...")
        from core.driver_manager import DriverManager
        print("✅ DriverManager imported successfully")
        pause_with_message("Import completed", 2)
        
        # BREAKPOINT 2: Initialize
        print("\n🏗️  STEP 2: Initializing DriverManager...")
        dm = DriverManager()
        print(f"✅ Platform detected: {dm.platform}")
        print(f"📁 Project root: {dm.project_root}")
        print(f"📁 Drivers directory: {dm.drivers_dir}")
        pause_with_message("Initialization completed", 2)
        
        # BREAKPOINT 3: Check temp directory
        print("\n📁 STEP 3: Checking temp directory structure...")
        temp_dir = Path(dm.drivers_dir) / "tmp"
        print(f"� Temp directory path: {temp_dir}")
        print(f"� Temp directory exists: {temp_dir.exists()}")
        
        if temp_dir.exists():
            contents = list(temp_dir.iterdir())
            print(f"📋 Current contents: {len(contents)} items")
            for item in contents[:5]:  # Show max 5 items
                print(f"   - {item.name}")
        else:
            print("📝 Temp directory will be created during download")
        
        wait_for_enter("Ready to detect Edge version?")
        
        # BREAKPOINT 4: Edge version detection
        print("\n🌐 STEP 4: Detecting Edge browser version...")
        edge_version = dm.get_edge_version()
        if edge_version:
            print(f"✅ Edge version detected: {edge_version}")
            pause_with_message("Version detection completed", 2)
            
            # BREAKPOINT 5: Driver version compatibility
            print("\n🔧 STEP 5: Finding compatible driver version...")
            driver_version = dm.get_compatible_driver_version(edge_version)
            print(f"✅ Compatible driver version: {driver_version}")
            print(f"📍 Will download from: {dm.EDGEDRIVER_BASE_URL}/{driver_version}/")
            
            wait_for_enter("Ready to start download? This will create temp directory and download the zip file")
            
            # BREAKPOINT 6: Download
            print("\n⬇️ STEP 6: Downloading EdgeDriver...")
            print("📦 Starting download to temp directory...")
            start_time = time.time()
            
            zip_path = dm.download_driver(driver_version)
            
            download_time = time.time() - start_time
            print(f"\n✅ Download completed in {download_time:.2f}s")
            print(f"� Downloaded to: {zip_path}")
            print(f"📏 File size: {Path(zip_path).stat().st_size / (1024*1024):.1f} MB")
            
            wait_for_enter("Ready to extract the driver binary?")
            
            # BREAKPOINT 7: Extraction
            print("\n📤 STEP 7: Extracting driver binary...")
            print("🔍 Looking for msedgedriver binary in zip...")
            
            driver_path = dm.extract_driver(zip_path)
            
            print(f"✅ Driver extracted to: {driver_path}")
            
            # BREAKPOINT 8: Analysis
            print("\n📊 STEP 8: Analyzing extraction results...")
            print("=" * 40)
            
            driver_dir = Path(driver_path).parent
            extracted_files = list(driver_dir.iterdir())
            
            print(f"📁 Temp directory: {driver_dir}")
            print(f"📋 Total files in temp: {len(extracted_files)}")
            
            driver_files = [f for f in extracted_files if "msedgedriver" in f.name.lower()]
            other_files = [f for f in extracted_files if "msedgedriver" not in f.name.lower()]
            
            print(f"\n🎯 Driver files found: {len(driver_files)}")
            for f in driver_files:
                size_mb = f.stat().st_size / (1024 * 1024)
                is_executable = bool(f.stat().st_mode & 0o111)
                print(f"   - {f.name}")
                print(f"     Size: {size_mb:.1f} MB")
                print(f"     Executable: {'✅' if is_executable else '❌'}")
            
            print(f"\n📄 Other files: {len(other_files)}")
            for f in other_files:
                size_kb = f.stat().st_size / 1024
                print(f"   - {f.name} ({size_kb:.1f} KB)")
            
            # BREAKPOINT 9: Validation
            if len(driver_files) == 1 and len(other_files) == 1:  # 1 driver + 1 zip
                print(f"\n✅ SUCCESS: Only driver binary was extracted!")
                print(f"📝 Note: Zip file remains for cleanup testing")
            else:
                print(f"\n⚠️ ANALYSIS: Found {len(driver_files)} driver files + {len(other_files)} other files")
            
            wait_for_enter("Ready to test driver functionality?")
            
            # BREAKPOINT 10: Driver verification
            print("\n🧪 STEP 9: Testing driver functionality...")
            print("🔍 Running driver --version test...")
            
            if dm.verify_driver(driver_path):
                print("✅ Driver verification PASSED - driver is functional!")
            else:
                print("❌ Driver verification FAILED - driver may not work")
            
            pause_with_message("Verification completed", 2)
            
            # BREAKPOINT 11: Cleanup
            print("\n🧹 STEP 10: Cleanup demonstration...")
            print(f"📍 Zip file location: {zip_path}")
            
            wait_for_enter("Ready to clean up the zip file?")
            
            try:
                zip_size = Path(zip_path).stat().st_size / (1024*1024)
                os.remove(zip_path)
                print(f"✅ Cleaned up zip file ({zip_size:.1f} MB freed)")
            except Exception as e:
                print(f"⚠️ Could not clean zip: {e}")
            
            # Final summary
            print(f"\n🎉 FINAL SUMMARY:")
            print("=" * 40)
            print(f"✅ Platform: {dm.platform}")
            print(f"✅ Edge version: {edge_version}")
            print(f"✅ Driver version: {driver_version}")
            print(f"✅ Driver location: {driver_path}")
            print(f"✅ Download time: {download_time:.2f}s")
            print(f"✅ Only driver binary extracted: {'Yes' if len(driver_files) == 1 else 'No'}")
            print(f"✅ Driver functional: {'Yes' if dm.verify_driver(driver_path) else 'No'}")
                
        else:
            print("❌ Could not detect Edge version")
            
    except KeyboardInterrupt:
        print("\n⏸️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🏁 Test completed! Check temp directory for results.")
    if 'dm' in locals():
        print(f"📁 Temp location: {Path(dm.drivers_dir) / 'tmp'}")
    else:
        print(f"📁 Temp location: {project_root / 'drivers' / 'tmp'}")

if __name__ == "__main__":
    test_driver_download()