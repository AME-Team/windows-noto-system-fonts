@echo off
title Restore All Original System Fonts from Backup

echo ========================================================
echo  Restoring All Original Fonts from Backup (*.bak)
echo ========================================================
echo.

set "FONTS=C:\Windows\Fonts"

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
    if exist "%FONTS%\%%f.bak" (
        copy /y "%FONTS%\%%f.bak" "%FONTS%\%%f" >nul
        echo   [RESTORED] %%f
    )
)

echo.
echo ========================================================
echo  Restore complete! Please reboot your PC.
echo ========================================================
pause
