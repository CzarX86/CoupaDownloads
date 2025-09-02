#!/usr/bin/env python3
"""
Comprehensive test for web download functionality.
This test isolates and tests the web download capabilities without affecting the overall module.
Mimics driver_manager methods but focuses on web download testing.
"""

import sys
import os
import platform
import re
import subprocess
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List
import requests

# Add src to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class WebDownloadTester:
    """
    Test class that mimics driver_manager methods for web download testing.
    Focuses on isolating and testing web download functionality.
    """
    
    # EdgeDriver download URLs
    EDGEDRIVER_BASE_URL = "https://msedgedriver.microsoft.com"
    
    def __init__(self, test_dir: Optional[str] = None):
        self.project_root = self._get_project_root()
        self.test_dir = test_dir or os.path.join(self.project_root, "test_downloads")
        self.platform = self._get_platform()
        self.test_results = []
        
        # Ensure test directory exists
        os.makedirs(self.test_dir, exist_ok=True)
        
    def _get_project_root(self) -> str:
        """Get the project root directory."""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
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

    def log_test_result(self, test_name: str, success: bool, message: str, details: Optional[dict] = None):
        """Log test results for reporting."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")

    def test_platform_detection(self):
        """Test platform detection functionality."""
        print("\n🔍 Testing Platform Detection")
        print("=" * 40)
        
        try:
            platform_info = {
                "system": platform.system(),
                "machine": platform.machine(),
                "detected_platform": self.platform
            }
            
            self.log_test_result(
                "Platform Detection",
                True,
                f"Detected platform: {self.platform}",
                platform_info
            )
            
            print(f"System: {platform.system()}")
            print(f"Machine: {platform.machine()}")
            print(f"Detected Platform: {self.platform}")
            
        except Exception as e:
            self.log_test_result(
                "Platform Detection",
                False,
                f"Failed to detect platform: {e}"
            )

    def test_edge_version_detection(self):
        """Test Edge version detection functionality."""
        print("\n🔍 Testing Edge Version Detection")
        print("=" * 40)
        
        try:
            edge_version = self.get_edge_version()
            
            if edge_version:
                major_version = self._major(edge_version)
                self.log_test_result(
                    "Edge Version Detection",
                    True,
                    f"Detected Edge version: {edge_version} (major: {major_version})",
                    {"version": edge_version, "major": major_version}
                )
                print(f"Edge version: {edge_version}")
                print(f"Major version: {major_version}")
            else:
                self.log_test_result(
                    "Edge Version Detection",
                    False,
                    "Could not detect Edge version"
                )
                print("⚠️ Could not detect Edge version")
                
        except Exception as e:
            self.log_test_result(
                "Edge Version Detection",
                False,
                f"Error detecting Edge version: {e}"
            )

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
            pass
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

    def _major(self, v: str) -> int:
        """Extract major version number."""
        try:
            return int(v.split(".")[0])
        except Exception:
            return -1

    def test_compatible_driver_version_detection(self):
        """Test compatible driver version detection from web."""
        print("\n�� Testing Compatible Driver Version Detection")
        print("=" * 50)
        
        try:
            edge_version = self.get_edge_version()
            if not edge_version:
                self.log_test_result(
                    "Compatible Driver Version Detection",
                    False,
                    "Cannot test without Edge version"
                )
                return
            
            driver_version = self.get_compatible_driver_version(edge_version)
            
            self.log_test_result(
                "Compatible Driver Version Detection",
                True,
                f"Found compatible driver version: {driver_version}",
                {"edge_version": edge_version, "driver_version": driver_version}
            )
            
            print(f"Edge version: {edge_version}")
            print(f"Compatible driver version: {driver_version}")
            
        except Exception as e:
            self.log_test_result(
                "Compatible Driver Version Detection",
                False,
                f"Error detecting compatible driver version: {e}"
            )

    def get_compatible_driver_version(self, edge_version: str) -> str:
        """Get the compatible EdgeDriver version from the web."""
        major_version = edge_version.split('.')[0]
        url = f"{self.EDGEDRIVER_BASE_URL}/LATEST_RELEASE_{major_version}_stable"
        
        try:
            print(f"🔗 Fetching from: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # The response is XML, we need to parse it to find the version
            content = response.text
            print(f"📄 Response content: {content[:200]}...")
            
            version_match = re.search(r'<Name>([0-9.]+)/</Name>', content)
            if version_match:
                driver_version = version_match.group(1)
                print(f"🔧 Found compatible driver version online: {driver_version}")
                return driver_version
            else:
                raise ValueError("Could not parse driver version from response.")
        except Exception as e:
            print(f"⚠️ Warning: Could not get compatible driver version: {e}. Falling back to latest stable.")
            return "LATEST_STABLE"

    def test_driver_download(self):
        """Test driver download functionality."""
        print("\n🔍 Testing Driver Download")
        print("=" * 30)
        
        try:
            # Test with a known version first
            test_version = "120.0.2210.61"  # Use a recent stable version
            
            zip_path = self.download_driver(test_version)
            
            if os.path.exists(zip_path):
                file_size = os.path.getsize(zip_path)
                self.log_test_result(
                    "Driver Download",
                    True,
                    f"Successfully downloaded driver: {zip_path} ({file_size} bytes)",
                    {"zip_path": zip_path, "file_size": file_size, "version": test_version}
                )
                print(f"✅ Downloaded: {zip_path}")
                print(f"📁 File size: {file_size} bytes")
                
                # Clean up test file
                try:
                    os.remove(zip_path)
                    print(f"🧹 Cleaned up test file: {zip_path}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not remove test file: {e}")
            else:
                self.log_test_result(
                    "Driver Download",
                    False,
                    f"Download file not found: {zip_path}"
                )
                
        except Exception as e:
            self.log_test_result(
                "Driver Download",
                False,
                f"Error downloading driver: {e}"
            )

    def download_driver(self, driver_version: str) -> str:
        """Download the EdgeDriver for the specified version."""
        zip_name = f"edgedriver_{self.platform}.zip"
        download_url = f"{self.EDGEDRIVER_BASE_URL}/{driver_version}/{zip_name}"
        local_path = os.path.join(self.test_dir, f"edgedriver_{self.platform}_{driver_version}.zip")
        
        print(f"📥 Downloading EdgeDriver from: {download_url}")
        print(f"📁 Saving to: {local_path}")
        
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

    def test_driver_extraction(self):
        """Test driver extraction functionality."""
        print("\n🔍 Testing Driver Extraction")
        print("=" * 30)
        
        try:
            # First download a test driver
            test_version = "120.0.2210.61"
            zip_path = self.download_driver(test_version)
            
            if not os.path.exists(zip_path):
                self.log_test_result(
                    "Driver Extraction",
                    False,
                    "Cannot test extraction without downloaded zip file"
                )
                return
            
            # Extract the driver
            driver_path = self.extract_driver(zip_path)
            
            if os.path.exists(driver_path):
                file_size = os.path.getsize(driver_path)
                self.log_test_result(
                    "Driver Extraction",
                    True,
                    f"Successfully extracted driver: {driver_path} ({file_size} bytes)",
                    {"driver_path": driver_path, "file_size": file_size, "zip_path": zip_path}
                )
                print(f"✅ Extracted: {driver_path}")
                print(f"�� Driver size: {file_size} bytes")
                
                # Test driver verification
                if self.verify_driver(driver_path):
                    self.log_test_result(
                        "Driver Verification",
                        True,
                        "Driver verification successful"
                    )
                else:
                    self.log_test_result(
                        "Driver Verification",
                        False,
                        "Driver verification failed"
                    )
                
                # Clean up test files
                try:
                    os.remove(zip_path)
                    os.remove(driver_path)
                    print(f"🧹 Cleaned up test files")
                except Exception as e:
                    print(f"⚠️ Warning: Could not remove test files: {e}")
            else:
                self.log_test_result(
                    "Driver Extraction",
                    False,
                    f"Extracted driver not found: {driver_path}"
                )
                
        except Exception as e:
            self.log_test_result(
                "Driver Extraction",
                False,
                f"Error extracting driver: {e}"
            )

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
            pass

    def _is_macos(self) -> bool:
        return self.platform.startswith("mac") or platform.system().lower() == "darwin"

    def test_network_connectivity(self):
        """Test network connectivity to EdgeDriver servers."""
        print("\n🔍 Testing Network Connectivity")
        print("=" * 35)
        
        try:
            # Test basic connectivity
            response = requests.get(self.EDGEDRIVER_BASE_URL, timeout=10)
            self.log_test_result(
                "Network Connectivity",
                response.status_code == 200,
                f"EdgeDriver server reachable (status: {response.status_code})",
                {"status_code": response.status_code, "url": self.EDGEDRIVER_BASE_URL}
            )
            print(f"✅ EdgeDriver server reachable: {response.status_code}")
            
        except Exception as e:
            self.log_test_result(
                "Network Connectivity",
                False,
                f"Network connectivity failed: {e}"
            )

    def run_all_tests(self):
        """Run all web download tests."""
        print("🚀 Starting Web Download Tests")
        print("=" * 50)
        print(f"Test directory: {self.test_dir}")
        print(f"Platform: {self.platform}")
        
        # Run all tests
        self.test_platform_detection()
        self.test_edge_version_detection()
        self.test_network_connectivity()
        self.test_compatible_driver_version_detection()
        self.test_driver_download()
        self.test_driver_extraction()
        
        # Print summary
        self.print_test_summary()

    def print_test_summary(self):
        """Print a summary of all test results."""
        print("\n📊 Test Summary")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success rate: {(passed/total)*100:.1f}%")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"  {status} {result['test']}: {result['message']}")
            
            if result["details"]:
                for key, value in result["details"].items():
                    print(f"    {key}: {value}")

def main():
    """Main test function."""
    print("🧪 Web Download Test Suite")
    print("=" * 50)
    
    # Create test directory in a temporary location
    with tempfile.TemporaryDirectory() as temp_dir:
        tester = WebDownloadTester(temp_dir)
        tester.run_all_tests()

if __name__ == "__main__":
    main()
