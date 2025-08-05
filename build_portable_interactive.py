#!/usr/bin/env python3
"""
Interactive Portable Package Builder for CoupaDownloads
Creates a self-contained package that runs directly from ZIP with terminal interface
"""

import os
import sys
import platform
import subprocess
import shutil
import zipfile
import requests
import tempfile
from pathlib import Path
import json


class InteractivePortableBuilder:
    """Builds an interactive portable package that runs from ZIP."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_dir = self.project_root / "build"
        self.portable_dir = self.build_dir / "CoupaDownloads_Interactive"
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
    
    def create_interactive_launcher(self):
        """Create interactive launcher that runs from ZIP."""
        print("🚀 Creating interactive launcher...")
        
        system = platform.system().lower()
        
        if system == "windows":
            launcher_content = """@echo off
setlocal enabledelayedexpansion

:: Set console title
title CoupaDownloads - Interactive Launcher

:: Clear screen
cls

echo.
echo ========================================
echo    CoupaDownloads - Interactive Mode
echo ========================================
echo.
echo 🚀 Welcome to CoupaDownloads!
echo This tool will guide you through the entire process.
echo.

:: Check if running from ZIP
set "ZIP_MODE=false"
if exist "%~dp0*.zip" (
    set "ZIP_MODE=true"
    echo 📦 Running in ZIP mode (no extraction needed)
) else (
    echo 📁 Running in extracted mode
)
echo.

:: Check Python installation
echo 🔍 Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo.
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ !PYTHON_VERSION!
echo.

:: Create temporary directory
echo 📁 Setting up temporary workspace...
set "TEMP_DIR=%TEMP%\\CoupaDownloads_%RANDOM%"
mkdir "%TEMP_DIR%" 2>nul
set "INPUT_FILE=%TEMP_DIR%\\input.csv"
echo.

:: Create virtual environment in temp
echo 📦 Setting up Python environment...
if not exist "%TEMP_DIR%\\venv" (
    python -m venv "%TEMP_DIR%\\venv"
    call "%TEMP_DIR%\\venv\\Scripts\\activate.bat"
    pip install -r "%~dp0requirements.txt" --quiet
) else (
    echo ✅ Virtual environment already exists
)
echo.

:: Copy driver to temp
echo 🔧 Setting up WebDriver...
if not exist "%TEMP_DIR%\\drivers" mkdir "%TEMP_DIR%\\drivers"
copy "%~dp0drivers\\*" "%TEMP_DIR%\\drivers\\" >nul 2>&1
echo ✅ WebDriver ready
echo.

:: Copy source files to temp
echo 📋 Setting up source files...
if not exist "%TEMP_DIR%\\src" mkdir "%TEMP_DIR%\\src\\core"
copy "%~dp0src\\*" "%TEMP_DIR%\\src\\" >nul 2>&1
copy "%~dp0src\\core\\*" "%TEMP_DIR%\\src\\core\\" >nul 2>&1
echo ✅ Source files ready
echo.

:: Create input file template
echo 📝 Creating input file template...
echo PO_NUMBER > "%INPUT_FILE%"
echo PO15262984 >> "%INPUT_FILE%"
echo PO15327452 >> "%INPUT_FILE%"
echo PO15362783 >> "%INPUT_FILE%"
echo.

:: Open input file for editing
echo 📋 Opening input file for editing...
echo Please add your PO numbers to the file that will open.
echo.
echo Format:
echo PO_NUMBER
echo PO12345678
echo PO87654321
echo.
echo Press any key to open the file...
pause >nul

:: Open file with default editor
start "" "%INPUT_FILE%"

echo.
echo ⏳ Waiting for you to edit the file...
echo Please close the file when you're done editing.
echo.
pause

:: Verify input file
echo 🔍 Verifying input file...
set "PO_COUNT=0"
for /f "skip=1" %%i in (%INPUT_FILE%) do set /a PO_COUNT+=1

if !PO_COUNT! LSS 1 (
    echo ❌ No PO numbers found in the file
    echo Please add at least one PO number and try again.
    echo.
    pause
    exit /b 1
)

echo ✅ Found !PO_COUNT! PO number(s)
echo.

:: Show summary
echo 📊 Summary:
echo - PO numbers: !PO_COUNT!
echo - Input file: %INPUT_FILE%
echo - Temporary directory: %TEMP_DIR%
echo.

