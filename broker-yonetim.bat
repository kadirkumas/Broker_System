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
echo    [1]  LOCAL Moduna Gec    - Cloud durur, Local baslar%MARK1%
echo    [2]  CLOUD Moduna Gec    - Local durur, Cloud baslar%MARK2%
echo    [3]  TUM SUNUCULARI DURDUR  - Cloud ve Local%MARK3%
echo.
echo    --- CLOUD ISLEMLERI ---
echo    [11] Cloud Bot DURUMUNU Gor
echo    [12] Cloud Bot CANLI LOG Izle
echo    [13] Cloud Bot DURDUR
echo    [14] Cloud Bot YENIDEN BASLAT
echo    [15] Cloud Son 50 Log
echo    [16] Cloud Arayuzu Ac
echo    [17] Cloud SSH
echo    [18] Cloud Sunucu Durumu
echo.
echo    --- LOCAL ISLEMLERI ---
echo    [21] Local Backend DURDUR
echo    [22] Local Backend DURUMUNU Gor
echo    [23] Local Arayuzu Ac
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
if "%secim%"=="92" goto DURUM_RAPORU
if "%secim%"=="0"  goto CIKIS

echo.
echo  !! Gecersiz secim: %secim%
timeout /t 2 >nul
goto MENU

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

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

start "LOCAL BROKER BACKEND" cmd /k "title LOCAL BROKER - Port 8000 && cd /d %LOCAL_DIR% && echo. && echo Local Broker Backend baslatiliyor... && echo. && py -m uvicorn backend.main:app --reload"

echo.
echo  ================================================
echo   [+] LOCAL MODU AKTIF
echo  ================================================
echo.
echo   Local arayuz : http://127.0.0.1:8000
echo   Cloud        : DURDURULDU
echo.
timeout /t 4 >nul
goto MENU

:GEC_CLOUD
cls
echo.
echo  ================================================
echo   CLOUD MODUNA GECILIYOR
echo  ================================================
echo.
echo  [1/2] Local backend durduruluyor...

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    set FOUND=1
)
if "%FOUND%"=="0" (
    echo        Local zaten kapali.
) else (
    echo        Local durduruldu.
)

echo.
echo  [2/2] Cloud bot baslatiliyor...
%SSH_CMD% "sudo systemctl start broker-bot && sleep 3 && sudo systemctl status broker-bot --no-pager | head -8"
echo.
echo  ================================================
echo   [+] CLOUD MODU AKTIF
echo  ================================================
echo.
echo   Cloud arayuz : http://%SSH_IP%:8000
echo   Local        : DURDURULDU
echo.
pause
goto MENU

:TUM_DURDUR
cls
echo.
echo  ================================================
echo   TUM SUNUCULARI DURDURULUYOR
echo  ================================================
echo.
echo  [1/2] Cloud bot durduruluyor...
%SSH_CMD% "sudo systemctl stop broker-bot" >nul 2>&1
echo        Cloud DURDURULDU.
echo.
echo  [2/2] Local backend durduruluyor...
set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo        Process PID: %%a - Kapatiliyor...
    taskkill /F /PID %%a >nul 2>&1
    set FOUND=1
)
if "%FOUND%"=="0" (
    echo        Local zaten kapali.
) else (
    echo        Local DURDURULDU.
)

echo.
echo  ================================================
echo   [+] TUM SUNUCULAR DURDURULDU
echo  ================================================
echo.
echo   Cloud : DURDURULDU
echo   Local : DURDURULDU
echo.
pause
goto MENU

:CLOUD_DURUM
cls
echo.
echo  === CLOUD BOT DURUMU ===
echo.
%SSH_CMD% "sudo systemctl status broker-bot --no-pager"
echo.
pause
goto MENU

:CLOUD_LOG
cls
echo.
echo  === CLOUD CANLI LOG - Durdurmak icin Ctrl+C ===
echo.
%SSH_CMD% "sudo journalctl -u broker-bot -f"
pause
goto MENU

:CLOUD_DURDUR
cls
echo.
echo  === CLOUD BOT DURDURULUYOR ===
echo.
%SSH_CMD% "sudo systemctl stop broker-bot && sudo systemctl status broker-bot --no-pager | head -8"
echo.
pause
goto MENU

:CLOUD_YENIDEN
cls
echo.
echo  === CLOUD BOT YENIDEN BASLATILIYOR ===
echo.
%SSH_CMD% "sudo systemctl restart broker-bot && sleep 2 && sudo systemctl status broker-bot --no-pager | head -8"
echo.
pause
goto MENU

:CLOUD_LOG_50
cls
echo.
echo  === CLOUD SON 50 LOG ===
echo.
%SSH_CMD% "sudo journalctl -u broker-bot -n 50 --no-pager"
echo.
pause
goto MENU

:CLOUD_ARAYUZ
start http://%SSH_IP%:8000
goto MENU

:CLOUD_SSH
cls
echo.
echo  === CLOUD SSH ===
echo.
echo  Cikmak icin: exit
echo.
%SSH_CMD%
echo.
pause
goto MENU

:CLOUD_SISTEM
cls
echo.
echo  === CLOUD SUNUCU DURUMU ===
echo.
%SSH_CMD% "echo '--- UPTIME ---' && uptime && echo '' && echo '--- DISK ---' && df -h / && echo '' && echo '--- RAM ---' && free -h"
echo.
pause
goto MENU

:LOCAL_DURDUR
cls
echo.
echo  === LOCAL BACKEND DURDURULUYOR ===
echo.

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo  Process PID: %%a - Kapatiliyor...
    taskkill /F /PID %%a >nul 2>&1
    set FOUND=1
)

if "%FOUND%"=="0" (
    echo  Port 8000'de calisan process bulunamadi.
) else (
    echo.
    echo  Local backend durduruldu.
)

echo.
pause
goto MENU

:LOCAL_DURUM
cls
echo.
echo  === LOCAL BACKEND DURUMU ===
echo.
echo  Port 8000 kontrolu:
echo.
netstat -ano | findstr :8000 | findstr LISTENING

if errorlevel 1 (
    echo.
    echo  [X] Local backend KAPALI - port 8000 bos
) else (
    echo.
    echo  [+] Local backend ACIK - port 8000 dolu
)

echo.
echo  Local arayuz: http://127.0.0.1:8000
echo.
pause
goto MENU

:LOCAL_ARAYUZ
start http://127.0.0.1:8000
goto MENU

:DURUM_RAPORU
cls
echo.
echo  ================================================
echo   DURUM RAPORU
echo  ================================================
echo.
echo  --- CLOUD ---
%SSH_CMD% "sudo systemctl is-active broker-bot"
echo.
echo  --- LOCAL ---
netstat -ano | findstr :8000 | findstr LISTENING >nul
if errorlevel 1 (
    echo  [X] Local KAPALI
) else (
    echo  [+] Local ACIK
)
echo.
pause
goto MENU

:CIKIS
echo.
echo  Cikiliyor...
timeout /t 1 >nul
exit /b 0