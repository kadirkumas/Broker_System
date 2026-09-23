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

set MARK1=
set MARK2=
set MARK3=

if /i "%LOCAL_ST%"=="AKTIF" if /i not "%CLOUD_ST%"=="active" set MARK1=   *** AKTIF ***
if /i "%CLOUD_ST%"=="active" if /i not "%LOCAL_ST%"=="AKTIF" set MARK2=   *** AKTIF ***
if /i not "%LOCAL_ST%"=="AKTIF" if /i not "%CLOUD_ST%"=="active" set MARK3=   *** DURDURULDU ***

echo.
echo  =====================================================
echo    BROKER YONETIM PANELI
echo  =====================================================
echo.
echo    CLOUD : %SSH_IP%   [durum: %CLOUD_ST%]
echo    LOCAL : %LOCAL_DIR%
echo.
echo  -----------------------------------------------------
echo    --- ANA ISLEMLER ---
echo    [1]  LOCAL Moduna Gec
echo    [2]  CLOUD Moduna Gec%MARK2%
echo    [3]  TUM SUNUCULARI DURDUR
echo.
echo    --- CLOUD ISLEMLERI ---
echo    [11] Cloud Bot Durum
echo    [12] Cloud Canli Log
echo    [13] Cloud Bot DURDUR
echo    [14] Cloud Bot Yeniden Baslat
echo    [15] Cloud Son 50 Log
echo    [16] Cloud Arayuzu Ac
echo    [17] Cloud SSH
echo    [18] Cloud Sunucu Durumu
echo.
echo    --- LOCAL ISLEMLERI ---
echo    [21] Local Backend DURDUR (nazik)
echo    [22] Local Backend Durum
echo    [23] Local Arayuzu Ac
echo    [24] Local Backend ZORLA Kapat (taskkill)
echo.
echo    --- SENKRONIZASYON ---
echo    [31] Local -^> Cloud Dosya Gonder
echo.
echo    --- DATABASE ISLEMLERI ---
echo    [41] Local DB Durum
echo    [42] Local DB TEMIZLE
echo    [43] Cloud DB Durum
echo    [44] Cloud DB TEMIZLE
echo.
echo    --- GENEL ---
echo    [92] Durum Raporu
echo    [0]  Cikis
echo  -----------------------------------------------------
echo.
set /p secim="  Secim: "

if "%secim%"=="1"  goto GEC_LOCAL
if "%secim%"=="2"  goto GEC_CLOUD
if "%secim%"=="3"  goto TUM_DURDUR
if "%secim%"=="11" goto CLOUD_DURUM
if "%secim%"=="12" goto CLOUD_LOG
if "%secim%"=="13" goto CLOUD_DURDUR
if "%secim%"=="14" goto CLOUD_YENIDEN
if "%secim%"=="15" goto CLOUD_LOG_50
if "%secim%"=="16" goto CLOUD_ARAYUZ
if "%secim%"=="17" goto CLOUD_SSH
if "%secim%"=="18" goto CLOUD_SISTEM
if "%secim%"=="21" goto LOCAL_DURDUR
if "%secim%"=="22" goto LOCAL_DURUM
if "%secim%"=="23" goto LOCAL_ARAYUZ
if "%secim%"=="24" goto LOCAL_FORCE_KILL
if "%secim%"=="31" goto SYNC_TO_CLOUD
if "%secim%"=="41" goto DB_LOCAL_CHECK
if "%secim%"=="42" goto DB_LOCAL_RESET
if "%secim%"=="43" goto DB_CLOUD_CHECK
if "%secim%"=="44" goto DB_CLOUD_RESET
if "%secim%"=="92" goto DURUM_RAPORU
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
echo  ================================================
echo   LOCAL MODUNA GECILIYOR
echo  ================================================
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
echo   CLOUD MODUNA GECILIYOR
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
REM  3 - TUM SUNUCULARI DURDUR
REM ================================================
:TUM_DURDUR
cls
echo.
echo  === TUM SUNUCULARI DURDURULUYOR ===
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
pause
goto MENU

REM ================================================
REM  11-18 - CLOUD ISLEMLERI
REM ================================================
:CLOUD_DURUM
cls
%SSH_CMD% "sudo systemctl status broker-bot --no-pager"
pause
goto MENU

:CLOUD_LOG
cls
echo  Canli log (Ctrl+C ile durdur)
%SSH_CMD% "sudo journalctl -u broker-bot -f"
pause
goto MENU

:CLOUD_DURDUR
cls
%SSH_CMD% "sudo systemctl stop broker-bot && sudo systemctl status broker-bot --no-pager | head -8"
pause
goto MENU

:CLOUD_YENIDEN
cls
%SSH_CMD% "sudo systemctl restart broker-bot && sleep 2 && sudo systemctl status broker-bot --no-pager | head -8"
pause
goto MENU

:CLOUD_LOG_50
cls
%SSH_CMD% "sudo journalctl -u broker-bot -n 50 --no-pager"
pause
goto MENU

:CLOUD_ARAYUZ
start http://%SSH_IP%:8000
goto MENU

:CLOUD_SSH
cls
echo  SSH baglantisi (cikmak icin: exit)
%SSH_CMD%
pause
goto MENU

:CLOUD_SISTEM
cls
%SSH_CMD% "echo '--- UPTIME ---' && uptime && echo '' && echo '--- DISK ---' && df -h / && echo '' && echo '--- RAM ---' && free -h"
pause
goto MENU

