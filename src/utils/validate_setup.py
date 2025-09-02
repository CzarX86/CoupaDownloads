#!/usr/bin/env python3
"""
Setup validation script for Coupa Downloads automation.
Checks driver compatibility, browser installation, and configuration.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

def check_drivers_directory():
    """Check if drivers directory exists and contains valid drivers."""
    print("🔍 Checking drivers directory...")
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    drivers_dir = project_root / "drivers"
    
    if not drivers_dir.exists():
        print("❌ Drivers directory not found!")
        print(f"   Expected: {drivers_dir}")
        return False
    
    # Check for driver files
    driver_files = list(drivers_dir.glob("msedgedriver*"))
    if not driver_files:
        print("❌ No EdgeDriver files found!")
        print(f"   Expected files: msedgedriver, msedgedriver.exe")
        return False
    
    print(f"✅ Found {len(driver_files)} driver file(s):")
    for driver_file in driver_files:
        print(f"   - {driver_file.name}")
    
    return True

def check_edge_browser():
    """Check if Microsoft Edge is installed and accessible."""
    print("\n🔍 Checking Microsoft Edge installation...")
    
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        edge_path = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        if os.path.exists(edge_path):
            try:
                result = subprocess.run([edge_path, "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    print(f"✅ Edge found: {version}")
                    return True
            except Exception as e:
                print(f"⚠️ Could not get Edge version: {e}")
    elif system == "win32":  # Windows
        try:
            result = subprocess.run(["powershell", "-Command", 
                                   "(Get-AppxPackage Microsoft.MicrosoftEdge.Stable).Version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip()
                print(f"✅ Edge found: {version}")
                return True
        except Exception as e:
            print(f"⚠️ Could not get Edge version: {e}")
    else:  # Linux
        edge_paths = ["/usr/bin/microsoft-edge", "/usr/bin/microsoft-edge-stable"]
        for path in edge_paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run([path, "--version"], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        print(f"✅ Edge found: {version}")
                        return True
                except Exception:
                    continue
    
    print("❌ Microsoft Edge not found or not accessible!")
    return False

def check_python_dependencies():
    """Check if required Python packages are installed."""
    print("\n🔍 Checking Python dependencies...")
    
    required_packages = [
        "selenium",
        "requests", 
        "pandas",
        "openpyxl"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def main():
    """Run all validation checks."""
    print("🚀 Coupa Downloads Setup Validation")
    print("=" * 40)
    
    checks = [
        check_drivers_directory,
        check_edge_browser,
        check_python_dependencies
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
        print()
    
    if all_passed:
        print("✅ All checks passed! Setup is ready.")
        print("💡 Run 'python src/main.py' to start downloading.")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
