@echo off
chcp 65001 >nul
title Broker Yonetim Paneli
color 0A
cd /d "%~dp0"

set SSH_KEY=C:\Users\kadir.kumas\.ssh\broker-bot.key
set SSH_USER=ubuntu
set SSH_IP=92.5.133.137
set SSH_CMD=ssh -i %SSH_KEY% %SSH_USER%@%SSH_IP%
set LOCAL_DIR=C:\Users\kadir.kumas\Desktop\Broker_System
set WIN_TITLE=LOCAL BROKER - Port 8000

REM Cloud durum cache
set CLOUD_CACHE_FILE=%TEMP%\broker_cloud_st_%RANDOM%_%RANDOM%.txt
set CLOUD_CACHE_TIME=0
set CLOUD_CACHED_ST=bilinmiyor

:MENU
cls

REM ---- Cloud durum (20 sn cache) ----
call :GET_CURRENT_TIME
set NOW=%CURRENT_TIME%
set /a DIFF=%NOW% - %CLOUD_CACHE_TIME%
if %DIFF% LSS 0 set DIFF=999
if %DIFF% GEQ 20 (
    "%SSH_CMD%" "sudo systemctl is-active broker-bot" > "%CLOUD_CACHE_FILE%" 2>nul
    if exist "%CLOUD_CACHE_FILE%" (
        set /p CLOUD_CACHED_ST=<"%CLOUD_CACHE_FILE%"
        del "%CLOUD_CACHE_FILE%" >nul 2>&1
    )
    if "%CLOUD_CACHED_ST%"=="" set CLOUD_CACHED_ST=bilinmiyor
    set CLOUD_CACHE_TIME=%NOW%
)
set CLOUD_ST=%CLOUD_CACHED_ST%

REM ---- Local durum (port kesin kontrol) ----
set LOCAL_ST=KAPALI
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
if not errorlevel 1 set LOCAL_ST=AKTIF

set MARK2=
set WARN_BOTH=
if /i "%CLOUD_ST%"=="active" if /i not "%LOCAL_ST%"=="AKTIF" set MARK2=   *** AKTIF ***
if /i "%CLOUD_ST%"=="active" if /i "%LOCAL_ST%"=="AKTIF" set WARN_BOTH=  [!!] IKI ORTAM DA AKTIF - TEHLIKE !!

echo.
echo  =====================================================
echo    BROKER YONETIM PANELI
echo  =====================================================
echo.
echo    CLOUD : %SSH_IP%   [durum: %CLOUD_ST%]
echo    LOCAL : %LOCAL_DIR%   [durum: %LOCAL_ST%]
if not "%WARN_BOTH%"=="" echo.%WARN_BOTH%
echo.
echo  -----------------------------------------------------
echo    --- MOD DEGISTIR ---
echo    [1]  LOCAL Moduna Gec
echo    [2]  CLOUD Moduna Gec%MARK2%
echo    [3]  TUMUNU DURDUR
echo.
echo    --- CLOUD BOT ---
echo    [11] Cloud Bot DURDUR
echo    [12] Cloud Bot YENIDEN BASLAT
echo    [13] Cloud Canli Log
echo    [14] Cloud Son 50 Log
echo    [15] Cloud Arayuzu Ac
echo    [16] Cloud SSH
echo.
echo    --- LOCAL ---
echo    [21] Local Backend DURDUR
echo    [22] Local Backend Durum
echo    [23] Local Arayuzu Ac
echo.
echo    --- SENKRONIZASYON ---
echo    [31] Local -^> Cloud Dosya Gonder
echo.
echo    --- DB TEMIZLE (DIKKAT!) ---
echo    [41] Local DB TEMIZLE
echo    [42] Cloud DB TEMIZLE
echo.
echo    --- CIKIS ---
echo    [0]  Cikis
echo  -----------------------------------------------------
echo.
set /p secim="  Secim: "

REM Trim bosluk
for /f "tokens=* delims= " %%a in ("%secim%") do set secim=%%a

