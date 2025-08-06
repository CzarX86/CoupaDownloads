"""
Enhanced EdgeDriver Manager for Windows Release
Automatically detects and uses the best available driver.
"""

import os
import platform
import subprocess
import re
from pathlib import Path
from typing import Optional, List


class EnhancedDriverManager:
    """Enhanced driver manager with multiple driver support."""
    
    def __init__(self):
        self.drivers_dir = Path(__file__).parent.parent.parent / "drivers"
        self.available_drivers = self._find_available_drivers()
    
    def _find_available_drivers(self) -> List[Path]:
        """Find all available EdgeDriver executables."""
        drivers = []
        if self.drivers_dir.exists():
            for file in self.drivers_dir.glob("msedgedriver*.exe"):
                drivers.append(file)
        return sorted(drivers, key=lambda x: x.name, reverse=True)
    
    def get_edge_version(self) -> Optional[str]:
        """Get the installed Edge browser version."""
        try:
            # Try PowerShell command
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
                "HKEY_CURRENT_USER\Software\Microsoft\Edge\BLBeacon", 
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
            print(f"⚠️ Warning: Could not detect Edge version: {e}")
        
        return None
    
    def get_best_driver(self) -> Optional[Path]:
        """Get the best available driver for the current Edge version."""
        edge_version = self.get_edge_version()
        
        if not edge_version:
            print("⚠️ Could not detect Edge version, using default driver")
            return self._get_default_driver()
        
        # Extract major version
        major_version = edge_version.split('.')[0]
        
        # Try to find exact version match
        for driver in self.available_drivers:
            if major_version in driver.name:
                print(f"✅ Found matching driver: {driver.name}")
                return driver
        
        # Fallback to default driver
        return self._get_default_driver()
    
    def _get_default_driver(self) -> Optional[Path]:
        """Get the default driver (first available)."""
        if self.available_drivers:
            default = self.available_drivers[0]
            print(f"✅ Using default driver: {default.name}")
            return default
        return None
    
    def verify_driver(self, driver_path: Path) -> bool:
        """Verify that the driver works correctly."""
        try:
            cmd = [str(driver_path), "--version"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ Driver verification successful: {result.stdout.strip()}")
                return True
            else:
                print(f"❌ Driver verification failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Driver verification error: {e}")
            return False
    
    def get_driver_path(self) -> str:
        """Get the path to the best available driver."""
        driver = self.get_best_driver()
        
        if not driver:
            raise RuntimeError("No EdgeDriver found. Please run download_drivers.bat first.")
        
        if not self.verify_driver(driver):
            raise RuntimeError(f"EdgeDriver verification failed: {driver}")
        
        return str(driver)
    
    def list_available_drivers(self) -> List[str]:
        """List all available drivers."""
        return [str(driver) for driver in self.available_drivers]
    
    def download_drivers_if_needed(self):
        """Download drivers if none are available."""
        if not self.available_drivers:
            print("⚠️ No drivers found. Please run download_drivers.bat first.")
            return False
        return True
