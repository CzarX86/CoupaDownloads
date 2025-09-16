@echo off
echo ========================================
echo    Manual WebDriver Download Guide
echo ========================================
echo.

echo 🔍 This script helps you manually download webdrivers
echo    when automatic download fails due to network issues.
echo.

echo 📋 Step-by-step instructions:
echo.
echo 1. OPEN BROWSER and go to:
echo    https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
echo.
echo 2. CLICK "Download" for Windows (64-bit)
echo.
echo 3. EXTRACT the ZIP file
echo.
echo 4. COPY msedgedriver.exe to this drivers\ directory
echo.
echo 5. RENAME to create multiple versions:
echo    - msedgedriver.exe (default)
echo    - msedgedriver_120.exe (Edge 120)
echo    - msedgedriver_119.exe (Edge 119)
echo    - msedgedriver_118.exe (Edge 118)
echo.

echo 🚨 Common Issues and Solutions:
echo.
echo ❌ "Failed to resolve msedgedriver.azureedge.net"
echo    ✅ SOLUTION: Manual download (this guide)
echo.
echo ❌ Corporate firewall blocking downloads
echo    ✅ SOLUTION: Download from home/outside network
echo.
echo ❌ DNS resolution errors
echo    ✅ SOLUTION: Use manual download
echo.
echo ❌ Proxy configuration issues
echo    ✅ SOLUTION: Manual download bypasses proxy
echo.

echo 📁 Expected file structure:
echo    drivers\
echo    ├── msedgedriver.exe
echo    ├── msedgedriver_120.exe
echo    ├── msedgedriver_119.exe
echo    └── msedgedriver_118.exe
echo.

echo 🔧 After manual download:
echo    1. Run setup_windows_offline.bat
echo    2. Verify webdriver detection
echo    3. Test application startup
echo.

echo 💡 Alternative download sources:
echo    - https://github.com/microsoft/edge-selenium-tools/releases
echo    - https://chromedriver.chromium.org/downloads
echo    - https://selenium.dev/downloads/
echo.

pause