if "%secim%"=="1"  goto GEC_LOCAL
if "%secim%"=="2"  goto GEC_CLOUD
if "%secim%"=="3"  goto TUM_DURDUR
if "%secim%"=="11" goto CLOUD_DURDUR
if "%secim%"=="12" goto CLOUD_YENIDEN
if "%secim%"=="13" goto CLOUD_LOG
if "%secim%"=="14" goto CLOUD_LOG_50
if "%secim%"=="15" goto CLOUD_ARAYUZ
if "%secim%"=="16" goto CLOUD_SSH
if "%secim%"=="21" goto LOCAL_DURDUR
if "%secim%"=="22" goto LOCAL_DURUM
if "%secim%"=="23" goto LOCAL_ARAYUZ
if "%secim%"=="31" goto SYNC_TO_CLOUD
if "%secim%"=="41" goto DB_LOCAL_RESET
if "%secim%"=="42" goto DB_CLOUD_RESET
if "%secim%"=="0"  goto CIKIS

echo.
echo  !! Gecersiz secim: %secim%
timeout /t 2 >nul
goto MENU


REM ================================================
REM  YARDIMCI: ZAMAN AL (epoch benzeri)
REM ================================================
:GET_CURRENT_TIME
for /f "tokens=1-4 delims=:., " %%a in ("%TIME%") do (
    set /a CURRENT_TIME=%%a * 3600 + %%b * 60 + %%c
)
exit /b 0


REM ================================================
REM  YARDIMCI: LOCAL BACKEND DURDUR
REM ================================================
:KILL_LOCAL_BACKEND
REM 1) Pencere basligi ile dene (tam eslesme)
taskkill /F /FI "WINDOWTITLE eq %WIN_TITLE%" /T >nul 2>&1

REM 2) Port 8000'deki process'leri oldur (sadece python.exe)
set KILLED=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
    tasklist /FI "PID eq %%a" 2>nul | findstr /i "python.exe" >nul
    if not errorlevel 1 (
        taskkill /F /T /PID %%a >nul 2>&1
        set KILLED=1
    )
)
exit /b %KILLED%


REM ================================================
REM  1 - LOCAL MODUNA GEC
REM ================================================
:GEC_LOCAL
cls
echo.
echo  LOCAL MODUNA GECILIYOR
echo.
echo  [1/2] Cloud bot durduruluyor...
%SSH_CMD% "sudo systemctl stop broker-bot" >nul 2>&1
echo        Cloud durduruldu.
echo.
echo  [2/2] Local backend baslatiliyor...
echo.

call :KILL_LOCAL_BACKEND

start "%WIN_TITLE%" cmd /k "title %WIN_TITLE% && cd /d %LOCAL_DIR% && echo. && echo Local Broker Backend baslatiliyor... && echo. && py -m uvicorn backend.main:app --reload"

echo.
echo  [+] LOCAL MODU AKTIF
echo.
timeout /t 4 >nul
goto MENU


REM ================================================
REM  2 - CLOUD MODUNA GEC
REM ================================================
:GEC_CLOUD
cls
echo.
echo  CLOUD MODUNA GECILIYOR
echo.
echo  [1/2] Local backend durduruluyor...

call :KILL_LOCAL_BACKEND
echo        Local durduruldu.

echo.
echo  [2/2] Cloud bot baslatiliyor...
%SSH_CMD% "sudo systemctl start broker-bot && sleep 3 && sudo systemctl status broker-bot --no-pager | head -8"
echo.
echo  [+] CLOUD MODU AKTIF
echo.
pause
goto MENU


REM ================================================
REM  3 - TUMUNU DURDUR
REM ================================================
:TUM_DURDUR
cls
echo.
echo  TUM SUNUCULARI DURDURULUYOR
echo.
%SSH_CMD% "sudo systemctl stop broker-bot" >nul 2>&1
echo        Cloud DURDURULDU.
echo.

