@echo off
chcp 65001 >nul
title GitHub Otomatik Gonderim
color 0a
cd /d "C:\Users\kadir.kumas\Desktop\Broker_System"

echo ========================================
echo     GitHub'a Gonderim Baslatiliyor
echo ========================================
echo.

REM ---- GIT REPO KONTROLU ----
if not exist ".git" (
    echo [X] HATA: Bu klasor bir git repo degil!
    pause
    exit /b 1
)

REM ---- .GITIGNORE KONTROLU ----
if not exist ".gitignore" (
    echo [!] .gitignore bulunamadi! Olusturuluyor...
    (
        echo .env
        echo .env.*
        echo *.key
        echo *.pem
        echo *.db
        echo *.db-wal
        echo *.db-shm
        echo *.bak*
        echo __pycache__/
        echo *.pyc
        echo .venv/
        echo venv/
        echo .vscode/
        echo .idea/
        echo *.log
        echo Thumbs.db
        echo .DS_Store
    ) > .gitignore
    echo [+] .gitignore olusturuldu.
)

REM ---- .env TAKIP KONTROLU (KRITIK) ----
git ls-files --error-unmatch .env >nul 2>&1
if not errorlevel 1 (
    echo.
    echo [!!!] KRITIK: .env git tarafindan TAKIP EDILIYOR!
    echo       API key'lerin GitHub'a sizmis olabilir!
    echo.
    set /p fixenv=".env'i takipten cikarmak ister misin? (E/H): "
    if /i "%fixenv%"=="E" (
        git rm --cached .env
        git commit -m "guvenlik: .env takipten cikarildi"
        echo.
        echo [!] .env takipten cikarildi.
        echo [!] UYARI: Eski commit'lerde .env hala var!
        echo [!] Binance API key'leri IPTAL edip YENISINI uretmelisin!
        pause
    )
)

REM ---- COMMIT MESAJI ----
echo.
set "msg="
set /p msg="Lutfen commit mesajini yazin: "

if "%msg%"=="" (
    echo.
    echo [X] Commit mesaji bos olamaz!
    pause
    exit /b 1
)

REM ---- DEGISIKLIK KONTROLU ----
git diff --quiet
set HAS_UNSTAGED=%errorlevel%
git diff --cached --quiet
set HAS_STAGED=%errorlevel%

if %HAS_UNSTAGED%==0 if %HAS_STAGED%==0 (
    echo.
    echo [!] Hicbir degisiklik yok, commit gerekmez.
    pause
    exit /b 0
)

echo.
echo Degisiklikler ekleniyor...
git add .

git commit -m "%msg%"
if errorlevel 1 (
    echo.
    echo [X] Commit basarisiz!
    pause
    exit /b 1
)

echo.
echo GitHub'a gonderiliyor...
git push
if errorlevel 1 (
    echo.
    echo [X] Push basarisiz!
    echo     Cozum: git push -u origin main
    pause
    exit /b 1
)

echo.
echo ========================================
echo     Islem Tamamlandi!
echo ========================================
pause
