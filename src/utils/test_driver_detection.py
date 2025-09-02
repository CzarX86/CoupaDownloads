#!/usr/bin/env python3
"""Test the actual driver detection logic."""

import sys
import os

# Add src to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.driver_manager import DriverManager

def test_driver_detection():
    """Test the actual driver detection logic."""
    print("🔍 Testing Actual Driver Detection")
    print("=" * 40)
    
    try:
        # Create driver manager
        driver_manager = DriverManager()
        
        print(f"Project root: {driver_manager.project_root}")
        print(f"Drivers directory: {driver_manager.drivers_dir}")
        print(f"Platform: {driver_manager.platform}")
        
        # Test Edge version detection
        print("\n--- Edge Version Detection ---")
        edge_version = driver_manager.get_edge_version()
        print(f"Edge version: {edge_version}")
        
        if edge_version:
            major = driver_manager._major(edge_version)
            print(f"Major version: {major}")
        
        # Test local driver scanning
        print("\n--- Local Driver Scanning ---")
        candidates = driver_manager._scan_local_drivers()
        print(f"Found {len(candidates)} driver candidates:")
        for candidate in candidates:
            print(f"  - {candidate}")
        
        # Test compatible driver finding
        print("\n--- Compatible Driver Finding ---")
        compatible_driver = driver_manager._find_compatible_local_driver()
        if compatible_driver:
            print(f"✅ Found compatible driver: {compatible_driver}")
        else:
            print("❌ No compatible driver found")
        
        # Test full driver path resolution
        print("\n--- Full Driver Path Resolution ---")
        try:
            driver_path = driver_manager.get_driver_path()
            print(f"✅ Final driver path: {driver_path}")
        except Exception as e:
            print(f"❌ Error getting driver path: {e}")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_driver_detection()
