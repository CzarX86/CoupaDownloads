#!/usr/bin/env python3
"""Quick test to verify driver detection."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.driver_manager import DriverManager

def quick_test():
    print("🔍 Quick Driver Detection Test")
    print("=" * 30)
    
    try:
        dm = DriverManager()
        
        # Test Edge version
        edge_version = dm.get_edge_version()
        print(f"Edge version: {edge_version}")
        
        if edge_version:
            major = dm._major(edge_version)
            print(f"Major version: {major}")
        
        # Test driver candidates
        candidates = dm._scan_local_drivers()
        print(f"Driver candidates: {candidates}")
        
        # Test driver versions
        for candidate in candidates:
            version = dm._get_driver_version(candidate)
            if version:
                major = dm._major(version)
                print(f"Driver {os.path.basename(candidate)}: version={version}, major={major}")
        
        # Test compatibility
        compatible = dm._find_compatible_local_driver()
        print(f"Compatible driver: {compatible}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_test()
