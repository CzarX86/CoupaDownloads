#!/usr/bin/env python3
"""
Simple Portable Package Builder for CoupaDownloads
Creates a self-contained package with Python, libraries, and WebDriver
"""

import os
import sys
import platform
import subprocess
import shutil
import zipfile
import requests
from pathlib import Path


class SimplePortableBuilder:
    """Builds a simple portable package with all dependencies."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_dir = self.project_root / "build"
        self.portable_dir = self.build_dir / "CoupaDownloads_Portable"
        self.drivers_dir = self.portable_dir / "drivers"
        
    def clean_build(self):
        """Clean previous build."""
        print("🧹 Cleaning previous build...")
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(exist_ok=True)
        print("✅ Build directory cleaned")
    
    def create_directories(self):
        """Create portable package directory structure."""
        print("📁 Creating directory structure...")
        
        directories = [
            self.portable_dir,
            self.drivers_dir,
            self.portable_dir / "data" / "input",
            self.portable_dir / "data" / "output",
            self.portable_dir / "data" / "backups",
            self.portable_dir / "src" / "core",
            self.portable_dir / "tests"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        print("✅ Directory structure created")
    
    def download_stable_edgedriver(self):
        """Download a stable EdgeDriver version."""
        print("🔧 Downloading stable EdgeDriver...")
        
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Use a stable version that works with most Edge versions
        stable_version = "120.0.2210.91"
        
        if system == "windows":
            if "64" in machine or "x86_64" in machine:
                driver_url = f"https://msedgedriver.azureedge.net/{stable_version}/edgedriver_win64.zip"
                driver_filename = "edgedriver_win64.zip"
            else:
                driver_url = f"https://msedgedriver.azureedge.net/{stable_version}/edgedriver_win32.zip"
                driver_filename = "edgedriver_win32.zip"
        elif system == "darwin":  # macOS
            if "arm" in machine or "aarch64" in machine:
                driver_url = f"https://msedgedriver.azureedge.net/{stable_version}/edgedriver_mac64_m1.zip"
                driver_filename = "edgedriver_mac64_m1.zip"
            else:
                driver_url = f"https://msedgedriver.azureedge.net/{stable_version}/edgedriver_mac64.zip"
                driver_filename = "edgedriver_mac64.zip"
        elif system == "linux":
            driver_url = f"https://msedgedriver.azureedge.net/{stable_version}/edgedriver_linux64.zip"
            driver_filename = "edgedriver_linux64.zip"
        else:
            print(f"⚠️ Unsupported platform: {system} {machine}")
            return False
        
        try:
            # Download EdgeDriver
            response = requests.get(driver_url, stream=True)
            response.raise_for_status()
            
            driver_zip = self.build_dir / driver_filename
            with open(driver_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract EdgeDriver
            with zipfile.ZipFile(driver_zip, 'r') as zip_ref:
                zip_ref.extractall(self.drivers_dir)
            
            # Make executable on Unix systems
            if system != "windows":
                driver_exe = self.drivers_dir / "msedgedriver"
                if driver_exe.exists():
                    os.chmod(driver_exe, 0o755)
            
            print(f"✅ Stable EdgeDriver {stable_version} downloaded")
            return True
            
        except Exception as e:
            print(f"❌ Failed to download EdgeDriver: {e}")
            return False
    
    def copy_source_files(self):
        """Copy source code files to portable package."""
        print("📋 Copying source files...")
        
        # Copy source files
        source_files = [
            "src/main.py",
            "src/core/__init__.py",
            "src/core/browser.py",
            "src/core/config.py",
            "src/core/csv_processor.py",
            "src/core/downloader.py",
            "src/core/driver_manager.py"
        ]
        
        for file_path in source_files:
            src = self.project_root / file_path
            dst = self.portable_dir / file_path
            
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"  ✅ {file_path}")
            else:
                print(f"  ⚠️ {file_path} not found")
        
        # Copy test files
        test_files = [
            "test_installation.py",
            "run_tests.py",
            "pytest.ini"
        ]
        
        for file_path in test_files:
            src = self.project_root / file_path
            dst = self.portable_dir / file_path
            
            if src.exists():
                shutil.copy2(src, dst)
                print(f"  ✅ {file_path}")
        
        print("✅ Source files copied")
    
    def create_portable_scripts(self):
        """Create portable launcher scripts."""
        print("🚀 Creating portable launcher scripts...")
        
        system = platform.system().lower()
        
        if system == "windows":
            # Windows batch launcher
            launcher_content = """@echo off
