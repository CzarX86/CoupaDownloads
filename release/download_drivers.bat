@echo off
echo ========================================
echo    EdgeDriver Download Script
echo ========================================
echo.

:: Create drivers directory
if not exist "drivers" mkdir drivers

:: Download EdgeDriver versions
echo 📥 Downloading EdgeDriver versions...

:: Edge 120
echo Downloading EdgeDriver 120.0.2210.91...
powershell -Command "Invoke-WebRequest -Uri 'https://msedgedriver.azureedge.net/120.0.2210.91/edgedriver_win64.zip' -OutFile 'drivers\edgedriver_120.zip'"
if exist "drivers\edgedriver_120.zip" (
    powershell -Command "Expand-Archive -Path 'drivers\edgedriver_120.zip' -DestinationPath 'drivers' -Force"
    ren "drivers\msedgedriver.exe" "msedgedriver_120.exe"
    del "drivers\edgedriver_120.zip"
    echo ✅ EdgeDriver 120 downloaded
)

:: Edge 119
echo Downloading EdgeDriver 119.0.2151.97...
powershell -Command "Invoke-WebRequest -Uri 'https://msedgedriver.azureedge.net/119.0.2151.97/edgedriver_win64.zip' -OutFile 'drivers\edgedriver_119.zip'"
if exist "drivers\edgedriver_119.zip" (
    powershell -Command "Expand-Archive -Path 'drivers\edgedriver_119.zip' -DestinationPath 'drivers' -Force"
    ren "drivers\msedgedriver.exe" "msedgedriver_119.exe"
    del "drivers\edgedriver_119.zip"
    echo ✅ EdgeDriver 119 downloaded
)

:: Edge 118
echo Downloading EdgeDriver 118.0.2088.76...
powershell -Command "Invoke-WebRequest -Uri 'https://msedgedriver.azureedge.net/118.0.2088.76/edgedriver_win64.zip' -OutFile 'drivers\edgedriver_118.zip'"
if exist "drivers\edgedriver_118.zip" (
    powershell -Command "Expand-Archive -Path 'drivers\edgedriver_118.zip' -DestinationPath 'drivers' -Force"
    ren "drivers\msedgedriver.exe" "msedgedriver_118.exe"
    del "drivers\edgedriver_118.zip"
    echo ✅ EdgeDriver 118 downloaded
)

:: Create default driver
if exist "drivers\msedgedriver_120.exe" (
    copy "drivers\msedgedriver_120.exe" "drivers\msedgedriver.exe"
    echo ✅ Default driver created
)

echo.
echo ========================================
echo    Driver Download Complete!
echo ========================================
echo.
echo 📁 Drivers downloaded to: drivers\
echo.
pause
