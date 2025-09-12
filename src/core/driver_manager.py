"""
Hybrid EdgeDriver Manager for automatic download and installation.
Prioritizes using a local driver if a compatible one is found,
otherwise falls back to automatic download and installation.
Handles version detection, download, and setup for Windows, macOS, and Linux.
"""

import os
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Optional, List
import requests


class DriverManager:
    """
    Manages EdgeDriver, prioritizing local drivers and falling back to web download.
    """
    
    # EdgeDriver download URLs
    EDGEDRIVER_BASE_URL = "https://msedgedriver.microsoft.com"
    
    def __init__(self):
        self.project_root = self._get_project_root()
        self.drivers_dir = os.path.join(self.project_root, "drivers")
        self.platform = self._get_platform()
        
    def _get_project_root(self) -> str:
        """Get the project root directory."""
        # FIXED: From src/core/ go up to src/, then to project root, then to workspace root
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
        1. Looks for a compatible local driver.
        2. If not found, downloads a compatible driver from the web.
        """
        # 0. Respect explicit env override first
        env_path = os.environ.get("EDGE_DRIVER_PATH")
        if env_path:
            env_path = os.path.expanduser(env_path)
            if os.path.exists(env_path) and self.verify_driver(env_path):
                print(f"✅ Using driver from EDGE_DRIVER_PATH: {env_path}")
                return env_path
            else:
                print("⚠️ EDGE_DRIVER_PATH provided but invalid; ignoring.")

        # 1. Try to find a suitable local driver first
        print("🔎 Searching for a compatible local EdgeDriver...")
        local_driver_path = self._find_compatible_local_driver()
        if local_driver_path and self.verify_driver(local_driver_path):
            print(f"✅ Using compatible local driver: {local_driver_path}")
            return local_driver_path

        # 2. If no local driver, fall back to web download
        if os.environ.get("DRIVER_AUTO_DOWNLOAD", "true").lower() != "true":
            raise RuntimeError(
                "No compatible local EdgeDriver found and DRIVER_AUTO_DOWNLOAD is disabled. "
                "Please provision a compatible driver and set EDGE_DRIVER_PATH or place it under 'drivers/'."
            )
        print("ℹ️ No compatible local driver found. Starting automatic download...")
        
        edge_version = self.get_edge_version()
        if not edge_version:
            print("⚠️ Could not detect Edge version. Attempting to use latest stable driver.")
            driver_version = "LATEST_STABLE"
        else:
            driver_version = self.get_compatible_driver_version(edge_version)
        
        zip_path = self.download_driver(driver_version)
        driver_path = self.extract_driver(zip_path)
        
        # Clean up the downloaded zip file
        try:
            os.remove(zip_path)
            print(f"🧹 Cleaned up: {zip_path}")
        except Exception as e:
            print(f"⚠️ Warning: Could not remove zip file: {e}")
        
        if not self.verify_driver(driver_path):
            raise RuntimeError("Downloaded EdgeDriver failed verification.")
            
        return driver_path

    def _find_compatible_local_driver(self) -> Optional[str]:
        """Find a compatible local driver by executing candidates with --version.

        - Filters by OS/architecture implicitly: only drivers that execute successfully are considered.
        - Chooses a driver whose major version matches the installed Edge major version.
        - If multiple match, picks the highest full version.
        """
        edge_version = self.get_edge_version()
        if not edge_version:
            print("⚠️ Could not detect Edge version to match with local drivers.")
            return None

        edge_major = self._major(edge_version)

        candidates = self._scan_local_drivers()
        if not candidates:
            print("ℹ️ No local drivers found in the 'drivers' directory.")
            return None

        compatible: list[tuple[tuple[int, int, int, int], str]] = []
        for path in candidates:
            # Ensure the binary is runnable on this system (permissions + quarantine)
            self._prepare_driver_candidate(path)

            # Filter out binaries that are the wrong architecture/format for this OS
            if not self._is_compatible_arch(path):
                print(f"⚠️ Skipping driver due to incompatible architecture: {os.path.basename(path)}")
                continue

            drv_version = self._get_driver_version(path)
            if not drv_version:
                continue  # not executable here or unknown format (likely wrong OS/arch)
            if self._major(drv_version) == edge_major:
                compatible.append((self._version_tuple(drv_version), path))

        if compatible:
            # pick the highest full version among compatibles
            compatible.sort(reverse=True)
            best_version, best_path = compatible[0]
            print(f"✅ Found matching local driver (v{self._format_version(best_version)}): {os.path.basename(best_path)}")
            return best_path

        print(f"ℹ️ No local driver with matching major version v{edge_major}.")
        return None

    def _scan_local_drivers(self) -> List[str]:
        """Scan the 'drivers' directory for EdgeDriver candidates by name.

        Returns a list of file paths for items that look like msedgedriver binaries.
        Actual OS compatibility is validated later by executing with --version.
        """
        drivers: List[str] = []
        if not os.path.exists(self.drivers_dir):
            return drivers

        base = "msedgedriver"
        for item in os.listdir(self.drivers_dir):
            lower = item.lower()
            if not lower.startswith(base):
                continue
            full_path = os.path.join(self.drivers_dir, item)
            if os.path.isfile(full_path):
                drivers.append(full_path)

        return sorted(drivers, reverse=True)

    def _get_driver_version(self, driver_path: str) -> Optional[str]:
        """Return the driver version by invoking '<driver> --version'.

        On success, returns a string like '120.0.2210.61'. On failure, returns None.
        """
        try:
            result = subprocess.run([driver_path, "--version"], capture_output=True, text=True, timeout=8)
            if result.returncode != 0:
                return None
            # Expect output like: 'MSEdgeDriver 120.0.2210.61 (hash)'
            m = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
            return m.group(1) if m else None
        except Exception:
            return None

    def _version_tuple(self, v: str) -> tuple[int, int, int, int]:
        parts = (v.split(".") + ["0", "0", "0", "0"])[:4]
        return tuple(int(p) for p in parts)  # type: ignore[return-value]

    def _major(self, v: str) -> int:
        try:
            return int(v.split(".")[0])
        except Exception:
            return -1

    def _format_version(self, t: tuple[int, int, int, int]) -> str:
        return ".".join(str(x) for x in t)

    def _prepare_driver_candidate(self, driver_path: str) -> None:
        """Make the binary executable and remove macOS Gatekeeper quarantine if present."""
        try:
            if self.platform != "win64":
                # Ensure executable bit
                try:
                    st = os.stat(driver_path)
                    os.chmod(driver_path, st.st_mode | 0o111)
                except Exception:
                    pass
                # Remove quarantine on macOS
                if self._is_macos():
                    try:
                        subprocess.run(["xattr", "-dr", "com.apple.quarantine", driver_path],
                                       capture_output=True, check=False)
                    except Exception:
                        pass
        except Exception:
            # Non-fatal preparation issues are ignored; execution checks will follow
            pass

    def _is_macos(self) -> bool:
        return self._get_platform().startswith("mac") or platform.system().lower() == "darwin"

    def _is_compatible_arch(self, driver_path: str) -> bool:
        """Best-effort check that the driver binary matches current architecture.

        - macOS: uses `lipo -info` or `file` to check for arm64/x86_64 slice.
        - Linux: uses `file` to check for x86-64/aarch64.
        - Windows: returns True (we rely on execution test afterwards).
        If tools are unavailable or detection fails, default to True.
        """
        system = platform.system().lower()
        machine = platform.machine().lower()

        try:
            if system == "windows":
                return True

            if system == "darwin":
                want = "arm64" if ("arm" in machine or "aarch64" in machine) else "x86_64"
                # Try lipo first
                try:
                    res = subprocess.run(["lipo", "-info", driver_path], capture_output=True, text=True, timeout=5)
                    if res.returncode == 0:
                        out = res.stdout.lower()
                        return want in out
                except Exception:
                    pass
                # Fallback to file
                try:
                    res = subprocess.run(["file", "-b", driver_path], capture_output=True, text=True, timeout=5)
                    if res.returncode == 0:
                        out = res.stdout.lower()
                        if want == "arm64":
                            return ("arm64" in out) or ("aarch64" in out)
                        else:
                            return "x86_64" in out or "x86-64" in out or "intel" in out
                except Exception:
                    pass
                # If we cannot determine, allow and let execution decide
                return True

            if system == "linux":
                try:
                    res = subprocess.run(["file", "-b", driver_path], capture_output=True, text=True, timeout=5)
                    if res.returncode == 0:
                        out = res.stdout.lower()
                        if "x86_64" in machine or "amd64" in machine:
                            return "x86-64" in out or "x86_64" in out
                        if "aarch64" in machine or "arm64" in machine:
                            return "aarch64" in out or "arm64" in out
                        # Unknown arch; allow and let execution decide
                        return True
                except Exception:
                    pass
                return True

        except Exception:
            return True
        return True

    def get_edge_version(self) -> Optional[str]:
        """Get the installed Edge browser version for the current platform."""
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
        """Get Edge version on Windows using PowerShell or registry."""
        try:
            cmd = [
                "powershell", "-Command",
                "(Get-AppxPackage Microsoft.MicrosoftEdge.Stable).Version"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

            cmd = [
                "reg", "query", r"HKEY_CURRENT_USER\Software\Microsoft\Edge\BLBeacon", "/v", "version"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode == 0:
                match = re.search(r'version\s+REG_SZ\s+([0-9.]+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception:
            pass  # Suppress errors if detection fails
        return None
    
    def _get_edge_version_macos(self) -> Optional[str]:
        """Get Edge version on macOS."""
        try:
            cmd = ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "--version"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode == 0 and result.stdout.strip():
                match = re.search(r'Microsoft Edge\s+([0-9.]+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return None
    
    def _get_edge_version_linux(self) -> Optional[str]:
        """Get Edge version on Linux."""
        for path in ["/usr/bin/microsoft-edge", "/usr/bin/microsoft-edge-stable", "/opt/microsoft/msedge/microsoft-edge"]:
            if os.path.exists(path):
                try:
                    cmd = [path, "--version"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
                    if result.returncode == 0:
                        match = re.search(r'Microsoft Edge\s+([0-9.]+)', result.stdout)
                        if match:
                            return match.group(1)
                except Exception:
                    continue
        return None
    
    def get_compatible_driver_version(self, edge_version: str) -> str:
        """Get the compatible EdgeDriver version from the web."""
        major_version = edge_version.split('.')[0]
        url = f"{self.EDGEDRIVER_BASE_URL}/LATEST_RELEASE_{major_version}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # FIXED: Response is plain text, not XML
            driver_version = response.text.strip()
            
            if driver_version and re.match(r'^\d+\.\d+\.\d+\.\d+$', driver_version):
                print(f"🔧 Found compatible driver version online: {driver_version}")
                return driver_version
            else:
                 raise ValueError("Could not parse driver version from response.")
        except Exception as e:
            print(f"⚠️ Warning: Could not get compatible driver version: {e}. Falling back to latest stable.")
            return "LATEST_STABLE"
    
    def download_driver(self, driver_version: str) -> str:
        """Download the EdgeDriver for the specified version."""
        zip_name = f"edgedriver_{self.platform}.zip"
        # The URL structure changed for newer drivers
        download_url = f"{self.EDGEDRIVER_BASE_URL}/{driver_version}/{zip_name}"
        local_path = os.path.join(self.drivers_dir, f"edgedriver_{self.platform}_{driver_version}.zip")
        
        print(f"📥 Downloading EdgeDriver from: {download_url}")
        os.makedirs(self.drivers_dir, exist_ok=True)
        
        try:
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            with open(local_path, 'wb') as f:
                downloaded = 0
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
        driver_name = "msedgedriver.exe" if self.platform == "win64" else "msedgedriver"
        extract_dir = Path(zip_path).parent
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Look for the driver inside a potential sub-directory in the zip
                zip_infos = zip_ref.infolist()
                driver_entry = next((info for info in zip_infos if driver_name in Path(info.filename).name), None)
                
                if not driver_entry:
                    raise FileNotFoundError(f"'{driver_name}' not found in the zip file.")

                # Extract to a specific file path to handle nested directories
                driver_path = extract_dir / driver_name
                with zip_ref.open(driver_entry) as source, open(driver_path, 'wb') as target:
                    target.write(source.read())

                if self.platform != "win64":
                    os.chmod(driver_path, 0o755)
                
                print(f"✅ EdgeDriver extracted to: {driver_path}")
                return str(driver_path)
                
        except Exception as e:
            print(f"❌ Failed to extract EdgeDriver: {e}")
            raise
    
    def verify_driver(self, driver_path: str) -> bool:
        """Verify that the EdgeDriver works correctly."""
        if not os.path.exists(driver_path):
            print(f"❌ Verification failed: Driver not found at {driver_path}")
            return False
        try:
            # Prepare binary (permissions/quarantine) before verifying
            self._prepare_driver_candidate(driver_path)
            cmd = [driver_path, "--version"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and "Edge" in result.stdout:
                print(f"✅ EdgeDriver verification successful: {result.stdout.strip()}")
                return True
            else:
                print(f"❌ EdgeDriver verification failed. stderr: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"❌ EdgeDriver verification error: {e}")
            return False
