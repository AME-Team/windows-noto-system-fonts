@echo off
title Clear Font Cache

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo  [ERROR] Please Run as Administrator!
    echo ========================================
    echo.
    pause
    exit /b 1
)

echo [1/3] Stopping Font Cache Service...
net stop "FontCache" /y >nul 2>&1
net stop "FontCache3.0.0.0" /y >nul 2>&1

echo [2/3] Deleting cache files...
del /f /s /q "%LOCALAPPDATA%\FontCache\*" >nul 2>&1
del /f /s /q "C:\Windows\ServiceProfiles\LocalService\AppData\Local\FontCache\*" >nul 2>&1

echo [3/3] Starting Font Cache Service...
net start "FontCache" >nul 2>&1

echo.
echo ========================================
echo  SUCCESS! Font cache cleared.
echo  Please reboot your PC now.
echo ========================================
pause
