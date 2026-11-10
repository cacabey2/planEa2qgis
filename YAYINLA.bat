@echo off
setlocal EnableExtensions EnableDelayedExpansion
title planEa2qgis - QGIS eklenti deposuna yayinla

rem ---------------------------------------------------------------------------
rem  1) Paketi (zip) hazirlar   2) plugins.qgis.org'a jetonla (token) yukler
rem  Ilk yayin: eklenti sitede henuz yoksa zip tarayicidan bir kez elle yuklenir,
rem  sonraki surumler bu dosyayla tek tikla gider.
rem ---------------------------------------------------------------------------
set "PAKET=planEa2qgis"
set "KAYNAK=%~dp0"
if "%KAYNAK:~-1%"=="\" set "KAYNAK=%KAYNAK:~0,-1%"
set "JETON_KLASOR=%APPDATA%\planEa2qgis"
set "JETON_DOSYA=%JETON_KLASOR%\qgis_token.txt"
set "API=https://plugins.qgis.org/plugins/%PAKET%/version/add/api/"

set "SURUM="
for /f "tokens=2 delims==" %%V in ('findstr /b "version=" "%KAYNAK%\metadata.txt"') do set "SURUM=%%V"
if "%SURUM%"=="" (echo [HATA] metadata.txt icinde version= bulunamadi. & goto :son)
set "ZIP=%KAYNAK%\cikti\%PAKET%-%SURUM%.zip"

echo ==========================================================
echo  planEa2qgis %SURUM%  -^>  plugins.qgis.org
echo ==========================================================
echo.
echo  Kontrol listesi (site bunlari ister):
echo   - GitHub deposu herkese acik ve guncel (GITHUB_YUKLE.bat)
echo   - metadata.txt: surum yukseltildi, changelog yazildi
echo.
set "CEVAP="
set /p "CEVAP=GitHub'a once simdi gonderilsin mi? (E/H) [H]: "
if /i "%CEVAP%"=="E" call "%KAYNAK%\GITHUB_YUKLE.bat"

rem ---------------------------------------------------------------- 1) zip
echo.
echo [1] Paket hazirlaniyor...
set "GECICI=%TEMP%\planEa2qgis_yayin"
if exist "%GECICI%" rd /s /q "%GECICI%"
mkdir "%GECICI%\%PAKET%"
robocopy "%KAYNAK%" "%GECICI%\%PAKET%" /E /XD .git __pycache__ cikti .vscode .idea /XF *.bat *.gpkg *.zip *.pyc *.log *_karsilastirma.png .gitignore Thumbs.db /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (echo [HATA] Kopyalama basarisiz. & goto :son)
if not exist "%GECICI%\%PAKET%\LICENSE" (echo [HATA] LICENSE dosyasi yok; site lisanssiz paketi kabul etmez. & goto :son)
if not exist "%KAYNAK%\cikti" mkdir "%KAYNAK%\cikti"
if exist "%ZIP%" del "%ZIP%"
tar -a -c -f "%ZIP%" -C "%GECICI%" %PAKET%
if errorlevel 1 (echo [HATA] zip olusturulamadi. & goto :son)
rd /s /q "%GECICI%"
for %%Z in ("%ZIP%") do set "BOYUT=%%~zZ"
echo     %ZIP%  (%BOYUT% bayt)

rem ---------------------------------------------------------------- 2) jeton
set "JETON="
if exist "%JETON_DOSYA%" set /p JETON=<"%JETON_DOSYA%"
if "!JETON!"=="" (
    echo.
    echo [2] Kayitli jeton yok.
    echo.
    echo  ILK YAYIN ise: eklenti sitede henuz olmadigi icin jeton da yoktur.
    echo    a^) Tarayicida acilan sayfada OSGeo hesabinla giris yap
    echo    b^) "Upload a plugin" ile su zip'i sec:  %ZIP%
    echo    c^) Onaydan sonra eklenti sayfasinda "Tokens" bolumunden jeton olustur
    echo    d^) Bu dosyayi tekrar calistir ve jetonu yapistir
    echo.
    set "CEVAP="
    set /p "CEVAP=Jetonun var mi? Varsa yapistir, yoksa Enter (ilk yayin sayfasi acilir): "
    if "!CEVAP!"=="" (
        start "" "https://plugins.qgis.org/plugins/add/"
        explorer /select,"%ZIP%"
        goto :son
    )
    set "JETON=!CEVAP!"
    set "CEVAP="
    set /p "CEVAP=Jeton bu bilgisayarda saklansin mi? (%JETON_DOSYA%) (E/H) [E]: "
    if /i not "!CEVAP!"=="H" (
        if not exist "%JETON_KLASOR%" mkdir "%JETON_KLASOR%"
        >"%JETON_DOSYA%" echo !JETON!
        echo     Jeton kaydedildi. Silmek icin dosyayi silebilirsin.
    )
)

rem ---------------------------------------------------------------- 3) yukle
where curl >nul 2>&1 || (echo [HATA] curl bulunamadi ^(Windows 10 1803+ icinde gelir^). & goto :son)
echo.
set "HIZLI=false"
set "CEVAP="
set /p "CEVAP=Taramadan gecince onaysiz yayin (yalniz onay yetkin varsa) istensin mi? (E/H) [H]: "
if /i "!CEVAP!"=="E" set "HIZLI=true"

echo [3] Yukleniyor: %API%
set "YANIT=%TEMP%\planEa2qgis_yanit.txt"
set "KOD="
for /f %%K in ('curl -sS -X POST "%API%" -H "Authorization: Bearer !JETON!" -F "package=@%ZIP%" -F "auto_approve_after_scan=!HIZLI!" -o "%YANIT%" -w "%%{http_code}"') do set "KOD=%%K"
echo     HTTP %KOD%
if exist "%YANIT%" (type "%YANIT%" & echo.)

if "%KOD:~0,1%"=="2" (
    echo.
    echo ===== TAMAM: %SURUM% yuklendi =====
    echo Guvenlik taramasi ve onaydan sonra yayinda gorunur:
    echo https://plugins.qgis.org/plugins/%PAKET%/
    goto :son
)
echo.
if "%KOD%"=="401" echo [HATA] Jeton gecersiz ya da suresi dolmus. Yeni jeton olustur; eskisini silmek icin: del "%JETON_DOSYA%"
if "%KOD%"=="403" echo [HATA] Jetonun bu eklentiye yetkisi yok.
if "%KOD%"=="404" echo [HATA] Eklenti sitede bulunamadi: ilk surum once tarayicidan yuklenmeli (https://plugins.qgis.org/plugins/add/).
if "%KOD%"=="400" echo [HATA] Paket reddedildi: yukaridaki mesaja bak ^(ayni surum numarasi, eksik metadata, lisans...^).
if "%KOD%"=="" echo [HATA] Sunucuya ulasilamadi.

:son
echo.
pause
endlocal
