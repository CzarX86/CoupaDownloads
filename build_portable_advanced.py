#!/usr/bin/env python3
"""
Advanced Portable Package Builder for CoupaDownloads
Creates a self-contained package with Python, all libraries, and WebDriver
"""

import os
import sys
import platform
import subprocess
import shutil
import zipfile
import requests
import venv
from pathlib import Path
import json


class AdvancedPortableBuilder:
    """Builds a complete portable package with all dependencies."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_dir = self.project_root / "build"
        self.portable_dir = self.build_dir / "CoupaDownloads_Portable"
        self.python_dir = self.portable_dir / "python"
        self.site_packages_dir = self.python_dir / "Lib" / "site-packages"
        self.scripts_dir = self.portable_dir / "scripts"
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
            self.python_dir,
            self.scripts_dir,
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
    
    def setup_portable_python(self):
        """Setup portable Python with all dependencies."""
        print("🐍 Setting up portable Python...")
        
        system = platform.system().lower()
        
        if system == "windows":
            return self.setup_windows_portable_python()
        else:
            return self.setup_unix_portable_python()
    
    def setup_windows_portable_python(self):
        """Setup portable Python for Windows."""
        try:
            # Create virtual environment in the portable directory
            venv.create(self.python_dir, with_pip=True)
            
            # Get Python executable paths
            python_exe = self.python_dir / "Scripts" / "python.exe"
            pip_exe = self.python_dir / "Scripts" / "pip.exe"
            
            if not python_exe.exists():
                print("❌ Python executable not found in virtual environment")
                return False
            
            # Install all dependencies
            print("📦 Installing Python dependencies...")
            
            # Upgrade pip first
            subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], 
                          check=True, capture_output=True)
            
            # Install requirements
            requirements_file = self.project_root / "requirements.txt"
            if requirements_file.exists():
                subprocess.run([str(pip_exe), "install", "-r", str(requirements_file)], 
                              check=True, capture_output=True)
            
            print("✅ Portable Python setup completed")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup portable Python: {e}")
            return False
    
    def setup_unix_portable_python(self):
        """Setup portable Python for Unix systems."""
        try:
            # Create virtual environment in the portable directory
            venv.create(self.python_dir, with_pip=True)
            
            # Get Python executable paths
            python_exe = self.python_dir / "bin" / "python"
            pip_exe = self.python_dir / "bin" / "pip"
            
            if not python_exe.exists():
                print("❌ Python executable not found in virtual environment")
                return False
            
            # Install all dependencies
            print("📦 Installing Python dependencies...")
            
            # Upgrade pip first
            subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], 
                          check=True, capture_output=True)
            
            # Install requirements
            requirements_file = self.project_root / "requirements.txt"
            if requirements_file.exists():
                subprocess.run([str(pip_exe), "install", "-r", str(requirements_file)], 
                              check=True, capture_output=True)
            
            print("✅ Portable Python setup completed")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup portable Python: {e}")
            return False
    
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

:: Set Python path
set PYTHONPATH=%~dp0python
set PATH=%~dp0python;%~dp0python\\Scripts;%PATH%

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

:: Run the application
echo 🚀 Starting CoupaDownloads...
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

:: Set Python path
set PYTHONPATH=%~dp0python
set PATH=%~dp0python;%~dp0python\\Scripts;%PATH%

:: Run test
python test_installation.py

echo.
echo Press any key to exit...
pause >nul
"""
            
            test_path = self.portable_dir / "test_installation.bat"
            test_path.write_text(test_content, encoding='utf-8')
            
            # Install launcher
            install_content = """@echo off
echo ========================================
echo    CoupaDownloads - Install Dependencies
echo ========================================
echo.

:: Set Python path
set PYTHONPATH=%~dp0python
set PATH=%~dp0python;%~dp0python\\Scripts;%PATH%

:: Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt

echo.
echo ✅ Installation complete!
echo Press any key to exit...
pause >nul
"""
            
            install_path = self.portable_dir / "install_dependencies.bat"
            install_path.write_text(install_content, encoding='utf-8')
            
        else:
            # Unix shell launcher
            launcher_content = """#!/bin/bash
echo "========================================"
echo "   CoupaDownloads - Portable Version"
echo "========================================"
echo ""

# Set Python path
export PYTHONPATH="$(dirname "$0")/python"
export PATH="$(dirname "$0")/python/bin:$PATH"

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

# Run the application
echo "🚀 Starting CoupaDownloads..."
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

# Set Python path
export PYTHONPATH="$(dirname "$0")/python"
export PATH="$(dirname "$0")/python/bin:$PATH"

# Run test
python test_installation.py
"""
            
            test_path = self.portable_dir / "test_installation.sh"
            test_path.write_text(test_content)
            os.chmod(test_path, 0o755)
            
            # Install launcher
            install_content = """#!/bin/bash
echo "========================================"
echo "   CoupaDownloads - Install Dependencies"
echo "========================================"
echo ""

# Set Python path
export PYTHONPATH="$(dirname "$0")/python"
export PATH="$(dirname "$0")/python/bin:$PATH"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Installation complete!"
"""
            
            install_path = self.portable_dir / "install_dependencies.sh"
            install_path.write_text(install_content)
            os.chmod(install_path, 0o755)
        
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

