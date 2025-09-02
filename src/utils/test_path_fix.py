#!/usr/bin/env python3
"""
Test to verify and fix the driver directory path issue.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.driver_manager import DriverManager

def test_paths():
    """Test the current path resolution."""
    print("🔍 Testing Path Resolution")
    print("=" * 40)
    
    driver_manager = DriverManager()
    
    print(f"Current file: {__file__}")
    print(f"Project root: {driver_manager.project_root}")
    print(f"Drivers directory: {driver_manager.drivers_dir}")
    
    # Check if the paths are correct
    expected_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    expected_drivers_dir = os.path.join(expected_project_root, "drivers")
    
    print(f"\nExpected project root: {expected_project_root}")
    print(f"Expected drivers directory: {expected_drivers_dir}")
    
    print(f"\nCurrent vs Expected:")
    print(f"Project root: {'✅' if driver_manager.project_root == expected_project_root else '❌'}")
    print(f"Drivers directory: {'✅' if driver_manager.drivers_dir == expected_drivers_dir else '❌'}")
    
    # Check if directories exist
    print(f"\nDirectory existence:")
    print(f"Current drivers dir exists: {'✅' if os.path.exists(driver_manager.drivers_dir) else '❌'}")
    print(f"Expected drivers dir exists: {'✅' if os.path.exists(expected_drivers_dir) else '❌'}")
    
    # List contents of both directories
    print(f"\nCurrent drivers directory contents:")
    if os.path.exists(driver_manager.drivers_dir):
        for item in os.listdir(driver_manager.drivers_dir):
            print(f"  - {item}")
    else:
        print("  (Directory does not exist)")
    
    print(f"\nExpected drivers directory contents:")
    if os.path.exists(expected_drivers_dir):
        for item in os.listdir(expected_drivers_dir):
            print(f"  - {item}")
    else:
        print("  (Directory does not exist)")

def fix_driver_manager_paths():
    """Show the fix for the path issue."""
    print("\n🔧 Path Fix Solution")
    print("=" * 30)
    
    print("The issue is in the _get_project_root() method.")
    print("Current implementation:")
    print("  return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))")
    print("  # From src/core/ goes up to src/, then to project root")
    
    print("\nThis should be:")
    print("  return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))")
    print("  # From src/core/ goes up to src/, then to project root, then to workspace root")
    
    # Demonstrate the fix
    current_file = os.path.abspath(__file__)
    print(f"\nCurrent file: {current_file}")
    
    # Current (wrong) path
    current_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"Current project root: {current_project_root}")
    
    # Fixed (correct) path
    fixed_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f"Fixed project root: {fixed_project_root}")
    
    print(f"\nThe fix is to add one more os.path.dirname() call")

if __name__ == "__main__":
    test_paths()
    fix_driver_manager_paths()
