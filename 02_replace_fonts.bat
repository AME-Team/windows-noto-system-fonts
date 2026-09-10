@echo off
title Major System Fonts Replacement (Noto Font Family)

echo ========================================================
echo  Major System Fonts Replacement (Noto Font Family)
echo ========================================================
echo.

set "FONTS=C:\Windows\Fonts"
set "SRC=C:\Temp"
if not exist "%SRC%\msgothic.ttc" set "SRC=%~dp0"

echo Fonts Target : %FONTS%
echo Fonts Source : %SRC%
echo.

if not exist "%SRC%\msgothic.ttc" (
    echo [ERROR] Font files not found in %SRC%!
    pause
    exit /b 1
)

echo [1/3] Taking ownership of system fonts...
for %%f in (
    meiryo.ttc meiryob.ttc
    YuGothR.ttc YuGothM.ttc YuGothB.ttc YuGothL.ttc
    msgothic.ttc msmincho.ttc
    segoeui.ttf segoeuib.ttf segoeuii.ttf segoeuiz.ttf segoeuil.ttf segoeuisl.ttf seguisb.ttf
    arial.ttf arialbd.ttf ariali.ttf arialbi.ttf
    calibri.ttf calibrib.ttf calibrii.ttf calibriz.ttf calibril.ttf calibrili.ttf
    tahoma.ttf tahomabd.ttf
    verdana.ttf verdanab.ttf verdanai.ttf verdanaz.ttf
    consola.ttf consolab.ttf consolai.ttf consolaz.ttf
    CascadiaMono.ttf CascadiaCode.ttf
    cour.ttf courbd.ttf couri.ttf courbi.ttf
) do (
    takeown /f "%FONTS%\%%f" >nul 2>&1
    icacls "%FONTS%\%%f" /grant administrators:F >nul 2>&1
)

echo [2/3] Backing up original fonts to .bak...
for %%f in (
    meiryo.ttc meiryob.ttc
    YuGothR.ttc YuGothM.ttc YuGothB.ttc YuGothL.ttc
    msgothic.ttc msmincho.ttc
    segoeui.ttf segoeuib.ttf segoeuii.ttf segoeuiz.ttf segoeuil.ttf segoeuisl.ttf seguisb.ttf
    arial.ttf arialbd.ttf ariali.ttf arialbi.ttf
    calibri.ttf calibrib.ttf calibrii.ttf calibriz.ttf calibril.ttf calibrili.ttf
    tahoma.ttf tahomabd.ttf
    verdana.ttf verdanab.ttf verdanai.ttf verdanaz.ttf
    consola.ttf consolab.ttf consolai.ttf consolaz.ttf
    CascadiaMono.ttf CascadiaCode.ttf
    cour.ttf courbd.ttf couri.ttf courbi.ttf
) do (
    if not exist "%FONTS%\%%f.bak" if exist "%FONTS%\%%f" copy /y "%FONTS%\%%f" "%FONTS%\%%f.bak" >nul 2>&1
)

echo [3/3] Copying new fonts to C:\Windows\Fonts...
for %%f in (
    meiryo.ttc meiryob.ttc
    YuGothR.ttc YuGothM.ttc YuGothB.ttc YuGothL.ttc
    msgothic.ttc msmincho.ttc
    segoeui.ttf segoeuib.ttf segoeuii.ttf segoeuiz.ttf segoeuil.ttf segoeuisl.ttf seguisb.ttf
    arial.ttf arialbd.ttf ariali.ttf arialbi.ttf
    calibri.ttf calibrib.ttf calibrii.ttf calibriz.ttf calibril.ttf calibrili.ttf
    tahoma.ttf tahomabd.ttf
    verdana.ttf verdanab.ttf verdanai.ttf verdanaz.ttf
    consola.ttf consolab.ttf consolai.ttf consolaz.ttf
    CascadiaMono.ttf CascadiaCode.ttf
    cour.ttf courbd.ttf couri.ttf courbi.ttf
) do (
    if exist "%SRC%\%%f" (
        copy /y "%SRC%\%%f" "%FONTS%\%%f" >nul
        if errorlevel 1 (
            echo   [FAILED] %%f
        ) else (
            echo   [OK] %%f
        )
    )
)

echo.
echo ========================================================
echo  All operations completed!
echo  Type 'exit' to reboot, then run 03_clear_font_cache.bat as Admin.
echo ========================================================
pause
