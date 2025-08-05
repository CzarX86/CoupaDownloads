#!/usr/bin/env python3
"""
Release Verification Script
Verifies that the Coupa Downloads automation is ready for production release.
"""

import sys
import os
import importlib

def check_imports():
    """Check that all core modules can be imported."""
    print("🔍 Checking module imports...")
    
    try:
        # Add src to path
        sys.path.append('src')
        
        # Test core imports
        from core.browser import BrowserManager
        from core.config import Config
        from core.downloader import DownloadManager, LoginManager
        from core.csv_processor import CSVProcessor
        from core.excel_processor import ExcelProcessor
        from core.unified_processor import UnifiedProcessor
        from core.progress_manager import progress_manager
        from core.msg_processor import MSGProcessor
        
        print("✅ All core modules import successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def check_main_application():
    """Check that the main application can be imported."""
    print("🔍 Checking main application...")
    
    try:
        from src.main import CoupaDownloader
        print("✅ Main application imports successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Main application import error: {e}")
        return False

def check_configuration():
    """Check that configuration is properly set up."""
    print("🔍 Checking configuration...")
    
    try:
        # Add src to path for proper import
        sys.path.append('src')
        from core.config import Config
        
        # Check essential config values
        assert hasattr(Config, 'DOWNLOAD_FOLDER')
        assert hasattr(Config, 'ALLOWED_EXTENSIONS')
        assert hasattr(Config, 'BASE_URL')
        
        print(f"✅ Configuration loaded successfully")
        print(f"   Download folder: {Config.DOWNLOAD_FOLDER}")
        print(f"   Allowed extensions: {len(Config.ALLOWED_EXTENSIONS)} types")
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def check_dependencies():
    """Check that all required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'selenium',
        'pandas', 
        'openpyxl',
        'extract_msg',
        'weasyprint',
        'requests',
        'pytest'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {missing_packages}")
        return False
    else:
        print("✅ All required dependencies available")
        return True

def check_file_structure():
    """Check that essential files exist."""
    print("🔍 Checking file structure...")
    
    essential_files = [
        'src/main.py',
        'src/core/__init__.py',
        'src/core/browser.py',
        'src/core/config.py',
        'src/core/downloader.py',
        'src/core/csv_processor.py',
        'src/core/excel_processor.py',
        'src/core/unified_processor.py',
        'requirements.txt',
        'README.md',
        'docs/FINAL_RELEASE_SUMMARY.md'
    ]
    
    missing_files = []
    
    for file_path in essential_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All essential files present")
        return True

def main():
    """Run all verification checks."""
    print("🚀 Coupa Downloads - Release Verification")
    print("=" * 50)
    
    checks = [
        ("File Structure", check_file_structure),
        ("Dependencies", check_dependencies),
        ("Configuration", check_configuration),
        ("Module Imports", check_imports),
        ("Main Application", check_main_application)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        print("-" * 30)
        result = check_func()
        results.append((check_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 ALL CHECKS PASSED!")
        print("✅ The application is ready for production release")
        print("✅ Ready for executable build")
        return True
    else:
        print(f"\n⚠️  {total - passed} checks failed")
        print("❌ Please fix the issues before release")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 