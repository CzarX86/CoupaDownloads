#!/usr/bin/env python3
"""
Debug script to diagnose driver detection issues.
Run this to understand why drivers aren't being found.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

def debug_path_resolution():
    """Debug the path resolution logic used by DriverManager."""
    print("🔍 Debugging Path Resolution")
    print("=" * 40)
    
    # Simulate DriverManager path resolution
    current_file = __file__
    print(f"Current file: {current_file}")
    
    # From src/utils/ to src/core/ (simulate driver_manager.py location)
    core_dir = os.path.dirname(os.path.dirname(current_file)) + "/core"
    print(f"Core directory: {core_dir}")
    
    # From src/core/ to project root
    project_root = os.path.dirname(os.path.dirname(core_dir))
    print(f"Project root: {project_root}")
    
    # Drivers directory
    drivers_dir = os.path.join(project_root, "drivers")
    print(f"Drivers directory: {drivers_dir}")
    
    # Check if drivers directory exists
    if os.path.exists(drivers_dir):
        print("✅ Drivers directory exists")
        
        # List contents
        try:
            contents = os.listdir(drivers_dir)
            print(f"Contents: {contents}")
            
            # Check for msedgedriver files
            msedgedriver_files = [f for f in contents if f.lower().startswith('msedgedriver')]
            print(f"msedgedriver files: {msedgedriver_files}")
            
        except Exception as e:
            print(f"❌ Error listing drivers directory: {e}")
    else:
        print("❌ Drivers directory does not exist!")
        
        # Check if we're in the right location
        current_dir = os.getcwd()
        print(f"Current working directory: {current_dir}")
        
        # Try to find drivers directory from current location
        possible_paths = [
            "drivers",
            "../drivers", 
            "../../drivers",
            "src/drivers",
            "../src/drivers"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ Found drivers at: {path}")
                try:
                    contents = os.listdir(path)
                    print(f"   Contents: {contents}")
                except Exception as e:
                    print(f"   Error listing: {e}")

def debug_platform_detection():
    """Debug platform detection logic."""
    print("\n🔍 Debugging Platform Detection")
    print("=" * 40)
    
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    print(f"System: {system}")
    print(f"Machine: {machine}")
    
    # Simulate DriverManager platform detection
    if system == "windows":
        platform_id = "win64"
    elif system == "darwin":  # macOS
        platform_id = "mac64_m1" if "arm" in machine or "aarch64" in machine else "mac64"
    elif system == "linux":
        platform_id = "linux64"
    else:
        platform_id = "unknown"
    
    print(f"Platform ID: {platform_id}")
    
    # Check which driver file should be used
    if platform_id == "win64":
        expected_driver = "msedgedriver.exe"
    else:
        expected_driver = "msedgedriver"
    
    print(f"Expected driver file: {expected_driver}")

def debug_edge_version_detection():
    """Debug Edge browser version detection."""
    print("\n🔍 Debugging Edge Version Detection")
    print("=" * 40)
    
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        edge_path = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        if os.path.exists(edge_path):
            try:
                result = subprocess.run([edge_path, "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    print(f"✅ Edge version: {version}")
                    
                    # Extract major version
                    major_version = version.split('.')[0] if '.' in version else "unknown"
                    print(f"Major version: {major_version}")
                    return major_version
                else:
                    print(f"❌ Edge version command failed: {result.stderr}")
            except Exception as e:
                print(f"❌ Error getting Edge version: {e}")
        else:
            print("❌ Edge not found at expected path")
    elif system == "win32":  # Windows
        try:
            result = subprocess.run(["powershell", "-Command", 
                                   "(Get-AppxPackage Microsoft.MicrosoftEdge.Stable).Version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip()
                print(f"✅ Edge version: {version}")
                
                # Extract major version
                major_version = version.split('.')[0] if '.' in version else "unknown"
                print(f"Major version: {major_version}")
                return major_version
            else:
                print("❌ Edge version command failed")
        except Exception as e:
            print(f"❌ Error getting Edge version: {e}")
    else:  # Linux
        edge_paths = ["/usr/bin/microsoft-edge", "/usr/bin/microsoft-edge-stable"]
        for path in edge_paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run([path, "--version"], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        print(f"✅ Edge version: {version}")
                        
                        # Extract major version
                        major_version = version.split('.')[0] if '.' in version else "unknown"
                        print(f"Major version: {major_version}")
                        return major_version
                except Exception:
                    continue
    
    print("❌ Could not detect Edge version")
    return None

def debug_driver_execution():
    """Debug driver execution and version detection."""
    print("\n🔍 Debugging Driver Execution")
    print("=" * 40)
    
    # Find drivers directory
    project_root = Path(__file__).parent.parent.parent
    drivers_dir = project_root / "drivers"
    
    if not drivers_dir.exists():
        print("❌ Drivers directory not found")
        return
    
    # Find driver files
    driver_files = list(drivers_dir.glob("msedgedriver*"))
    if not driver_files:
        print("❌ No driver files found")
        return
    
    print(f"Found {len(driver_files)} driver file(s):")
    
    for driver_file in driver_files:
        print(f"\n--- Testing {driver_file.name} ---")
        
        # Check file permissions
        try:
            stat = os.stat(driver_file)
            print(f"File permissions: {oct(stat.st_mode)}")
            
            # Check if executable
            is_executable = os.access(driver_file, os.X_OK)
            print(f"Executable: {is_executable}")
            
            if not is_executable:
                print("⚠️ File is not executable, trying to make it executable...")
                try:
                    os.chmod(driver_file, stat.st_mode | 0o111)
                    print("✅ Made file executable")
                except Exception as e:
                    print(f"❌ Could not make file executable: {e}")
            
        except Exception as e:
            print(f"❌ Error checking file permissions: {e}")
        
        # Try to execute driver
        try:
            print("Testing driver execution...")
            result = subprocess.run([str(driver_file), "--version"], 
                                  capture_output=True, text=True, timeout=10)
            
            print(f"Return code: {result.returncode}")
            print(f"Stdout: {result.stdout.strip()}")
            print(f"Stderr: {result.stderr.strip()}")
            
            if result.returncode == 0:
                # Parse version
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                if version_match:
                    version = version_match.group(1)
                    print(f"✅ Driver version: {version}")
                else:
                    print("⚠️ Could not parse driver version")
            else:
                print("❌ Driver execution failed")
                
        except Exception as e:
            print(f"❌ Error executing driver: {e}")

def debug_architecture_compatibility():
    """Debug architecture compatibility checks."""
    print("\n🔍 Debugging Architecture Compatibility")
    print("=" * 40)
    
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    print(f"System: {system}")
    print(f"Machine: {machine}")
    
    # Find drivers directory
    project_root = Path(__file__).parent.parent.parent
    drivers_dir = project_root / "drivers"
    
    if not drivers_dir.exists():
        print("❌ Drivers directory not found")
        return
    
    # Find driver files
    driver_files = list(drivers_dir.glob("msedgedriver*"))
    if not driver_files:
        print("❌ No driver files found")
        return
    
    for driver_file in driver_files:
        print(f"\n--- Checking {driver_file.name} ---")
        
        if system == "darwin":  # macOS
            want = "arm64" if ("arm" in machine or "aarch64" in machine) else "x86_64"
            print(f"Expected architecture: {want}")
            
            # Try lipo first
            try:
                result = subprocess.run(["lipo", "-info", str(driver_file)], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"Lipo output: {result.stdout.strip()}")
                    if want in result.stdout.lower():
                        print("✅ Architecture matches (lipo)")
                    else:
                        print("❌ Architecture mismatch (lipo)")
                else:
                    print("⚠️ Lipo failed, trying file command...")
            except Exception as e:
                print(f"⚠️ Lipo not available: {e}")
            
            # Try file command
            try:
                result = subprocess.run(["file", "-b", str(driver_file)], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"File output: {result.stdout.strip()}")
                    if want == "arm64":
                        if "arm64" in result.stdout.lower() or "aarch64" in result.stdout.lower():
                            print("✅ Architecture matches (file)")
                        else:
                            print("❌ Architecture mismatch (file)")
                    else:
                        if "x86_64" in result.stdout.lower() or "intel" in result.stdout.lower():
                            print("✅ Architecture matches (file)")
                        else:
                            print("❌ Architecture mismatch (file)")
                else:
                    print("❌ File command failed")
            except Exception as e:
                print(f"❌ File command error: {e}")
        
        elif system == "linux":
            try:
                result = subprocess.run(["file", "-b", str(driver_file)], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"File output: {result.stdout.strip()}")
                    
                    if "x86_64" in machine or "amd64" in machine:
                        if "x86-64" in result.stdout.lower() or "x86_64" in result.stdout.lower():
                            print("✅ Architecture matches")
                        else:
                            print("❌ Architecture mismatch")
                    elif "aarch64" in machine or "arm64" in machine:
                        if "aarch64" in result.stdout.lower() or "arm64" in result.stdout.lower():
                            print("✅ Architecture matches")
                        else:
                            print("❌ Architecture mismatch")
                else:
                    print("❌ File command failed")
            except Exception as e:
                print(f"❌ File command error: {e}")
        
        else:  # Windows
            print("✅ Windows - architecture check not needed")

def main():
    """Run all debug checks."""
    print("🚀 Driver Detection Debug Tool")
    print("=" * 50)
    
    debug_path_resolution()
    debug_platform_detection()
    debug_edge_version_detection()
    debug_driver_execution()
    debug_architecture_compatibility()
    
    print("\n" + "=" * 50)
    print("🔍 Debug Complete")
    print("\n💡 Next steps:")
    print("1. Check the output above for any ❌ errors")
    print("2. Ensure driver files are executable")
    print("3. Verify Edge browser is installed and accessible")
    print("4. Check if architecture matches your system")

if __name__ == "__main__":
    main()