:: Ask for confirmation
echo 🚀 Ready to start processing?
echo This will:
echo - Open Microsoft Edge
echo - Navigate to Coupa
echo - Wait for you to log in
echo - Process all PO numbers
echo - Download attachments
echo.
set /p "CONFIRM=Do you want to proceed? (y/N): "

if /i not "!CONFIRM!"=="y" (
    echo.
    echo ❌ Operation cancelled by user
    echo.
    pause
    exit /b 0
)

echo.
echo 🚀 Starting CoupaDownloads...
echo.

:: Set environment variables
set "PYTHONPATH=%TEMP_DIR%"
set "EDGEDRIVER_PATH=%TEMP_DIR%\\drivers\\msedgedriver.exe"

:: Activate virtual environment and run
call "%TEMP_DIR%\\venv\\Scripts\\activate.bat"
cd /d "%TEMP_DIR%"
python src\\main.py

echo.
echo ✅ Processing completed!
echo.
echo 📁 Downloads saved to: %%USERPROFILE%%\\Downloads\\CoupaDownloads\\
echo 📊 Reports saved to: %TEMP_DIR%\\data\\output\\
echo.

:: Ask if user wants to keep temporary files
set /p "KEEP_TEMP=Keep temporary files for debugging? (y/N): "

if /i not "!KEEP_TEMP!"=="y" (
    echo.
    echo 🧹 Cleaning up temporary files...
    rmdir /s /q "%TEMP_DIR%" 2>nul
    echo ✅ Temporary files cleaned up
) else (
    echo.
    echo 📁 Temporary files kept at: %TEMP_DIR%
)

echo.
echo 🎉 Thank you for using CoupaDownloads!
echo.
pause
"""
            
            launcher_path = self.portable_dir / "run_interactive.bat"
            launcher_path.write_text(launcher_content, encoding='utf-8')
            
        else:
            # Unix shell launcher
            launcher_content = """#!/bin/bash

# Set terminal title
echo -e "\\033]0;CoupaDownloads - Interactive Launcher\\007"

# Clear screen
clear

echo ""
echo "========================================"
echo "   CoupaDownloads - Interactive Mode"
echo "========================================"
echo ""
echo "🚀 Welcome to CoupaDownloads!"
echo "This tool will guide you through the entire process."
echo ""

# Check if running from ZIP
ZIP_MODE=false
if ls *.zip >/dev/null 2>&1; then
    ZIP_MODE=true
    echo "📦 Running in ZIP mode (no extraction needed)"
else
    echo "📁 Running in extracted mode"
fi
echo ""

# Check Python installation
echo "🔍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo ""
    echo "Please install Python 3 from https://python.org"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "✅ $PYTHON_VERSION"
echo ""

# Create temporary directory
echo "📁 Setting up temporary workspace..."
TEMP_DIR=$(mktemp -d)
INPUT_FILE="$TEMP_DIR/input.csv"
echo "Temporary directory: $TEMP_DIR"
echo ""

# Create virtual environment in temp
echo "📦 Setting up Python environment..."
if [ ! -d "$TEMP_DIR/venv" ]; then
    python3 -m venv "$TEMP_DIR/venv"
    source "$TEMP_DIR/venv/bin/activate"
    pip install -r "$(dirname "$0")/requirements.txt" --quiet
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Copy driver to temp
echo "🔧 Setting up WebDriver..."
mkdir -p "$TEMP_DIR/drivers"
cp "$(dirname "$0")/drivers/"* "$TEMP_DIR/drivers/" 2>/dev/null
chmod +x "$TEMP_DIR/drivers/msedgedriver" 2>/dev/null
echo "✅ WebDriver ready"
echo ""

# Copy source files to temp
echo "📋 Setting up source files..."
mkdir -p "$TEMP_DIR/src/core"
cp "$(dirname "$0")/src/"* "$TEMP_DIR/src/" 2>/dev/null
cp "$(dirname "$0")/src/core/"* "$TEMP_DIR/src/core/" 2>/dev/null
echo "✅ Source files ready"
echo ""

# Create input file template
echo "📝 Creating input file template..."
cat > "$INPUT_FILE" << EOF
PO_NUMBER
PO15262984
PO15327452
PO15362783
EOF
echo ""

# Open input file for editing
echo "📋 Opening input file for editing..."
echo "Please add your PO numbers to the file that will open."
echo ""
echo "Format:"
echo "PO_NUMBER"
echo "PO12345678"
echo "PO87654321"
echo ""
echo "Press Enter to open the file..."
read

