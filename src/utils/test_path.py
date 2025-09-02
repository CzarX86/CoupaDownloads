#!/usr/bin/env python3
"""Simple path test to verify driver location."""

import os
from pathlib import Path

def test_paths():
    print("🔍 Testing Path Resolution")
    print("=" * 30)
    
    # Method 1: From current file
    current_file = __file__
    print(f"Current file: {current_file}")
    
    # Method 2: From project root
    project_root = Path(__file__).parent.parent.parent
    print(f"Project root: {project_root}")
    
    # Method 3: Drivers directory
    drivers_dir = project_root / "drivers"
    print(f"Drivers directory: {drivers_dir}")
    
    # Check if exists
    if drivers_dir.exists():
        print("✅ Drivers directory exists")
        contents = list(drivers_dir.iterdir())
        print(f"Contents: {[f.name for f in contents]}")
    else:
        print("❌ Drivers directory not found")
        
        # Try alternative paths
        alt_paths = [
            "drivers",
            "../drivers",
            "../../drivers"
        ]
        
        for path in alt_paths:
            if os.path.exists(path):
                print(f"✅ Found at: {path}")
                contents = os.listdir(path)
                print(f"   Contents: {contents}")

if __name__ == "__main__":
    test_paths()