- ✅ Python 3.x (portable with all dependencies)
- ✅ All required libraries (selenium, pandas, openpyxl, etc.)
- ✅ Stable EdgeDriver
- ✅ Source code
- ✅ Sample input file
- ✅ Launcher scripts

## 🔧 Testing

Run the test script to verify everything works:
- Windows: `test_installation.bat`
- macOS/Linux: `./test_installation.sh`

## 📁 File Structure

```
CoupaDownloads_Portable/
├── run_coupa_downloads.bat/sh    # Main launcher
├── test_installation.bat/sh      # Test script
├── install_dependencies.bat/sh   # Dependency installer
├── python/                       # Portable Python with all libs
│   ├── Scripts/ (Windows)        # Python executables
│   ├── bin/ (Unix)              # Python executables
│   └── Lib/site-packages/       # All Python libraries
├── drivers/                      # EdgeDriver
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

- No installation required
- Self-contained package with all dependencies
- Works on any compatible system
- No system modifications
- Easy to delete/remove
- Portable Python included

## 🔍 Troubleshooting

If you encounter issues:
1. Run the test script first
2. Check that Microsoft Edge is installed
3. Ensure you have internet connection
4. Verify PO numbers in input.csv
5. Run `install_dependencies.bat/sh` if needed

## 📊 System Requirements

- **Windows 10/11** (64-bit) OR **macOS 10.14+** OR **Linux**
- **Microsoft Edge** browser
- **Internet connection**
- **Coupa access** (valid login)

## 🎯 Advantages

- **Zero Installation**: No Python installation required
- **Complete Package**: All dependencies included
- **Cross-Platform**: Works on Windows, macOS, Linux
- **Stable Driver**: Pre-downloaded compatible EdgeDriver
- **Easy Distribution**: Single ZIP file contains everything

That's it! No Python installation, no driver downloads, no library installation needed.
"""
        
        readme_file = self.portable_dir / "README_Portable.md"
        readme_file.write_text(readme_content, encoding='utf-8')
        
        print("✅ Sample files created")
    
    def create_requirements_file(self):
        """Create requirements.txt for the portable version."""
        print("📦 Creating requirements file...")
        
        requirements_content = """# Portable Package Requirements
# These are already included in the portable package

selenium>=4.0.0
requests>=2.31.0
pandas>=1.5.0
openpyxl>=3.0.0
psutil>=5.8.0
pytest>=7.0.0
pytest-mock>=3.10.0
pytest-cov>=4.0.0
pytest-xdist>=3.0.0
pytest-timeout>=2.0.0
pytest-html>=3.0.0
freezegun>=1.2.0
factory-boy>=3.2.0
faker>=18.0.0
"""
        
        requirements_file = self.portable_dir / "requirements.txt"
        requirements_file.write_text(requirements_content)
        
        print("✅ Requirements file created")
    
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
        
        zip_filename = f"CoupaDownloads_Portable_Complete_{platform_name}.zip"
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
        print("🏗️ Building advanced portable package...")
        print("=" * 50)
        
        try:
            # Clean previous build
            self.clean_build()
            
            # Create directory structure
            self.create_directories()
            
            # Setup portable Python with dependencies
            if not self.setup_portable_python():
                print("❌ Failed to setup portable Python")
                return False
            
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
            
            # Create requirements file
            self.create_requirements_file()
            
            # Create ZIP package
            zip_path = self.create_zip_package()
            
            print("\n" + "=" * 50)
            print("🎉 Advanced portable package built successfully!")
            print("=" * 50)
            print(f"📦 Package: {zip_path}")
            print(f"📁 Size: {zip_path.stat().st_size / (1024*1024):.1f} MB")
            print("\n🚀 To use:")
            print("1. Extract the ZIP file")
            print("2. Edit data/input/input.csv with your PO numbers")
            print("3. Run the launcher script")
            print("\n✨ Features:")
            print("- Complete Python environment included")
            print("- All dependencies pre-installed")
            print("- Stable EdgeDriver included")
            print("- Zero installation required")
            
            return True
            
        except Exception as e:
            print(f"❌ Build failed: {e}")
            return False


def main():
    """Main function."""
    print("CoupaDownloads - Advanced Portable Package Builder")
    print("=" * 50)
    
    builder = AdvancedPortableBuilder()
    
    if builder.build():
        print("\n✅ Advanced build completed successfully!")
        return 0
    else:
        print("\n❌ Advanced build failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 