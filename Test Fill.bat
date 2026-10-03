@echo off
chcp 65001 >nul
title Fill Fiyat Testi
color 0B
cd /d "C:\Users\kadir.kumas\Desktop\Broker_System"

echo.
echo  =====================================================
echo    FILL FIYAT TESTI (TESTNET)
echo  =====================================================
echo.
echo  Bu test gercek testnet emri gonderir:
echo    - 20 USDT, 5x leverage
echo    - LIMIT ^+ MARKET fallback
echo    - Sonunda pozisyon OTOMATIK kapatilir
echo.
echo  ONERILEN SEMBOLLER (likit):
echo    BTCUSDT  ETHUSDT  SOLUSDT  BNBUSDT  XRPUSDT
echo.
set /p SYMBOL="Sembol (bos = SOLUSDT): "

if "%SYMBOL%"=="" set SYMBOL=SOLUSDT

echo.
echo  [TEST] Sembol: %SYMBOL%
echo.
timeout /t 2 >nul

py "Patch\yeni\test_fill_price.py" %SYMBOL%

echo.
echo  =====================================================
echo    TEST TAMAMLANDI
echo  =====================================================
echo.
pause