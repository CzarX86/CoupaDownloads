#!/usr/bin/env python3
"""
Test script to verify CoupaDownloads installation
Checks all components and provides detailed feedback
"""

import os
import sys
import platform
import subprocess
from pathlib import Path


def print_header():
    """Print test header."""
    print("=" * 60)
    print("    CoupaDownloads - Installation Test")
    print("=" * 60)
    print()


def test_python_version():
    """Test Python version."""
    print("🐍 Testing Python version...")
    version = sys.version_info
    
    if version >= (3, 8):
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Requires 3.8+")
        return False


def test_virtual_environment():
    """Test virtual environment."""
    print("\n📦 Testing virtual environment...")
    
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment is active")
        return True
    else:
        print("⚠️ Virtual environment not detected")
        print("   Run: source venv/bin/activate (or venv\\Scripts\\activate on Windows)")
        return False


def test_dependencies():
    """Test if all dependencies are installed."""
    print("\n📦 Testing Python dependencies...")
    
    required_packages = [
        'selenium',
        'requests', 
        'pandas',
        'openpyxl',
        'pytest'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    return True


def test_edge_detection():
    """Test Edge browser detection."""
    print("\n🔍 Testing Microsoft Edge detection...")
    
    system = platform.system()
    
    if system == "Windows":
        # Test PowerShell detection
        try:
            result = subprocess.run([
                "powershell", "-Command", 
                "(Get-AppxPackage Microsoft.MicrosoftEdge.Stable).Version"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip()
                print(f"✅ Microsoft Edge found (Windows Store): {version}")
                return True
        except:
            pass
        
        # Test traditional installation
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
        
        for path in edge_paths:
            if Path(path).exists():
                print(f"✅ Microsoft Edge found (Traditional): {path}")
                return True
    
    elif system == "Darwin":  # macOS
        edge_path = Path("/Applications/Microsoft Edge.app")
        if edge_path.exists():
            print("✅ Microsoft Edge found (macOS)")
            return True
    
    elif system == "Linux":
        edge_paths = [
            "/usr/bin/microsoft-edge",
            "/usr/bin/microsoft-edge-stable",
            "/opt/microsoft/msedge/microsoft-edge"
        ]
        
        for path in edge_paths:
            if Path(path).exists():
                print(f"✅ Microsoft Edge found (Linux): {path}")
                return True
    
    print("⚠️ Microsoft Edge not found")
    print("   Install from: https://microsoft.com/edge")
    return False


def test_driver_manager():
    """Test the DriverManager module."""
    print("\n🔧 Testing DriverManager...")
    
    try:
        from src.core.driver_manager import DriverManager
        
        driver_manager = DriverManager()
        print("✅ DriverManager imported successfully")
        
        # Test platform detection
        platform = driver_manager.platform
        print(f"✅ Platform detected: {platform}")
        
        # Test Edge version detection (if Edge is installed)
        edge_version = driver_manager.get_edge_version()
        if edge_version:
            print(f"✅ Edge version detected: {edge_version}")
        else:
            print("⚠️ Edge version not detected (Edge may not be installed)")
        
        return True
        
    except ImportError as e:
        print(f"❌ DriverManager import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ DriverManager test failed: {e}")
        return False


def test_project_structure():
    """Test project structure and files."""
    print("\n📁 Testing project structure...")
    
    required_files = [
        "src/main.py",
        "src/core/config.py",
        "src/core/browser.py",
        "src/core/downloader.py",
        "src/core/csv_processor.py",
        "src/core/driver_manager.py",
        "requirements.txt",
        "data/input/input.csv"
    ]
    
    required_dirs = [
        "src",
        "src/core",
        "data",
        "data/input",
        "data/output",
        "drivers"
    ]
    
    missing_files = []
    missing_dirs = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
            missing_files.append(file_path)
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/ - Missing")
            missing_dirs.append(dir_path)
    
    if missing_files or missing_dirs:
        print(f"\n⚠️ Missing: {len(missing_files)} files, {len(missing_dirs)} directories")
        return False
    
    return True


def test_sample_input():
    """Test sample input file."""
    print("\n📝 Testing sample input file...")
    
    input_file = Path("data/input/input.csv")
    
    if not input_file.exists():
        print("❌ input.csv not found")
        return False
    
    try:
        content = input_file.read_text(encoding='utf-8')
        lines = content.strip().split('\n')
        
        if len(lines) >= 2 and lines[0] == "PO_NUMBER":
            print(f"✅ input.csv format is correct ({len(lines)-1} PO numbers)")
            return True
        else:
            print("❌ input.csv format is incorrect")
            print("   Expected: PO_NUMBER header followed by PO numbers")
            return False
            
    except Exception as e:
        print(f"❌ Error reading input.csv: {e}")
        return False


def test_browser_manager():
    """Test BrowserManager module."""
    print("\n🌐 Testing BrowserManager...")
    
    try:
        from src.core.browser import BrowserManager
        
        browser_manager = BrowserManager()
        print("✅ BrowserManager imported successfully")
        
        # Test driver manager integration
        if hasattr(browser_manager, 'driver_manager'):
            print("✅ DriverManager integration working")
        else:
            print("❌ DriverManager not integrated")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ BrowserManager import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ BrowserManager test failed: {e}")
        return False


def run_integration_test():
    """Run a basic integration test."""
    print("\n🧪 Running integration test...")
    
    try:
        # Test CSV processor
        from src.core.csv_processor import CSVProcessor
        
        csv_file_path = CSVProcessor.get_csv_file_path()
        if Path(csv_file_path).exists():
            print("✅ CSV processor working")
        else:
            print("❌ CSV file not found")
            return False
        
        # Test config
        from src.core.config import Config
        
        Config.ensure_download_folder_exists()
        if Path(Config.DOWNLOAD_FOLDER).exists():
            print("✅ Config and download folder working")
        else:
            print("❌ Download folder creation failed")
            return False
        
        print("✅ Integration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def print_summary(results):
    """Print test summary."""
    print("\n" + "=" * 60)
    print("    Test Summary")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your installation is ready.")
        print("\n🚀 Next steps:")
        print("1. Edit data/input/input.csv with your PO numbers")
        print("2. Run: python src/main.py")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please check the issues above.")
        print("\n💡 Try running the installer again:")
        print("   Windows: install_windows.bat")
        print("   All platforms: python install.py")


def main():
    """Main test function."""
    print_header()
    
    results = {}
    
    # Run all tests
    results["Python Version"] = test_python_version()
    results["Virtual Environment"] = test_virtual_environment()
    results["Dependencies"] = test_dependencies()
    results["Edge Detection"] = test_edge_detection()
    results["DriverManager"] = test_driver_manager()
    results["Project Structure"] = test_project_structure()
    results["Sample Input"] = test_sample_input()
    results["BrowserManager"] = test_browser_manager()
    results["Integration Test"] = run_integration_test()
    
    # Print summary
    print_summary(results)
    
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main()) 