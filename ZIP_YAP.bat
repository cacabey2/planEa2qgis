@echo off
setlocal EnableExtensions
title planEa2qgis - zip paketi

set "KAYNAK=%~dp0"
if "%KAYNAK:~-1%"=="\" set "KAYNAK=%KAYNAK:~0,-1%"
set "SURUM="
for /f "tokens=2 delims==" %%V in ('findstr /b "version=" "%KAYNAK%\metadata.txt"') do set "SURUM=%%V"
set "GECICI=%TEMP%\planEa2qgis_zip"
set "ZIP=%KAYNAK%\cikti\planEa2qgis-%SURUM%.zip"

if exist "%GECICI%" rd /s /q "%GECICI%"
mkdir "%GECICI%\planEa2qgis"
robocopy "%KAYNAK%" "%GECICI%\planEa2qgis" /E /XD .git __pycache__ cikti /XF *.bat *.gpkg *.zip *_karsilastirma.png .gitignore /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (echo [HATA] Kopyalama basarisiz. & goto :son)

if not exist "%KAYNAK%\cikti" mkdir "%KAYNAK%\cikti"
if exist "%ZIP%" del "%ZIP%"
tar -a -c -f "%ZIP%" -C "%GECICI%" planEa2qgis
if errorlevel 1 (echo [HATA] tar ile zip olusturulamadi. & goto :son)
rd /s /q "%GECICI%"

echo.
echo ===== TAMAM: %ZIP% =====
echo QGIS ^> Eklentiler ^> Eklentileri Yonet ^> ZIP'ten Kur
:son
echo.
pause
endlocal