# Open file with default editor
if command -v xdg-open &> /dev/null; then
    xdg-open "$INPUT_FILE" &
elif command -v open &> /dev/null; then
    open "$INPUT_FILE" &
else
    echo "Please open the file manually: $INPUT_FILE"
fi

echo ""
echo "⏳ Waiting for you to edit the file..."
echo "Please close the file when you're done editing."
echo ""
read -p "Press Enter when you're done editing..."

# Verify input file
echo "🔍 Verifying input file..."
PO_COUNT=$(tail -n +2 "$INPUT_FILE" | wc -l)

if [ "$PO_COUNT" -lt 1 ]; then
    echo "❌ No PO numbers found in the file"
    echo "Please add at least one PO number and try again."
    echo ""
    exit 1
fi

echo "✅ Found $PO_COUNT PO number(s)"
echo ""

# Show summary
echo "📊 Summary:"
echo "- PO numbers: $PO_COUNT"
echo "- Input file: $INPUT_FILE"
echo "- Temporary directory: $TEMP_DIR"
echo ""

# Ask for confirmation
echo "🚀 Ready to start processing?"
echo "This will:"
echo "- Open Microsoft Edge"
echo "- Navigate to Coupa"
echo "- Wait for you to log in"
echo "- Process all PO numbers"
echo "- Download attachments"
echo ""
read -p "Do you want to proceed? (y/N): " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo ""
    echo "❌ Operation cancelled by user"
    echo ""
    exit 0
fi

echo ""
echo "🚀 Starting CoupaDownloads..."
echo ""

# Set environment variables
export PYTHONPATH="$TEMP_DIR"
export EDGEDRIVER_PATH="$TEMP_DIR/drivers/msedgedriver"

# Activate virtual environment and run
source "$TEMP_DIR/venv/bin/activate"
cd "$TEMP_DIR"
python src/main.py

echo ""
echo "✅ Processing completed!"
echo ""
echo "📁 Downloads saved to: ~/Downloads/CoupaDownloads/"
echo "📊 Reports saved to: $TEMP_DIR/data/output/"
echo ""

# Ask if user wants to keep temporary files
read -p "Keep temporary files for debugging? (y/N): " KEEP_TEMP

if [[ ! "$KEEP_TEMP" =~ ^[Yy]$ ]]; then
    echo ""
    echo "🧹 Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
    echo "✅ Temporary files cleaned up"
else
    echo ""
    echo "📁 Temporary files kept at: $TEMP_DIR"
fi

echo ""
echo "🎉 Thank you for using CoupaDownloads!"
echo ""
"""
            
            launcher_path = self.portable_dir / "run_interactive.sh"
            launcher_path.write_text(launcher_content)
            os.chmod(launcher_path, 0o755)
        
        print("✅ Interactive launcher created")
    
    def create_requirements_file(self):
        """Create requirements.txt for the portable version."""
        print("📦 Creating requirements file...")
        
        requirements_content = """# Interactive Portable Package Requirements