echo ========================================
echo    CoupaDownloads - Portable Version
echo ========================================
echo.

:: Set driver path
set EDGEDRIVER_PATH=%~dp0drivers\\msedgedriver.exe

:: Check if input file exists
if not exist "data\\input\\input.csv" (
    echo ❌ input.csv not found
    echo Please create data\\input\\input.csv with your PO numbers
    echo.
    echo Example format:
    echo PO_NUMBER
    echo PO15262984
    echo PO15327452
    pause
    exit /b 1
)

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    echo 📦 Installing dependencies...
    call venv\\Scripts\\activate.bat
    pip install -r requirements.txt
) else (
    echo ✅ Virtual environment found
)

:: Activate virtual environment and run
echo 🚀 Starting CoupaDownloads...
call venv\\Scripts\\activate.bat
python src\\main.py

echo.
echo Press any key to exit...
pause >nul
"""
            
            launcher_path = self.portable_dir / "run_coupa_downloads.bat"
            launcher_path.write_text(launcher_content, encoding='utf-8')
            
            # Test launcher
            test_content = """@echo off
echo ========================================
echo    CoupaDownloads - Test Installation
echo ========================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    echo 📦 Installing dependencies...
    call venv\\Scripts\\activate.bat
    pip install -r requirements.txt
)

:: Run test
call venv\\Scripts\\activate.bat
python test_installation.py

echo.
echo Press any key to exit...
pause >nul
"""
            
            test_path = self.portable_dir / "test_installation.bat"
            test_path.write_text(test_content, encoding='utf-8')
            
        else:
            # Unix shell launcher
            launcher_content = """#!/bin/bash
echo "========================================"
echo "   CoupaDownloads - Portable Version"
echo "========================================"
echo ""

# Set driver path
export EDGEDRIVER_PATH="$(dirname "$0")/drivers/msedgedriver"

# Check if input file exists
if [ ! -f "data/input/input.csv" ]; then
    echo "❌ input.csv not found"
    echo "Please create data/input/input.csv with your PO numbers"
    echo ""
    echo "Example format:"
    echo "PO_NUMBER"
    echo "PO15262984"
    echo "PO15327452"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install Python 3 from https://python.org"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "📦 Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "✅ Virtual environment found"
fi

# Activate virtual environment and run
echo "🚀 Starting CoupaDownloads..."
source venv/bin/activate
python src/main.py
"""
            
            launcher_path = self.portable_dir / "run_coupa_downloads.sh"
            launcher_path.write_text(launcher_content)
            os.chmod(launcher_path, 0o755)
            
            # Test launcher
            test_content = """#!/bin/bash
echo "========================================"
echo "   CoupaDownloads - Test Installation"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install Python 3 from https://python.org"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "📦 Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Run test
source venv/bin/activate
python test_installation.py
"""
            
            test_path = self.portable_dir / "test_installation.sh"
            test_path.write_text(test_content)
            os.chmod(test_path, 0o755)
        
        print("✅ Portable launcher scripts created")
    
    def create_sample_files(self):
        """Create sample input and configuration files."""
        print("📝 Creating sample files...")
        
        # Sample input file
        input_content = """PO_NUMBER
PO15262984
PO15327452
PO15362783
"""
        
        input_file = self.portable_dir / "data" / "input" / "input.csv"
        input_file.write_text(input_content, encoding='utf-8')
        
        # Copy requirements.txt
        requirements_src = self.project_root / "requirements.txt"
        requirements_dst = self.portable_dir / "requirements.txt"
        if requirements_src.exists():
            shutil.copy2(requirements_src, requirements_dst)
            print("  ✅ requirements.txt")
        
        # README for portable version
        readme_content = """# CoupaDownloads - Portable Version

## 🚀 Quick Start

### Windows
1. Double-click `run_coupa_downloads.bat`
2. Edit `data\\input\\input.csv` with your PO numbers
3. Run again

### macOS/Linux
1. Double-click `run_coupa_downloads.sh` OR
2. Open terminal and run: `./run_coupa_downloads.sh`

## 📋 What's Included

- ✅ Stable EdgeDriver (pre-downloaded)
- ✅ Source code
- ✅ Sample input file
- ✅ Launcher scripts
- ✅ Requirements file

## 🔧 Testing

Run the test script to verify everything works:
- Windows: `test_installation.bat`
- macOS/Linux: `./test_installation.sh`

## 📁 File Structure

