@echo off
echo ========================================
echo    CoupaDownloads - Windows Setup (EdgeDriver 138)
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

:: Check for EdgeDriver 138
echo.
echo 🔍 Checking for EdgeDriver 138...
if exist "drivers\\msedgedriver.exe" (
    :: Check if it's a real executable or placeholder
    for %%A in ("drivers\\msedgedriver.exe") do set size=%%~zA
    if !size! LSS 1000000 (
        echo ⚠️ EdgeDriver 138 placeholder detected
        echo.
        echo 📋 Manual download required:
        echo 1. Visit: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
        echo 2. Download EdgeDriver 138 for Windows
        echo 3. Extract and replace drivers\\msedgedriver.exe
        echo.
        echo 💡 Expected file size: ~15-16 MB (not 57 bytes)
        echo.
        pause
        goto :manual_download
    ) else (
        echo ✅ Real EdgeDriver 138 found (!size! bytes)
        echo 🎉 No manual download required!
    )
) else (
    echo ❌ EdgeDriver 138 not found
    goto :manual_download
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
call venv\\Scripts\\activate.bat

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
if not exist "data\\input\\input.csv" (
    echo PO_NUMBER > "data\\input\\input.csv"
    echo PO15262984 >> "data\\input\\input.csv"
    echo PO15327452 >> "data\\input\\input.csv"
    echo PO15362783 >> "data\\input\\input.csv"
    echo ✅ Sample input file created
)

echo.
echo ========================================
echo    Setup Complete! 🎉
echo ========================================
echo.
echo 📋 Next steps:
echo 1. Edit data\\input\\input.csv with your PO numbers
echo 2. Run: python src\\main.py
echo.
echo 💡 This bundle includes the actual EdgeDriver 138
echo    No manual download required!
echo.
pause
goto :end

:manual_download
echo.
echo 📋 Manual EdgeDriver 138 Download Instructions:
echo.
echo 1. OPEN BROWSER: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
echo 2. DOWNLOAD: EdgeDriver 138 for Windows (64-bit)
echo 3. EXTRACT: ZIP file to temporary location
echo 4. COPY: msedgedriver.exe to drivers\\ directory
echo 5. VERIFY: File size should be ~15-16 MB
echo 6. RUN: setup_windows.bat again
echo.
echo 💡 Alternative sources:
echo    - https://github.com/microsoft/edge-selenium-tools/releases
echo    - https://selenium.dev/downloads/
echo.
pause

:end
