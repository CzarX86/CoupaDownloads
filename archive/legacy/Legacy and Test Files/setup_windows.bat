@echo off
echo ========================================
echo    CoupaDownloads - Windows Setup
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo.
    echo 📥 Download Python from: https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo ✅ Python found
python --version

:: Download drivers if needed
if not exist "drivers\msedgedriver.exe" (
    echo.
    echo 🔧 Downloading EdgeDrivers...
    call download_drivers.bat
)

:: Create virtual environment
echo.
echo 📦 Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ❌ Failed to create virtual environment
    pause
    exit /b 1
)

:: Activate virtual environment
echo.
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo.
echo 📦 Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

:: Create sample input file
echo.
echo 📝 Creating sample input file...
if not exist "data\input\input.csv" (
    echo PO_NUMBER > "data\input\input.csv"
    echo PO15262984 >> "data\input\input.csv"
    echo PO15327452 >> "data\input\input.csv"
    echo PO15362783 >> "data\input\input.csv"
    echo ✅ Sample input file created
)

echo.
echo ========================================
echo    Setup Complete! 🎉
echo ========================================
echo.
echo 📋 Next steps:
echo 1. Edit data\input\input.csv with your PO numbers
echo 2. Run: python src\main.py
echo.
echo 💡 This release includes:
echo    - Automatic EdgeDriver download
echo    - Enhanced driver management
echo    - All Python dependencies
echo    - Ready-to-use configuration
echo.
pause