call :KILL_LOCAL_BACKEND
if errorlevel 1 (echo        Local DURDURULDU.) else (echo        Local zaten kapali.)
echo.
echo  [+] Her iki bot da durduruldu.
echo.
pause
goto MENU


REM ================================================
REM  11 - CLOUD BOT DURDUR
REM ================================================
:CLOUD_DURDUR
cls
echo.
echo  CLOUD BOT DURDURULUYOR
echo.
%SSH_CMD% "sudo systemctl stop broker-bot && sudo systemctl status broker-bot --no-pager | head -8"
pause
goto MENU


REM ================================================
REM  12 - CLOUD BOT YENIDEN BASLAT
REM ================================================
:CLOUD_YENIDEN
cls
echo.
echo  CLOUD BOT YENIDEN BASLATILIYOR
echo.
%SSH_CMD% "sudo systemctl restart broker-bot && sleep 2 && sudo systemctl status broker-bot --no-pager | head -8"
pause
goto MENU


REM ================================================
REM  13 - CLOUD CANLI LOG
REM ================================================
:CLOUD_LOG
cls
echo  CANLI LOG (durdurmak icin Ctrl+C)
echo.
%SSH_CMD% "sudo journalctl -u broker-bot -f"
pause
goto MENU


REM ================================================
REM  14 - CLOUD SON 50 LOG
REM ================================================
:CLOUD_LOG_50
cls
echo  CLOUD SON 50 LOG
echo.
%SSH_CMD% "sudo journalctl -u broker-bot -n 50 --no-pager"
pause
goto MENU


REM ================================================
REM  15 - CLOUD ARAYUZU AC
REM ================================================
:CLOUD_ARAYUZ
start http://%SSH_IP%:8000
goto MENU


REM ================================================
REM  16 - CLOUD SSH
REM ================================================
:CLOUD_SSH
cls
echo  SSH baglantisi (cikmak icin: exit)
echo.
%SSH_CMD%
pause
goto MENU


REM ================================================
REM  21 - LOCAL BACKEND DURDUR
REM ================================================
:LOCAL_DURDUR
cls
echo.
echo  LOCAL BACKEND DURDURULUYOR
echo.

call :KILL_LOCAL_BACKEND
if errorlevel 1 (echo  Local durduruldu.) else (echo  Local zaten kapali.)
pause
goto MENU


REM ================================================
REM  22 - LOCAL BACKEND DURUM
REM ================================================
:LOCAL_DURUM
cls
echo.
echo  LOCAL BACKEND DURUMU
echo.
netstat -ano | findstr /R /C:":8000 .*LISTENING"
if errorlevel 1 (echo  [X] Local KAPALI) else (echo  [+] Local ACIK - Port 8000 dinleniyor)
pause
goto MENU


REM ================================================
REM  23 - LOCAL ARAYUZU AC
REM ================================================
:LOCAL_ARAYUZ
start http://127.0.0.1:8000
goto MENU


REM ================================================
REM  31 - SYNC TO CLOUD
REM ================================================
:SYNC_TO_CLOUD
cls
echo.
echo  LOCAL -^> CLOUD DOSYA SENKRONIZASYONU
echo.
set SYNC_ERR=0

echo  [1/4] Frontend dosyalari...
scp -i "%SSH_KEY%" ^
    "%LOCAL_DIR%\frontend\index.html" ^
    "%LOCAL_DIR%\frontend\chart.js" ^
    "%LOCAL_DIR%\frontend\style.css" ^
    "%LOCAL_DIR%\frontend\zoom_controls.js" ^
    "%SSH_USER%@%SSH_IP%:~/Broker_System/frontend/"
if errorlevel 1 (echo     [X] Frontend scp HATA! & set SYNC_ERR=1)

echo.
echo  [2/4] Mobile dosyalari...
scp -i "%SSH_KEY%" ^
    "%LOCAL_DIR%\frontend\mobile\index.html" ^
    "%LOCAL_DIR%\frontend\mobile\mobile.css" ^
    "%LOCAL_DIR%\frontend\mobile\mobile.js" ^
    "%SSH_USER%@%SSH_IP%:~/Broker_System/frontend/mobile/"
