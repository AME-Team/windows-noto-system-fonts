@echo off
title Restore Original MS Gothic Font

echo ========================================================
echo  Restoring Original MS Gothic Font from Backup
echo ========================================================
echo.

set "FONTS=C:\Windows\Fonts"

if not exist "%FONTS%\msgothic.ttc.bak" (
    echo [ERROR] Backup file %FONTS%\msgothic.ttc.bak not found!
    pause
    exit /b 1
)

echo Restoring msgothic.ttc from backup...
copy /y "%FONTS%\msgothic.ttc.bak" "%FONTS%\msgothic.ttc" >nul
if errorlevel 1 (
    echo [FAILED] Could not overwrite msgothic.ttc.
    echo Please run this script in Windows Recovery Command Prompt.
) else (
    echo [OK] msgothic.ttc restored successfully.
)

echo.
echo ========================================================
echo  Complete! Please reboot and run clear_cache.bat as Admin.
echo ========================================================
pause
