@echo off
chcp 65001 >nul
title Broker Local Yedek
color 0A
cd /d "%~dp0"

set SRC=C:\Users\kadir.kumas\Desktop\Broker_System
set BACKUP_ROOT=C:\Users\kadir.kumas\Desktop\Broker_Backups\local

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set STAMP=%%i
set ZIP_NAME=Broker_Local_%STAMP%.zip
set ZIP_PATH=%BACKUP_ROOT%\%ZIP_NAME%

echo.
echo  =====================================================
echo    BROKER LOCAL YEDEK
echo  =====================================================
echo.
echo  Kaynak : %SRC%
echo  Hedef  : %ZIP_PATH%
echo.

if not exist "%SRC%" (
    echo  [HATA] Proje klasoru bulunamadi.
    pause
    exit /b 1
)
if not exist "%BACKUP_ROOT%" mkdir "%BACKUP_ROOT%"

echo  Yedekleniyor... -10-30 sn-
echo.

powershell -NoProfile -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$src='%SRC%'; $dst='%ZIP_PATH%';" ^
  "$temp=Join-Path $env:TEMP -ChildPath ('broker_zip_' + [guid]::NewGuid().ToString());" ^
  "New-Item -ItemType Directory -Path $temp | Out-Null;" ^
  "$dest=Join-Path $temp 'Broker_System';" ^
  "Copy-Item -Path $src -Destination $dest -Recurse -Force;" ^
  "Get-ChildItem -Path $dest -Recurse -Directory -Force | Where-Object { $_.Name -in @('venv','__pycache__','node_modules','.git') } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue;" ^
  "Get-ChildItem -Path $dest -Recurse -File -Force | Where-Object { $_.Extension -in @('.pyc','.pyo') } | Remove-Item -Force -ErrorAction SilentlyContinue;" ^
  "Compress-Archive -Path $dest -DestinationPath $dst -CompressionLevel Optimal -Force;" ^
  "Remove-Item -Path $temp -Recurse -Force;" ^
  "Write-Host '  [+] Tamamlandi' -ForegroundColor Green"

if errorlevel 1 (
    echo.
    echo  [HATA] Yedekleme basarisiz.
    pause
    exit /b 1
)

echo.
echo  =====================================================
echo    YEDEK TAMAMLANDI
echo  =====================================================
for %%A in ("%ZIP_PATH%") do (
    echo  Dosya : %%~nxA
    echo  Boyut : %%~zA byte
)
echo  Yer   : %BACKUP_ROOT%
echo.

echo  --- Mevcut Local Yedekler ---
dir /b /o-d "%BACKUP_ROOT%\Broker_Local_*.zip" 2>nul

echo.
echo  Eski yedekler temizleniyor -son 10 tutulur-...
powershell -NoProfile -Command "Get-ChildItem '%BACKUP_ROOT%\Broker_Local_*.zip' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 10 | Remove-Item -Force -ErrorAction SilentlyContinue"

echo.
echo  Cikmak icin bir tusa basin...
pause >nul