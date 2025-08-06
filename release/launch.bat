@echo off
echo.
echo ========================================
echo    CoupaDownloads Launcher
echo ========================================
echo.

:: Check if setup was run
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Setup not completed
    echo 💡 Please run setup_windows_enhanced.bat first
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Check for input file
if not exist "data\input\input.csv" (
    if not exist "data\input\input.xlsx" (
        echo ❌ No input file found
        echo 💡 Please place input.csv or input.xlsx in data\input\
        pause
        exit /b 1
    )
)

:: Launch application
echo 🚀 Starting CoupaDownloads...
cd src
python main.py

echo.
echo ✅ Application completed
pause