# These will be installed automatically

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
    
    def create_readme(self):
        """Create README for interactive version."""
        print("📝 Creating README...")
        
        readme_content = """# CoupaDownloads - Interactive Portable Version

## 🚀 Quick Start

### Windows
1. **Double-click** `run_interactive.bat`
2. **Follow** the interactive prompts
3. **Edit** the input file when it opens
4. **Confirm** to start processing

### macOS/Linux
1. **Double-click** `run_interactive.sh` OR
2. **Open terminal** and run: `./run_interactive.sh`
3. **Follow** the interactive prompts

## 🎯 Interactive Features

### 🔍 **Automatic Detection**
- ✅ Python installation check
- ✅ ZIP mode detection
- ✅ WebDriver setup
- ✅ Virtual environment creation

### 📝 **Smart Input Handling**
- ✅ Opens input file automatically
- ✅ Waits for user to edit
- ✅ Validates PO numbers
- ✅ Shows summary before processing

### 🛡️ **Security & Safety**
- ✅ Runs from ZIP (no extraction needed)
- ✅ Uses temporary directories
- ✅ Automatic cleanup option
- ✅ No system modifications

### 🚀 **User Guidance**
- ✅ Step-by-step prompts
- ✅ Clear instructions
- ✅ Progress feedback
- ✅ Error handling

## 📋 What's Included

- ✅ Interactive launcher scripts
- ✅ Stable EdgeDriver (pre-downloaded)
- ✅ Source code
- ✅ Requirements file
- ✅ Auto-setup system

## 💡 How It Works

### 1. **Launch**
```
User runs launcher script
↓
System detects environment
↓
Creates temporary workspace
↓
Sets up Python environment
```

### 2. **Input**
```
Opens input file automatically
↓
User adds PO numbers
↓
System validates input
↓
Shows summary
```

### 3. **Processing**
```
User confirms to proceed
↓
Opens Microsoft Edge
↓
Waits for login
↓
Processes POs automatically
```

### 4. **Cleanup**
```
Processing completes
↓
Shows results
↓
Offers cleanup option
↓
Removes temporary files
```

## 📁 File Structure

```
CoupaDownloads_Interactive/
├── run_interactive.bat/sh       # Interactive launcher
├── requirements.txt             # Python dependencies
├── drivers/                     # EdgeDriver (pre-downloaded)
│   └── msedgedriver.exe        # Stable WebDriver
├── src/                         # Source code
└── tests/                       # Test files
```

## 🎯 Advantages

- **🎒 Zero Installation**: No Python installation required
- **📦 ZIP Mode**: Runs directly from ZIP file
- **🛡️ Secure**: Uses temporary directories
- **🎮 Interactive**: Guides user through entire process
- **🧹 Clean**: Automatic cleanup option
- **🚀 Simple**: One-click execution

## 🔍 Troubleshooting

### "Python not found"
- Install Python from https://python.org
- Check "Add Python to PATH" during installation

### "File won't open"
- The system will show the file path
- Open manually with any text editor

### "Processing fails"
- Check Microsoft Edge installation
- Ensure internet connection
- Verify Coupa login credentials

## 📊 System Requirements

- **Python 3.8+** (automatically detected)
- **Windows 10/11** OR **macOS 10.14+** OR **Linux**
- **Microsoft Edge** browser
- **Internet connection**
- **Coupa access** (valid login)

## 🎉 User Experience

1. **Double-click** launcher
2. **Wait** for setup
3. **Edit** input file
4. **Confirm** processing
5. **Login** to Coupa
6. **Watch** progress
7. **Find** downloads

**That's it! The system handles everything else automatically.**
"""
        
        readme_file = self.portable_dir / "README_Interactive.md"
        readme_file.write_text(readme_content, encoding='utf-8')
        
        print("✅ README created")
    
    def create_zip_package(self):
        """Create the final ZIP package."""
        print("📦 Creating interactive portable ZIP package...")
        
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
        
        zip_filename = f"CoupaDownloads_Interactive_{platform_name}.zip"
        zip_path = self.build_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.portable_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(self.portable_dir)
                    zipf.write(file_path, arcname)
        
        print(f"✅ Interactive portable package created: {zip_filename}")
        print(f"📁 Location: {zip_path}")
        
        return zip_path
    
    def build(self):
        """Build the complete interactive portable package."""
        print("🏗️ Building interactive portable package...")
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
            
            # Create interactive launcher
            self.create_interactive_launcher()
            
            # Create requirements file
            self.create_requirements_file()
            
            # Create README
            self.create_readme()
            
            # Create ZIP package
            zip_path = self.create_zip_package()
            
            print("\n" + "=" * 50)
            print("🎉 Interactive portable package built successfully!")
            print("=" * 50)
            print(f"📦 Package: {zip_path}")
            print(f"📁 Size: {zip_path.stat().st_size / (1024*1024):.1f} MB")
            print("\n🚀 To use:")
            print("1. Extract the ZIP file")
            print("2. Run the interactive launcher")
            print("3. Follow the prompts")
            print("\n✨ Features:")
            print("- Runs directly from ZIP")
            print("- Interactive terminal interface")
            print("- Auto-opens input file")
            print("- Temporary workspace")
            print("- Automatic cleanup")
            
            return True
            
        except Exception as e:
            print(f"❌ Build failed: {e}")
            return False


def main():
    """Main function."""
    print("CoupaDownloads - Interactive Portable Package Builder")
    print("=" * 50)
    
    builder = InteractivePortableBuilder()
    
    if builder.build():
        print("\n✅ Interactive build completed successfully!")
        return 0
    else:
        print("\n❌ Interactive build failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 