if errorlevel 1 (echo     [X] Mobile scp HATA! & set SYNC_ERR=1)

echo.
echo  [3/4] Backend dosyalari...
scp -i "%SSH_KEY%" ^
    "%LOCAL_DIR%\backend\main.py" ^
    "%LOCAL_DIR%\backend\strategy_engine.py" ^
    "%LOCAL_DIR%\backend\position_manager.py" ^
    "%LOCAL_DIR%\backend\order_manager.py" ^
    "%LOCAL_DIR%\backend\indicators.py" ^
    "%LOCAL_DIR%\backend\database.py" ^
    "%LOCAL_DIR%\backend\backtest_engine.py" ^
    "%LOCAL_DIR%\backend\telegram_notifier.py" ^
    "%LOCAL_DIR%\backend\bot_config.json" ^
    "%LOCAL_DIR%\backend\bot_config.default.json" ^
    "%SSH_USER%@%SSH_IP%:~/Broker_System/backend/"
if errorlevel 1 (echo     [X] Backend scp HATA! & set SYNC_ERR=1)

echo.
echo  [4/4] Strateji dosyalari...
scp -i "%SSH_KEY%" ^
    "%LOCAL_DIR%\backend\strategies\*.py" ^
    "%SSH_USER%@%SSH_IP%:~/Broker_System/backend/strategies/"
if errorlevel 1 (echo     [X] Strateji scp HATA! & set SYNC_ERR=1)

echo.
if %SYNC_ERR%==1 (
    echo  [X] SENKRONIZASYON HATALARLA TAMAMLANDI!
    echo      Yukaridaki [X] satirlarini kontrol et.
) else (
    echo  [+] SENKRONIZASYON TAMAMLANDI
    echo.
    echo   Yeni dosyalari AKTIF ETMEK icin: [12] Cloud Bot Yeniden Baslat
)
echo.
pause
goto MENU


REM ================================================
REM  41 - LOCAL DB TEMIZLE
REM ================================================
:DB_LOCAL_RESET
cls
echo.
echo  LOCAL DB TEMIZLE
echo.
echo  DIKKAT: Local bot CALISIYOR olabilir!
echo          Once [21] ile durdurun.
echo.
set /p onay="  Devam edilsin mi? (E/H): "
if /i not "%onay%"=="E" goto MENU

if not exist "%LOCAL_DIR%\Patch\yeni\db_check.py" (
    echo.
    echo [X] HATA: db_check.py bulunamadi!
    echo     Beklenen: %LOCAL_DIR%\Patch\yeni\db_check.py
    pause
    goto MENU
)

cd /d %LOCAL_DIR%
py Patch\yeni\db_check.py local reset
if errorlevel 1 (
    echo.
    echo [X] db_check.py HATA ile cikti!
)
echo.
pause
goto MENU


REM ================================================
REM  42 - CLOUD DB TEMIZLE
REM ================================================
:DB_CLOUD_RESET
cls
echo.
echo  CLOUD DB TEMIZLE
echo.
echo  DIKKAT: Cloud bot CALISIYOR olabilir!
echo          Once [11] ile durdurun.
echo.
set /p onay="  Devam edilsin mi? (E/H): "
if /i not "%onay%"=="E" goto MENU

if not exist "%LOCAL_DIR%\Patch\yeni\db_check.py" (
    echo.
    echo [X] HATA: db_check.py bulunamadi!
    pause
    goto MENU
)

cd /d %LOCAL_DIR%
py Patch\yeni\db_check.py cloud reset
if errorlevel 1 (
    echo.
    echo [X] db_check.py HATA ile cikti!
)
echo.
pause
goto MENU


REM ================================================
REM  CIKIS
REM ================================================
:CIKIS
echo.
echo  Cikiliyor...
timeout /t 1 >nul
exit /b 0
