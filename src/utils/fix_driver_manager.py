#!/usr/bin/env python3
"""
Fix for driver_manager.py web download functionality.
Addresses the incorrect URL pattern issue discovered in testing.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.driver_manager import DriverManager

class FixedDriverManager(DriverManager):
    """
    Fixed version of DriverManager with correct API endpoints.
    """
    
    def get_compatible_driver_version(self, edge_version: str) -> str:
        """Get the compatible EdgeDriver version from the web - FIXED VERSION."""
        major_version = edge_version.split('.')[0]
        
        # FIXED: Use correct URL pattern without '_stable' suffix
        url = f"{self.EDGEDRIVER_BASE_URL}/LATEST_RELEASE_{major_version}"
        
        try:
            print(f"🔗 Fetching from: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # The response is plain text with just the version number
            driver_version = response.text.strip()
            
            if driver_version and re.match(r'^\d+\.\d+\.\d+\.\d+$', driver_version):
                print(f"🔧 Found compatible driver version online: {driver_version}")
                return driver_version
            else:
                raise ValueError(f"Invalid version format received: {driver_version}")
                
        except Exception as e:
            print(f"⚠️ Warning: Could not get compatible driver version: {e}")
            print("🔄 Falling back to known stable versions...")
            
            # Fallback to known working versions
            fallback_versions = [
                "120.0.2210.61",  # Known working version
                "119.0.2151.97",  # Previous stable
                "118.0.2088.76",  # Previous stable
            ]
            
            for version in fallback_versions:
                if self._test_version_availability(version):
                    print(f"✅ Using fallback version: {version}")
                    return version
            
            # Last resort
            print("⚠️ No compatible version found, using hardcoded fallback")
            return "120.0.2210.61"
    
    def _test_version_availability(self, version: str) -> bool:
        """Test if a specific driver version is available."""
        try:
            zip_name = f"edgedriver_{self.platform}.zip"
            url = f"{self.EDGEDRIVER_BASE_URL}/{version}/{zip_name}"
            response = requests.head(url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

def test_fixed_driver_manager():
    """Test the fixed driver manager functionality."""
    print("🧪 Testing Fixed Driver Manager")
    print("=" * 40)
    
    try:
        # Create fixed driver manager
        driver_manager = FixedDriverManager()
        
        # Test Edge version detection
        edge_version = driver_manager.get_edge_version()
        print(f"Edge version: {edge_version}")
        
        if edge_version:
            # Test compatible version detection
            compatible_version = driver_manager.get_compatible_driver_version(edge_version)
            print(f"Compatible driver version: {compatible_version}")
            
            # Test download
            print(f"\n📥 Testing download of version: {compatible_version}")
            zip_path = driver_manager.download_driver(compatible_version)
            
            if os.path.exists(zip_path):
                print(f"✅ Download successful: {zip_path}")
                
                # Test extraction
                driver_path = driver_manager.extract_driver(zip_path)
                print(f"✅ Extraction successful: {driver_path}")
                
                # Test verification
                if driver_manager.verify_driver(driver_path):
                    print("✅ Driver verification successful!")
                else:
                    print("❌ Driver verification failed")
                
                # Cleanup
                try:
                    os.remove(zip_path)
                    os.remove(driver_path)
                    print("🧹 Cleaned up test files")
                except Exception as e:
                    print(f"⚠️ Warning: Could not remove test files: {e}")
            else:
                print("❌ Download failed")
        else:
            print("❌ Could not detect Edge version")
            
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_driver_manager()
