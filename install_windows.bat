@echo off
echo ========================================
echo    CoupaDownloads - Windows Installer
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo ✅ Python found
python --version

:: Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip is not available
    echo Please ensure pip is installed with Python
    pause
    exit /b 1
)

echo ✅ pip found

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo.
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)

:: Activate virtual environment
echo.
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

:: Upgrade pip
echo.
echo ⬆️ Upgrading pip...
python -m pip install --upgrade pip

:: Install requirements
echo.
echo 📦 Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

:: Create necessary directories
echo.
echo 📁 Creating necessary directories...
if not exist "data\input" mkdir "data\input"
if not exist "data\output" mkdir "data\output"
if not exist "data\backups" mkdir "data\backups"

:: Create sample input file if it doesn't exist
if not exist "data\input\input.csv" (
    echo.
    echo 📝 Creating sample input file...
    echo PO_NUMBER > "data\input\input.csv"
    echo PO15262984 >> "data\input\input.csv"
    echo PO15327452 >> "data\input\input.csv"
    echo PO15362783 >> "data\input\input.csv"
    echo ✅ Sample input file created
)

echo.
echo ========================================
echo    Installation Complete! 🎉
echo ========================================
echo.
echo 📋 Next steps:
echo 1. Edit data\input\input.csv with your PO numbers
echo 2. Run: python src\main.py
echo.
echo 💡 The tool will automatically:
echo    - Download the correct EdgeDriver
echo    - Open Microsoft Edge
echo    - Wait for you to log in to Coupa
echo    - Download attachments from your POs
echo.
echo 📁 Downloads will be saved to: %USERPROFILE%\Downloads\CoupaDownloads\
echo.
pause 