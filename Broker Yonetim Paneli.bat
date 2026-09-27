@echo off
title Broker Yonetim Paneli
color 0A
cd /d "%~dp0"

set SSH_KEY=C:\Users\kadir.kumas\.ssh\broker-bot.key
set SSH_USER=ubuntu
set SSH_IP=92.5.133.137
set SSH_CMD=ssh -i %SSH_KEY% %SSH_USER%@%SSH_IP%
set LOCAL_DIR=C:\Users\kadir.kumas\Desktop\Broker_System

:MENU
cls

%SSH_CMD% "sudo systemctl is-active broker-bot" > "%TEMP%\cloud_st.txt" 2>nul
set /p CLOUD_ST=<"%TEMP%\cloud_st.txt"
del "%TEMP%\cloud_st.txt" >nul 2>&1
if "%CLOUD_ST%"=="" set CLOUD_ST=bilinmiyor

set LOCAL_ST=KAPALI
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if not errorlevel 1 set LOCAL_ST=AKTIF

set MARK2=
if /i "%CLOUD_ST%"=="active" if /i not "%LOCAL_ST%"=="AKTIF" set MARK2=   *** AKTIF ***

echo.
echo  =====================================================
echo    BROKER YONETIM PANELI
echo  =====================================================
echo.
echo    CLOUD : %SSH_IP%   [durum: %CLOUD_ST%]
echo    LOCAL : %LOCAL_DIR%
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
echo    +------------------------------------+  +------------------------------------+
echo    ^| ASIL TEMIZLIK ICIN SIRA:           ^|  ^| LOCAL -> CLOUD GONDERIM:           ^|
echo    ^|  1) [3]  TUM SUNUCULARI DURDUR     ^|  ^|  1) [31] Sync (dosyalari gonder)   ^|
echo    ^|  2) [42] Cloud DB TEMIZLE          ^|  ^|  2) [14] Cloud Bot YENIDEN BASLAT  ^|
echo    ^|  3) [41] Local DB TEMIZLE          ^|  ^|  3) [15] Son 50 Log (kontrol)      ^|
echo    ^|  4) [1]  LOCAL Moduna Gec          ^|  ^|  4) [16] Cloud SSH (gerekirse)     ^|
echo    ^|  5) [2]  CLOUD Moduna Gec          ^|  ^|  5) [13] Canli Log (izle)          ^|
echo    +------------------------------------+  +------------------------------------+
echo.
set /p secim="  Secim: "

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

taskkill /F /FI "WINDOWTITLE eq LOCAL BROKER*" /T >nul 2>&1

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /T /PID %%a >nul 2>&1
)

start "LOCAL BROKER - Port 8000" cmd /k "title LOCAL BROKER - Port 8000 && cd /d %LOCAL_DIR% && echo. && echo Local Broker Backend baslatiliyor... && echo. && py -m uvicorn backend.main:app --reload"

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

taskkill /F /FI "WINDOWTITLE eq LOCAL BROKER*" /T >nul 2>&1

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /T /PID %%a >nul 2>&1
)
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

taskkill /F /FI "WINDOWTITLE eq LOCAL BROKER*" /T >nul 2>&1

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /T /PID %%a >nul 2>&1
    set FOUND=1
)
if "%FOUND%"=="0" (echo        Local zaten kapali.) else (echo        Local DURDURULDU.)
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
%SSH_CMD% "sudo systemctl stop broker-bot && sudo systemctl status broker-bot --no-pager | head -8"
pause
goto MENU


REM ================================================
REM  12 - CLOUD BOT YENIDEN BASLAT
REM ================================================
:CLOUD_YENIDEN
cls
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

taskkill /F /FI "WINDOWTITLE eq LOCAL BROKER*" /T >nul 2>&1

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /T /PID %%a >nul 2>&1
    set FOUND=1
)
if "%FOUND%"=="0" (echo  Local zaten kapali.) else (echo  Local durduruldu.)
pause
goto MENU


REM ================================================
REM  22 - LOCAL BACKEND DURUM
REM ================================================
:LOCAL_DURUM
cls
netstat -ano | findstr :8000 | findstr LISTENING
if errorlevel 1 (echo  [X] Local KAPALI) else (echo  [+] Local ACIK)
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
echo  (Cloud bot RESTART EDILMEZ)
echo.
echo  Frontend dosyalari...
scp -i %SSH_KEY% ^
    "%LOCAL_DIR%\frontend\index.html" ^
    "%LOCAL_DIR%\frontend\chart.js" ^
    "%LOCAL_DIR%\frontend\style.css" ^
    "%LOCAL_DIR%\frontend\favicon.svg" ^
    "%LOCAL_DIR%\frontend\zoom_controls.js" ^
    %SSH_USER%@%SSH_IP%:~/Broker_System/frontend/

echo.
echo  Backend dosyalari...
scp -i %SSH_KEY% ^
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
    %SSH_USER%@%SSH_IP%:~/Broker_System/backend/

echo.
echo  Strateji dosyalari...
scp -i %SSH_KEY% ^
    "%LOCAL_DIR%\backend\strategies\*.py" ^
    %SSH_USER%@%SSH_IP%:~/Broker_System/backend/strategies/

echo.
echo  Mobile dosyalari...
scp -i %SSH_KEY% ^
    "%LOCAL_DIR%\frontend\mobile\index.html" ^
    "%LOCAL_DIR%\frontend\mobile\mobile.css" ^
    "%LOCAL_DIR%\frontend\mobile\mobile.js" ^
    %SSH_USER%@%SSH_IP%:~/Broker_System/frontend/mobile/

echo.
echo  [+] SENKRONIZASYON TAMAMLANDI
echo.
echo   Yeni dosyalari AKTIF ETMEK icin: [12] Cloud Bot Yeniden Baslat
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

cd /d %LOCAL_DIR%
py Patch\yeni\db_check.py local reset
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

cd /d %LOCAL_DIR%
py Patch\yeni\db_check.py cloud reset
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
