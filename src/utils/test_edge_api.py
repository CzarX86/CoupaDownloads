#!/usr/bin/env python3
"""
Test Microsoft EdgeDriver API endpoints to understand the correct URL structure.
This will help us fix the version detection issue.
"""

import requests
import re
from typing import Optional

def test_edge_api_endpoints():
    """Test various EdgeDriver API endpoints to find the correct ones."""
    print("🔍 Testing Microsoft EdgeDriver API Endpoints")
    print("=" * 50)
    
    base_url = "https://msedgedriver.microsoft.com"
    
    # Test different endpoint patterns
    endpoints_to_test = [
        # Current pattern (failing)
        f"{base_url}/LATEST_RELEASE_139_stable",
        
        # Alternative patterns to try
        f"{base_url}/LATEST_RELEASE_139",
        f"{base_url}/LATEST_RELEASE_139.0",
        f"{base_url}/LATEST_RELEASE_139.0.3405",
        
        # Try with different suffixes
        f"{base_url}/LATEST_RELEASE_139_stable",
        f"{base_url}/LATEST_RELEASE_139_beta",
        f"{base_url}/LATEST_RELEASE_139_dev",
        
        # Try different major versions
        f"{base_url}/LATEST_RELEASE_120_stable",
        f"{base_url}/LATEST_RELEASE_119_stable",
        f"{base_url}/LATEST_RELEASE_118_stable",
        
        # Try without version specification
        f"{base_url}/LATEST_RELEASE",
        f"{base_url}/LATEST_RELEASE_stable",
        
        # Try different URL patterns
        f"{base_url}/latest",
        f"{base_url}/latest/stable",
        f"{base_url}/latest/139",
        f"{base_url}/latest/139/stable",
    ]
    
    successful_endpoints = []
    
    for endpoint in endpoints_to_test:
        print(f"\n🔗 Testing: {endpoint}")
        try:
            response = requests.get(endpoint, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                print(f"   Content (first 200 chars): {content[:200]}...")
                
                # Try to extract version information
                version_patterns = [
                    r'<Name>([0-9.]+)/</Name>',
                    r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',
                    r'version[":\s]*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',
                ]
                
                for pattern in version_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        print(f"   ✅ Found versions: {matches}")
                        successful_endpoints.append({
                            'endpoint': endpoint,
                            'status': response.status_code,
                            'versions': matches,
                            'content_preview': content[:100]
                        })
                        break
                else:
                    print(f"   ⚠️ No version pattern matched")
                    
            elif response.status_code == 404:
                print(f"   ❌ 404 Not Found")
            else:
                print(f"   ⚠️ Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Test direct download URLs
    print(f"\n🔍 Testing Direct Download URLs")
    print("=" * 40)
    
    # Test with a known working version
    test_versions = ["120.0.2210.61", "119.0.2151.97", "118.0.2088.76"]
    platform = "mac64_m1"  # Based on your system
    
    for version in test_versions:
        download_url = f"{base_url}/{version}/edgedriver_{platform}.zip"
        print(f"\n🔗 Testing download: {download_url}")
        
        try:
            response = requests.head(download_url, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ Download URL works!")
                successful_endpoints.append({
                    'endpoint': download_url,
                    'status': response.status_code,
                    'type': 'download_url',
                    'version': version
                })
            else:
                print(f"   ❌ Download URL failed")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Summary
    print(f"\n📊 Summary of Successful Endpoints")
    print("=" * 40)
    
    if successful_endpoints:
        for i, endpoint_info in enumerate(successful_endpoints, 1):
            print(f"{i}. {endpoint_info['endpoint']}")
            print(f"   Status: {endpoint_info['status']}")
            if 'versions' in endpoint_info:
                print(f"   Versions: {endpoint_info['versions']}")
            if 'type' in endpoint_info:
                print(f"   Type: {endpoint_info['type']}")
            print()
    else:
        print("❌ No successful endpoints found")
    
    return successful_endpoints

def test_alternative_sources():
    """Test alternative sources for EdgeDriver information."""
    print(f"\n🔍 Testing Alternative Sources")
    print("=" * 40)
    
    # Test GitHub releases
    github_url = "https://api.github.com/repos/microsoft/edge-selenium-tools/releases/latest"
    print(f"�� Testing GitHub API: {github_url}")
    
    try:
        response = requests.get(github_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ GitHub API works!")
            print(f"   Latest release: {data.get('tag_name', 'Unknown')}")
            print(f"   Published: {data.get('published_at', 'Unknown')}")
            
            # Look for assets
            assets = data.get('assets', [])
            for asset in assets:
                if 'edgedriver' in asset.get('name', '').lower():
                    print(f"   Asset: {asset.get('name')} - {asset.get('browser_download_url')}")
        else:
            print(f"   ❌ GitHub API failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ GitHub API error: {e}")

def main():
    """Main test function."""
    print("🧪 Microsoft EdgeDriver API Investigation")
    print("=" * 50)
    
    # Test API endpoints
    successful_endpoints = test_edge_api_endpoints()
    
    # Test alternative sources
    test_alternative_sources()
    
    # Recommendations
    print(f"\n💡 Recommendations")
    print("=" * 30)
    
    if successful_endpoints:
        print("✅ Found working endpoints!")
        print("Update the driver_manager.py to use these working URLs.")
    else:
        print("❌ No working endpoints found")
        print("Consider using alternative download methods or manual downloads.")

if __name__ == "__main__":
    main()
