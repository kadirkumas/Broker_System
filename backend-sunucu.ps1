# ============================================================
#  BROKER SYSTEM - BACKEND SUNUCU (PowerShell)
# ============================================================
# - UTF-8 karakter destegi
# - Renkli cikti
# - Port kontrolu
# - Hata yakalama
# ============================================================

# UTF-8 output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Pencere basligi
$Host.UI.RawUI.WindowTitle = "LOCAL BROKER - Port 8000"

# Fonksiyonlar
function Write-Banner {
    Write-Host ""
    Write-Host "  =============================================" -ForegroundColor Cyan
    Write-Host "    BROKER SYSTEM - LOCAL BACKEND (PowerShell)"   -ForegroundColor Cyan
    Write-Host "  =============================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Info($msg)  { Write-Host "[*] $msg" -ForegroundColor Gray }
function Write-Ok($msg)    { Write-Host "[+] $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "[X] $msg" -ForegroundColor Red }

# Banner
Clear-Host
Write-Banner

# Proje dizini
$projectRoot = "C:\Users\kadir.kumas\Desktop\Broker_System"
Write-Info "Proje dizini: $projectRoot"

if (-not (Test-Path $projectRoot)) {
    Write-Err "Proje klasoru bulunamadi!"
    Read-Host "Cikmak icin Enter"
    exit 1
}

Set-Location $projectRoot

# Python kontrolu
try {
    $pyVer = py --version 2>&1
    Write-Ok "Python: $pyVer"
} catch {
    Write-Err "Python (py) bulunamadi!"
    Read-Host "Cikmak icin Enter"
    exit 1
}

# .env kontrolu
if (Test-Path "$projectRoot\.env") {
    Write-Ok ".env dosyasi bulundu"
} else {
    Write-Warn2 ".env dosyasi yok! Bot basarisiz olabilir."
}

# Port 8000 kontrolu
Write-Host ""
Write-Info "Port 8000 kontrolu..."
$portBusy = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($portBusy) {
    $owner = ($portBusy | Select-Object -First 1).OwningProcess
    $proc = Get-Process -Id $owner -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Warn2 "Port 8000 ZATEN KULLANIMDA!"
    if ($proc) {
        Write-Host "     Process: $($proc.ProcessName) (PID: $owner)" -ForegroundColor Yellow
    }
    Write-Host ""
    $ans = Read-Host "Mevcut process kapatilsin mi? (E/H)"
    if ($ans -eq 'E' -or $ans -eq 'e') {
        try {
            Stop-Process -Id $owner -Force -ErrorAction Stop
            Write-Ok "Process kapatildi (PID: $owner)"
            Start-Sleep -Seconds 2
        } catch {
            Write-Err "Process kapatilamadi: $($_.Exception.Message)"
            Read-Host "Cikmak icin Enter"
            exit 1
        }
    } else {
        Write-Info "Iptal edildi."
        Read-Host "Cikmak icin Enter"
        exit 0
    }
} else {
    Write-Ok "Port 8000 musait"
}

# Baslat
Write-Host ""
Write-Info "Backend baslatiliyor..."
Write-Host ""
Write-Host "  Arayuz : " -NoNewline -ForegroundColor DarkGray
Write-Host "http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  Mobil  : " -NoNewline -ForegroundColor DarkGray
Write-Host "http://127.0.0.1:8000/m" -ForegroundColor Cyan
Write-Host "  Durdur : " -NoNewline -ForegroundColor DarkGray
Write-Host "Ctrl+C" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ---------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# Uvicorn
$exitCode = 0
try {
    py -m uvicorn backend.main:app --reload
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host ""
    Write-Err "Hata: $($_.Exception.Message)"
    $exitCode = 1
}

# Cikis
Write-Host ""
Write-Host "  ---------------------------------------------" -ForegroundColor DarkGray
if ($exitCode -eq 0) {
    Write-Info "Sunucu normal sekilde durdu."
} else {
    Write-Warn2 "Sunucu hata kodu ile durdu: $exitCode"
}
Write-Host ""
Read-Host "Cikmak icin Enter"
