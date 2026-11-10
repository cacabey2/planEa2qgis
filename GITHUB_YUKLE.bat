@echo off
setlocal EnableExtensions EnableDelayedExpansion
title planEa2qgis - GitHub'a yukle

set "SAHIP=cacabey2"
set "DEPO=planEa2qgis"
set "REPO_URL=https://github.com/%SAHIP%/%DEPO%.git"
set "SAYFA=https://github.com/%SAHIP%/%DEPO%"
set "BRANCH=main"
set "KLASOR=%~dp0"
if "%KLASOR:~-1%"=="\" set "KLASOR=%KLASOR:~0,-1%"

echo Klasor : %KLASOR%
echo Depo   : %SAYFA%
echo.
where git >nul 2>&1 || (echo [HATA] git bulunamadi. https://git-scm.com & goto :son)
where curl >nul 2>&1 || (echo [HATA] curl bulunamadi. & goto :son)

rem ------------------------------------------------ 0) depo GitHub'da var mi
:kontrol
set "KOD="
for /f %%K in ('curl -s -o nul -w "%%{http_code}" "https://api.github.com/repos/%SAHIP%/%DEPO%"') do set "KOD=%%K"
if "%KOD%"=="200" goto :var
echo [0] %SAYFA% bulunamadi ^(HTTP %KOD%^).
echo     Depo once olusturulmali; QGIS sitesi de bu adresin HERKESE ACIK olmasini ister.
echo.
where gh >nul 2>&1
if not errorlevel 1 (
    echo     GitHub CLI ^(gh^) bulundu, depo olusturuluyor...
    gh repo create %SAHIP%/%DEPO% --public --description "NCZ imar planlarini e-Plan gosterimiyle QGIS'e aktaran eklenti" && goto :kontrol
    echo     gh ile olusturulamadi ^(gh auth login gerekebilir^); tarayici aciliyor.
)
echo     Tarayicida acilan sayfada:
echo       - Owner: %SAHIP%    Repository name: %DEPO%
echo       - Public secili olsun
echo       - README / .gitignore / license EKLEME ^(bos depo^)
echo       - "Create repository"
start "" "https://github.com/new?owner=%SAHIP%&name=%DEPO%&visibility=public"
echo.
echo     Depoyu olusturduktan sonra bu pencerede bir tusa bas...
pause >nul
goto :kontrol

:var
echo [0] Depo var: %SAYFA%
cd /d "%KLASOR%" || goto :son

if not exist ".git\" (
    echo [1] Git deposu olusturuluyor...
    git init || goto :hata
)
git symbolic-ref HEAD refs/heads/%BRANCH% >nul 2>&1
rem kimlik: git'te tanimli degilse GitHub'in gizli (noreply) adresi kullanilir
git config user.name  >nul 2>&1 || git config user.name  "%SAHIP%"
git config user.email >nul 2>&1 || git config user.email "%SAHIP%@users.noreply.github.com"

git remote get-url origin >nul 2>&1
if errorlevel 1 (git remote add origin "%REPO_URL%" || goto :hata) else (git remote set-url origin "%REPO_URL%")

echo [2] Dosyalar ekleniyor...
git add -A || goto :hata
set "MSG="
set /p "MSG=Commit mesaji (bos birakirsan tarih yazilir): "
if "!MSG!"=="" set "MSG=Guncelleme %DATE% %TIME:~0,5%"
git diff --cached --quiet && (echo Yeni degisiklik yok.) || (git commit -m "!MSG!" || goto :hata)

echo [3] GitHub'a gonderiliyor...
git push -u origin %BRANCH% || goto :hata
echo.
echo ===== TAMAM: %SAYFA% =====
goto :son
:hata
echo.
echo [HATA] Islem basarisiz. Yukaridaki mesaji kontrol edin.
echo  - "rejected / fetch first": depo bos degil ^(README eklenmis^). Bir kez:
echo      git pull origin %BRANCH% --allow-unrelated-histories
echo  - kimlik sorulursa GitHub'a %SAHIP% hesabiyla giris yapin.
:son
echo.
pause
endlocal