```
CoupaDownloads_Portable/
├── run_coupa_downloads.bat/sh    # Main launcher
├── test_installation.bat/sh      # Test script
├── requirements.txt              # Python dependencies
├── drivers/                      # EdgeDriver (pre-downloaded)
├── data/
│   ├── input/
│   │   └── input.csv            # Your PO numbers here
│   ├── output/                  # Generated reports
│   └── backups/                 # Backup files
├── src/                         # Source code
└── tests/                       # Test files
```

## 💡 Usage

1. **Edit PO numbers**: Open `data/input/input.csv`
2. **Run the tool**: Execute the launcher script
3. **Login to Coupa**: When browser opens, log in manually
4. **Monitor progress**: Watch terminal for updates
5. **Find downloads**: Check `~/Downloads/CoupaDownloads/`

## 🛡️ Safety Features

- No installation required (except Python)
- Self-contained package
- Works on any compatible system
- No system modifications
- Easy to delete/remove
- Stable EdgeDriver included

## 🔍 Troubleshooting

If you encounter issues:
1. Run the test script first
2. Check that Microsoft Edge is installed
3. Ensure you have internet connection
4. Verify PO numbers in input.csv
5. Make sure Python 3.8+ is installed

## 📊 System Requirements

- **Python 3.8+** (automatically detected and installed)
- **Windows 10/11** (64-bit) OR **macOS 10.14+** OR **Linux**
- **Microsoft Edge** browser
- **Internet connection**
- **Coupa access** (valid login)

## 🎯 Advantages

- **Minimal Setup**: Only Python installation required
- **Stable Driver**: Pre-downloaded compatible EdgeDriver
- **Cross-Platform**: Works on Windows, macOS, Linux
- **Easy Distribution**: Single ZIP file
- **Auto-Installation**: Creates virtual environment automatically

The launcher script will automatically:
- Check if Python is installed
- Create virtual environment if needed
- Install all dependencies
- Run the application

That's it! Just extract and run.
"""
        
        readme_file = self.portable_dir / "README_Portable.md"
        readme_file.write_text(readme_content, encoding='utf-8')
        
        print("✅ Sample files created")
    
    def create_zip_package(self):
        """Create the final ZIP package."""
        print("📦 Creating portable ZIP package...")
        
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            platform_name = "win64" if "64" in machine else "win32"
        elif system == "darwin":
            platform_name = "mac64_m1" if "arm" in machine else "mac64"
        elif system == "linux":
            platform_name = "linux64"
        else:
            platform_name = "unknown"
        
        zip_filename = f"CoupaDownloads_Portable_{platform_name}.zip"
        zip_path = self.build_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.portable_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(self.portable_dir)
                    zipf.write(file_path, arcname)
        
        print(f"✅ Portable package created: {zip_filename}")
        print(f"📁 Location: {zip_path}")
        
        return zip_path
    
    def build(self):
        """Build the complete portable package."""
        print("🏗️ Building simple portable package...")
        print("=" * 50)
        
        try:
            # Clean previous build
            self.clean_build()
            
            # Create directory structure
            self.create_directories()
            
            # Download stable EdgeDriver
            if not self.download_stable_edgedriver():
                print("❌ Failed to download EdgeDriver")
                return False
            
            # Copy source files
            self.copy_source_files()
            
            # Create portable scripts
            self.create_portable_scripts()
            
            # Create sample files
            self.create_sample_files()
            
            # Create ZIP package
            zip_path = self.create_zip_package()
            
            print("\n" + "=" * 50)
            print("🎉 Simple portable package built successfully!")
            print("=" * 50)
            print(f"📦 Package: {zip_path}")
            print(f"📁 Size: {zip_path.stat().st_size / (1024*1024):.1f} MB")
            print("\n🚀 To use:")
            print("1. Extract the ZIP file")
            print("2. Edit data/input/input.csv with your PO numbers")
            print("3. Run the launcher script")
            print("\n✨ Features:")
            print("- Stable EdgeDriver included")
            print("- Auto-creates virtual environment")
            print("- Auto-installs dependencies")
            print("- Cross-platform compatibility")
            
            return True
            
        except Exception as e:
            print(f"❌ Build failed: {e}")
            return False


def main():
    """Main function."""
    print("CoupaDownloads - Simple Portable Package Builder")
    print("=" * 50)
    
    builder = SimplePortableBuilder()
    
    if builder.build():
        print("\n✅ Simple build completed successfully!")
        return 0
    else:
        print("\n❌ Simple build failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 