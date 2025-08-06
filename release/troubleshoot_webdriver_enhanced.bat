@echo off
echo ========================================
echo    WebDriver Enhanced Troubleshooter
echo ========================================
echo.

echo 🔍 Comprehensive webdriver diagnostics...
echo.

:: Check network connectivity
echo 📡 Testing network connectivity...
ping -n 1 msedgedriver.azureedge.net >nul 2>&1
if errorlevel 1 (
    echo ❌ Network connectivity issue detected
    echo 💡 This explains why automatic download failed
    echo 📋 Use manual download method instead
) else (
    echo ✅ Network connectivity OK
)

echo.

:: Check if drivers directory exists
if not exist "drivers" (
    echo ❌ Drivers directory not found
    mkdir drivers
    echo ✅ Created drivers directory
)

:: Check for webdriver files
echo 🔍 Checking for webdriver files...
set "driver_count=0"

for %%f in (drivers\msedgedriver*.exe) do (
    echo ✅ Found: %%~nxf
    set /a driver_count+=1
)

if %driver_count%==0 (
    echo ❌ No webdriver files found
    echo.
    echo 📋 Manual download required:
    echo 1. Run: manual_webdriver_download.bat
    echo 2. Follow the step-by-step instructions
    echo 3. Download from Microsoft Edge Developer site
    echo.
    goto :manual_download
) else (
    echo ✅ Found %driver_count% webdriver file(s)
)

:: Check Edge browser
echo.
echo 🔍 Checking Microsoft Edge installation...
reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\EdgeUpdate" >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Microsoft Edge may not be installed
    echo 📥 Download from: https://www.microsoft.com/edge
) else (
    echo ✅ Microsoft Edge found
)

:: Check file permissions
echo.
echo 🔍 Checking file permissions...
for %%f in (drivers\msedgedriver*.exe) do (
    echo Testing: %%~nxf
    "%%f" --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Permission issue with %%~nxf
        echo 💡 Try running as Administrator
    ) else (
        echo ✅ %%~nxf permissions OK
    )
)

echo.
echo ========================================
echo    Troubleshooting Complete
echo ========================================
echo.
goto :end

:manual_download
echo.
echo 📋 Manual Download Instructions:
echo.
echo 1. OPEN BROWSER: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
echo 2. DOWNLOAD: Windows (64-bit) version
echo 3. EXTRACT: ZIP file to temporary location
echo 4. COPY: msedgedriver.exe to drivers\ directory
echo 5. RENAME: Create multiple versions as needed
echo 6. TEST: Run setup_windows.bat
echo.

:end
pause
