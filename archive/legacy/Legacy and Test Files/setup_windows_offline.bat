@echo off
echo ========================================
echo    CoupaDownloads - Offline Windows Setup
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

:: Check for included webdrivers
echo.
echo 🔍 Checking for included webdrivers...
set "driver_found="

:: Check for specific versions
for %%v in (120 119 118) do (
    if exist "drivers\msedgedriver_%%v.exe" (
        echo ✅ Found msedgedriver_%%v.exe
        set "driver_found=1"
    )
)

:: Check for default driver
if exist "drivers\msedgedriver.exe" (
    echo ✅ Found default msedgedriver.exe
    set "driver_found=1"
)

if not defined driver_found (
    echo ❌ No webdrivers found in bundle
    echo.
    echo 📋 Manual webdriver setup required:
    echo 1. Download EdgeDriver from: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
    echo 2. Extract and rename to: msedgedriver.exe
    echo 3. Place in the drivers\ directory
    echo.
    echo 💡 This offline bundle should include webdrivers
    echo    Contact support if drivers are missing
    echo.
    pause
    exit /b 1
)

:: Create default driver if needed
if not exist "drivers\msedgedriver.exe" (
    if exist "drivers\msedgedriver_120.exe" (
        copy "drivers\msedgedriver_120.exe" "drivers\msedgedriver.exe"
        echo ✅ Default driver created from version 120
    ) else if exist "drivers\msedgedriver_119.exe" (
        copy "drivers\msedgedriver_119.exe" "drivers\msedgedriver.exe"
        echo ✅ Default driver created from version 119
    ) else if exist "drivers\msedgedriver_118.exe" (
        copy "drivers\msedgedriver_118.exe" "drivers\msedgedriver.exe"
        echo ✅ Default driver created from version 118
    )
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

:: Verify webdriver setup
echo.
echo 🔍 Verifying webdriver setup...
if exist "drivers\msedgedriver.exe" (
    echo ✅ Webdriver ready for offline use
) else (
    echo ❌ Webdriver not found - setup incomplete
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Offline Setup Complete! 🎉
echo ========================================
echo.
echo 📋 Next steps:
echo 1. Edit data\input\input.csv with your PO numbers
echo 2. Run: python src\main.py
echo.
echo 💡 This offline release includes:
echo    - Pre-downloaded webdrivers (no internet required)
echo    - All Python dependencies
echo    - Ready-to-use configuration
echo    - No network dependencies for webdriver setup
echo.
echo 🔧 If you encounter issues:
echo    - Check drivers\README.md for troubleshooting
echo    - Ensure Microsoft Edge is installed
echo    - Run as Administrator if needed
echo.
pause
