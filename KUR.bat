@echo off
setlocal EnableExtensions
title planEa2qgis - QGIS'e kur

set "KAYNAK=%~dp0"
if "%KAYNAK:~-1%"=="\" set "KAYNAK=%KAYNAK:~0,-1%"
set "EKLENTILER=%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins"
set "HEDEF=%EKLENTILER%\planEa2qgis"
set "ESKI=%EKLENTILER%\EplanNczimport"
set "YEDEK=%KAYNAK%\..\EplanNczimport_eski_yedek"

echo Kaynak : %KAYNAK%
echo Hedef  : %HEDEF%
echo.
tasklist /fi "imagename eq qgis-bin.exe" 2>nul | find /i "qgis-bin.exe" >nul && (
    echo [UYARI] QGIS acik. Kurulumdan sonra QGIS'i yeniden baslatin.
    echo.
)

if not exist "%ESKI%\" goto :kopyala
echo Eski "EplanNczimport" eklentisi bulundu. Iki eklenti birlikte gorunmesin diye
echo eklenti klasorunden cikarilip su klasore TASINABILIR (silinmez):
echo    %YEDEK%
set "CEVAP="
set /p "CEVAP=Tasinsin mi? (E/H): "
if /i not "%CEVAP%"=="E" goto :kopyala
if exist "%YEDEK%\" (
    echo [HATA] Yedek klasoru zaten var: %YEDEK%
    echo        Once onu kaldirin ya da adini degistirin.
    goto :son
)
robocopy "%ESKI%" "%YEDEK%" /E /MOVE /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (echo [HATA] Eski eklenti tasinamadi. & goto :son)
echo [1] Eski eklenti tasindi.

:kopyala
echo [2] planEa2qgis kopyalaniyor...
robocopy "%KAYNAK%" "%HEDEF%" /MIR /XD .git __pycache__ cikti /XF *.bat *.gpkg *.zip *_karsilastirma.png .gitignore /NFL /NDL /NJH /NJS /NP
if errorlevel 8 (echo [HATA] Kopyalama basarisiz. & goto :son)

echo.
echo ===== TAMAM =====
echo QGIS'i yeniden baslatin: Eklentiler ^> Eklentileri Yonet ^> planEa2qgis
:son
echo.
pause
endlocal
