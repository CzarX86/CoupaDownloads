"""
EdgeDriver Manager for automatic download and installation.
Handles version detection, download, and setup for Windows, macOS, and Linux.
"""

import os
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Optional, Tuple
import requests
import json


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
    
    def get_compatible_driver_version(self, edge_version: str) -> str:
        """Get the compatible EdgeDriver version for the given Edge version."""
        try:
            # Extract major version from Edge version (e.g., "120.0.2210.91" -> "120")
            major_version = edge_version.split('.')[0]
            
            # Get the latest driver version for this major version
            url = f"{self.EDGEDRIVER_BASE_URL}/{major_version}/LATEST_STABLE"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            driver_version = response.text.strip()
            print(f"🔧 Compatible EdgeDriver version: {driver_version}")
            return driver_version
            
        except Exception as e:
            print(f"⚠️ Warning: Could not get compatible driver version: {e}")
            # Fallback to latest stable
            return "LATEST_STABLE"
    
    def get_driver_filename(self, driver_version: str) -> str:
        """Get the driver filename for the current platform."""
        if self.platform == "win64":
            return f"edgedriver_win64_{driver_version}.zip"
        elif self.platform.startswith("mac"):
            return f"edgedriver_mac64_{driver_version}.zip"
        elif self.platform == "linux64":
            return f"edgedriver_linux64_{driver_version}.zip"
        else:
            raise OSError(f"Unsupported platform: {self.platform}")
    
    def download_driver(self, driver_version: str) -> str:
        """Download the EdgeDriver for the specified version."""
        filename = self.get_driver_filename(driver_version)
        download_url = f"{self.EDGEDRIVER_BASE_URL}/{driver_version}/{filename}"
        local_path = os.path.join(self.drivers_dir, filename)
        
        print(f"📥 Downloading EdgeDriver from: {download_url}")
        
        try:
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Create drivers directory if it doesn't exist
            os.makedirs(self.drivers_dir, exist_ok=True)
            
            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r📥 Download progress: {progress:.1f}%", end='', flush=True)
            
            print(f"\n✅ EdgeDriver downloaded successfully: {local_path}")
            return local_path
            
        except Exception as e:
            print(f"\n❌ Failed to download EdgeDriver: {e}")
            raise
    
    def extract_driver(self, zip_path: str) -> str:
        """Extract the EdgeDriver from the zip file."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the driver executable name
                driver_name = "msedgedriver.exe" if self.platform == "win64" else "msedgedriver"
                
                # Extract the driver
                zip_ref.extract(driver_name, self.drivers_dir)
                
                driver_path = os.path.join(self.drivers_dir, driver_name)
                
                # Make executable on Unix systems
                if self.platform != "win64":
                    os.chmod(driver_path, 0o755)
                
                print(f"✅ EdgeDriver extracted: {driver_path}")
                return driver_path
                
        except Exception as e:
            print(f"❌ Failed to extract EdgeDriver: {e}")
            raise
    
    def get_driver_path(self) -> str:
        """Get the path to the EdgeDriver, downloading if necessary."""
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
        
        # Driver doesn't exist, download it
        print("🔍 EdgeDriver not found. Starting automatic download...")
        
        # Get Edge version
        edge_version = self.get_edge_version()
        if not edge_version:
            print("⚠️ Could not detect Edge version. Using latest stable driver.")
            driver_version = "LATEST_STABLE"
        else:
            # Get compatible driver version
            driver_version = self.get_compatible_driver_version(edge_version)
        
        # Download and extract driver
        zip_path = self.download_driver(driver_version)
        driver_path = self.extract_driver(zip_path)
        
        # Clean up zip file
        try:
            os.remove(zip_path)
            print(f"🧹 Cleaned up: {zip_path}")
        except Exception as e:
            print(f"⚠️ Warning: Could not remove zip file: {e}")
        
        return driver_path
    
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