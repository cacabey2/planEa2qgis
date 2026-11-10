@echo off
setlocal EnableExtensions
title planEa2qgis - GitHub'a yukle

set "REPO_URL=https://github.com/cacabey2/planEa2qgis.git"
set "BRANCH=main"
set "KLASOR=%~dp0"
if "%KLASOR:~-1%"=="\" set "KLASOR=%KLASOR:~0,-1%"

echo Klasor : %KLASOR%
echo Depo   : %REPO_URL%
echo  (Depo GitHub'da once bos olarak olusturulmus olmali.)
echo.
where git >nul 2>&1 || (echo [HATA] git bulunamadi. https://git-scm.com & goto :son)
cd /d "%KLASOR%" || goto :son

if not exist ".git\" (
    echo [1] Git deposu olusturuluyor...
    git init || goto :hata
)
git symbolic-ref HEAD refs/heads/%BRANCH% >nul 2>&1
git config user.name  >nul 2>&1 || git config user.name  "cacabey2"
git config user.email >nul 2>&1 || git config user.email "cacalar0635@gmail.com"

git remote get-url origin >nul 2>&1
if errorlevel 1 (git remote add origin "%REPO_URL%" || goto :hata) else (git remote set-url origin "%REPO_URL%")

echo [2] Dosyalar ekleniyor...
git add -A || goto :hata
set "MSG="
set /p "MSG=Commit mesaji (bos birakirsan tarih yazilir): "
if "%MSG%"=="" set "MSG=Guncelleme %DATE% %TIME:~0,5%"
git diff --cached --quiet && (echo Yeni degisiklik yok.) || (git commit -m "%MSG%" || goto :hata)

echo [3] GitHub'a gonderiliyor...
git push -u origin %BRANCH% || goto :hata
echo.
echo ===== TAMAM: https://github.com/cacabey2/planEa2qgis =====
goto :son
:hata
echo.
echo [HATA] Islem basarisiz. Yukaridaki mesaji kontrol edin.
:son
echo.
pause
endlocal
