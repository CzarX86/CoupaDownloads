@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo    CoupaDownloads Windows Setup
echo ========================================
echo.

:: Check for administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  This setup requires administrator privileges
    echo 💡 Right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo ✅ Administrator privileges confirmed

:: Check Python installation
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Python not found in PATH
    echo 💡 Please install Python 3.8+ and add to PATH
    echo 📥 Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python version: %PYTHON_VERSION%

:: Check for virtual environment
if exist "venv\Scripts\activate.bat" (
    echo ✅ Virtual environment found
    call venv\Scripts\activate.bat
    echo ✅ Virtual environment activated
) else (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if %errorLevel% neq 0 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    echo ✅ Virtual environment created and activated
)

:: Install dependencies
echo 📦 Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed

:: Validate webdriver
echo 🔍 Validating webdriver...
if exist "drivers\msedgedriver_x64_138.exe" (
    for %%A in ("drivers\msedgedriver_x64_138.exe") do set size=%%~zA
    if !size! LSS 15000000 (
        echo ❌ WebDriver appears to be corrupted or incomplete
        echo 💡 Expected size: ~18MB, Found: !size! bytes
        pause
        exit /b 1
    ) else (
        echo ✅ WebDriver validated (!size! bytes)
    )
) else (
    echo ❌ WebDriver not found: drivers\msedgedriver_x64_138.exe
    pause
    exit /b 1
)

:: Test application startup
echo 🧪 Testing application startup...
cd src
python main.py --test-mode
if %errorLevel% neq 0 (
    echo ❌ Application test failed
    pause
    exit /b 1
)
cd ..

echo.
echo ========================================
echo    ✅ Setup completed successfully!
echo ========================================
echo.
echo 🚀 To run the application:
echo    1. cd src
echo    2. python main.py
echo.
echo 📁 Input files: data\input\
echo 📁 Output files: data\output\
echo.
pause
