@echo off
setlocal enabledelayedexpansion

REM Check for drivers directory
if not exist "drivers\" (
    echo Creating drivers directory...
    mkdir drivers
)

echo.
echo ===== Manual Driver Setup Required =====
echo 1. Find your Edge version:
echo    - Open Edge browser
echo    - Go to edge://settings/help
echo    - Note the version number (e.g., 124.0.2478.80)
echo.
echo 2. Download matching driver from:
echo    https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
echo.
echo 3. Save driver in drivers directory as:
echo    edgedriver_[VERSION].exe
echo    Example: edgedriver_124.0.2478.80.exe
echo =======================================
echo.

echo Running Coupa downloader...
"c:\Program Files\Python313\python.exe" c:\MyScripts\CoupaDownloads\main.py

if errorlevel 1 (
    echo.
    echo ===== ERROR =====
    echo Script failed. Please check:
    echo 1. Driver setup instructions above
    echo 2. Error messages from the script
    echo =================
    pause
    exit /b 1
)

pause
