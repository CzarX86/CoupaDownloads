"""
Simplified EdgeDriver Manager for parallel testing.
"""

import os
import platform
import subprocess
from typing import Optional

class DriverManager:
    """
    Simplified driver manager for parallel testing.
    """
    
    def __init__(self):
        self.project_root = self._get_project_root()
        self.drivers_dir = os.path.join(self.project_root, "drivers")
        self.platform = self._get_platform()
        
    def _get_project_root(self) -> str:
        """Get the project root directory."""
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    def _get_platform(self) -> str:
        """Get the current platform identifier."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            return "win64"
        elif system == "darwin":  # macOS
            return "mac64_m1" if "arm" in machine or "aarch64" in machine else "mac64"
        elif system == "linux":
            return "linux64"
        else:
            raise OSError(f"Unsupported platform: {system} {machine}")

    def get_driver_path(self) -> str:
        """
        Get the path to the EdgeDriver.
        """
        # Look for local driver
        if self.platform == "win64":
            driver_path = "drivers/msedgedriver.exe"
        else:
            driver_path = "drivers/msedgedriver"
        
        if os.path.exists(driver_path):
            print(f"✅ Using local driver: {driver_path}")
            return driver_path
        else:
            raise FileNotFoundError(f"EdgeDriver not found at {driver_path}")

    def verify_driver(self, driver_path: str) -> bool:
        """Verify that the driver is executable."""
        try:
            if not os.path.exists(driver_path):
                return False
            
            # Check if file is executable
            if not os.access(driver_path, os.X_OK):
                os.chmod(driver_path, 0o755)
            
            # Try to get version
            result = subprocess.run([driver_path, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            print(f"⚠️ Driver verification failed: {e}")
            return False
