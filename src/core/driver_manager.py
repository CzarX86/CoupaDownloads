"""
EdgeDriver Manager for detection and setup.
Handles version detection and setup for Windows, macOS, and Linux.
User must provide drivers manually.
"""

import os
import platform
import re
import subprocess
import sys
from typing import Optional


class DriverManager:
    """Manages EdgeDriver detection and setup. User must provide drivers manually."""
    
    def __init__(self):
        self.project_root = self._get_project_root()
        self.drivers_dir = os.path.join(self.project_root, "drivers")
        self.platform = self._get_platform()
        
    def _get_project_root(self) -> str:
        """Get the project root directory."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # From src/core/ go up to src/, then to project root
        return os.path.dirname(os.path.dirname(current_dir))
    
    def _get_platform(self) -> str:
        """Get the current platform identifier."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            return "win64"
        elif system == "darwin":  # macOS
            if "arm" in machine or "aarch64" in machine:
                return "mac64_m1"
            else:
                return "mac64"
        elif system == "linux":
            return "linux64"
        else:
            raise OSError(f"Unsupported platform: {system} {machine}")
    
    def get_edge_version(self) -> Optional[str]:
        """Get the installed Edge browser version."""
        try:
            if self.platform == "win64":
                return self._get_edge_version_windows()
            elif self.platform.startswith("mac"):
                return self._get_edge_version_macos()
            elif self.platform == "linux64":
                return self._get_edge_version_linux()
        except Exception as e:
            print(f"⚠️ Warning: Could not detect Edge version: {e}")
            return None
    
    def _get_edge_version_windows(self) -> Optional[str]:
        """Get Edge version on Windows."""
        try:
            # Try PowerShell command first
            cmd = [
                "powershell", 
                "-Command", 
                "(Get-AppxPackage Microsoft.MicrosoftEdge.Stable).Version"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip()
                print(f"🔍 Detected Edge version: {version}")
                return version
            
            # Fallback: try registry
            cmd = [
                "reg", "query", 
                "HKEY_CURRENT_USER\\Software\\Microsoft\\Edge\\BLBeacon", 
                "/v", "version"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                match = re.search(r'version\s+REG_SZ\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
                if match:
                    version = match.group(1)
                    print(f"🔍 Detected Edge version: {version}")
                    return version
                    
        except Exception as e:
            print(f"⚠️ Warning: Could not detect Edge version on Windows: {e}")
        
        return None
    
    def _get_edge_version_macos(self) -> Optional[str]:
        """Get Edge version on macOS."""
        try:
            cmd = ["defaults", "read", "/Applications/Microsoft Edge.app/Contents/Info.plist", "CFBundleShortVersionString"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"🔍 Detected Edge version: {version}")
                return version
                
        except Exception as e:
            print(f"⚠️ Warning: Could not detect Edge version on macOS: {e}")
        
        return None
    
    def _get_edge_version_linux(self) -> Optional[str]:
        """Get Edge version on Linux."""
        try:
            # Try different possible locations
            edge_paths = [
                "/usr/bin/microsoft-edge",
                "/usr/bin/microsoft-edge-stable",
                "/opt/microsoft/msedge/microsoft-edge"
            ]
            
            for edge_path in edge_paths:
                if os.path.exists(edge_path):
                    cmd = [edge_path, "--version"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        # Extract version from output like "Microsoft Edge 120.0.2210.91"
                        match = re.search(r'Microsoft Edge (\d+\.\d+\.\d+\.\d+)', result.stdout)
                        if match:
                            version = match.group(1)
                            print(f"🔍 Detected Edge version: {version}")
                            return version
                            
        except Exception as e:
            print(f"⚠️ Warning: Could not detect Edge version on Linux: {e}")
        
        return None
    

    

    
    def get_driver_path(self) -> str:
        """Get the path to the EdgeDriver. User must provide drivers manually."""
        # Check for existing drivers with different naming patterns
        possible_driver_names = [
            "msedgedriver.exe" if self.platform == "win64" else "msedgedriver",
            "edgedriver",
            "edgedriver_138",
            "edgedriver_137",
            "edgedriver_136"
        ]
        
        for driver_name in possible_driver_names:
            driver_path = os.path.join(self.drivers_dir, driver_name)
            if os.path.exists(driver_path):
                print(f"✅ EdgeDriver found: {driver_path}")
                return driver_path
        
        # Driver doesn't exist - user must provide it manually
        print("❌ EdgeDriver not found in drivers directory.")
        print("📋 Please manually download and place EdgeDriver in the drivers/ directory.")
        print("💡 Download from: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/")
        raise FileNotFoundError("EdgeDriver not found. Please download and place it in the drivers/ directory.")
    
    def verify_driver(self, driver_path: str) -> bool:
        """Verify that the EdgeDriver works correctly."""
        try:
            cmd = [driver_path, "--version"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ EdgeDriver verification successful: {result.stdout.strip()}")
                return True
            else:
                print(f"❌ EdgeDriver verification failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ EdgeDriver verification error: {e}")
            return False 