REM ================================================
REM  21-24 - LOCAL ISLEMLERI
REM ================================================
:LOCAL_DURDUR
cls
echo.
echo  === LOCAL BACKEND DURDURULUYOR (nazik) ===
echo.
taskkill /F /FI "WINDOWTITLE eq LOCAL BROKER*" /T >nul 2>&1

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /T /PID %%a >nul 2>&1
    set FOUND=1
)
if "%FOUND%"=="0" (echo Local zaten kapali.) else (echo Local durduruldu.)
pause
goto MENU

:LOCAL_DURUM
cls
netstat -ano | findstr :8000 | findstr LISTENING
if errorlevel 1 (echo [X] Local KAPALI) else (echo [+] Local ACIK)
pause
goto MENU

:LOCAL_ARAYUZ
start http://127.0.0.1:8000
goto MENU

REM ================================================
REM  24 - LOCAL ZORLA KAPAT
REM ================================================
:LOCAL_FORCE_KILL
cls
echo.
echo  ================================================
echo   LOCAL BACKEND ZORLA KAPATILIYOR
echo  ================================================
echo.
echo  DIKKAT: Bu islem TUM Python process'lerini kapatir!
echo          Baslka bir Python script'i calisiyorsa etkilenir.
echo.
echo  Kapatilacak process'ler:
tasklist /FI "IMAGENAME eq python.exe" 2>nul | findstr /I "python.exe"
echo.
set /p onay="  Devam edilsin mi? (E/H): "
if /i not "%onay%"=="E" goto MENU

echo.
echo  [1/3] Pencere basligi ile kapatiliyor...
taskkill /F /FI "WINDOWTITLE eq LOCAL BROKER*" /T >nul 2>&1

echo  [2/3] Port 8000 kullanan process'ler kapatiliyor...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo        PID: %%a - Kapatiliyor...
    taskkill /F /T /PID %%a >nul 2>&1
)

echo  [3/3] TUM python.exe process'leri kapatiliyor...
taskkill /F /IM python.exe >nul 2>&1

timeout /t 2 >nul

echo.
echo  === SONUC ===
netstat -ano | findstr :8000 | findstr LISTENING >nul
if errorlevel 1 (
    echo  [+] TUM LOCAL PYTHON PROCESS'LERI KAPATILDI
    echo  [+] Port 8000 bos
) else (
    echo  [!] Hala acik process var, elle kontrol gerekli
    netstat -ano | findstr :8000 | findstr LISTENING
)
echo.
pause
goto MENU

REM ================================================
REM  31 - SYNC TO CLOUD
REM ================================================
:SYNC_TO_CLOUD
cls
echo.
echo   LOCAL -^> CLOUD DOSYA SENKRONIZASYONU
echo.
echo   (Cloud bot RESTART EDILMEZ)
echo.
echo  Frontend dosyalari...
scp -i %SSH_KEY% ^
    "%LOCAL_DIR%\frontend\index.html" ^
    "%LOCAL_DIR%\frontend\chart.js" ^
    "%LOCAL_DIR%\frontend\style.css" ^
    "%LOCAL_DIR%\frontend\favicon.svg" ^
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
    %SSH_USER%@%SSH_IP%:~/Broker_System/backend/

echo.
echo  Strateji dosyalari...
scp -i %SSH_KEY% ^
    "%LOCAL_DIR%\backend\strategies\*.py" ^
    %SSH_USER%@%SSH_IP%:~/Broker_System/backend/strategies/

echo.
echo  [+] SENKRONIZASYON TAMAMLANDI
echo.
echo   Yeni dosyalari AKTIF ETMEK icin:
echo     [14] Cloud Bot Yeniden Baslat
echo.
pause
goto MENU

REM ================================================
REM  41-44 - DATABASE ISLEMLERI
REM ================================================
:DB_LOCAL_CHECK
cls
cd /d %LOCAL_DIR%
py Patch\yeni\db_check.py local
echo.
pause
goto MENU

:DB_LOCAL_RESET
cls
echo.
echo  === LOCAL DB TEMIZLE ===
echo.
echo  DIKKAT: Local bot CALISIYOR olabilir!
echo          Once [24] ile durdurun.
echo.
set /p onay="  Devam edilsin mi? (E/H): "
if /i not "%onay%"=="E" goto MENU

cd /d %LOCAL_DIR%
py Patch\yeni\db_check.py local reset
echo.
pause
goto MENU

:DB_CLOUD_CHECK
cls
cd /d %LOCAL_DIR%
py Patch\yeni\db_check.py cloud
echo.
pause
goto MENU

:DB_CLOUD_RESET
cls
echo.
echo  === CLOUD DB TEMIZLE ===
echo.
echo  DIKKAT: Cloud bot CALISIYOR olabilir!
echo          Once [13] ile durdurun.
echo.
set /p onay="  Devam edilsin mi? (E/H): "
if /i not "%onay%"=="E" goto MENU

cd /d %LOCAL_DIR%
py Patch\yeni\db_check.py cloud reset
echo.
pause
goto MENU

REM ================================================
REM  92 - DURUM RAPORU
REM ================================================
:DURUM_RAPORU
cls
echo.
echo  --- CLOUD ---
%SSH_CMD% "sudo systemctl is-active broker-bot"
echo.
echo  --- LOCAL ---
netstat -ano | findstr :8000 | findstr LISTENING >nul
if errorlevel 1 (echo  [X] Local KAPALI) else (echo  [+] Local ACIK)
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