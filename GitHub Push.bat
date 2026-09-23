@echo off
title GitHub Otomatik Gonderim
color 0a
cd /d "C:\Users\kadir.kumas\Desktop\Broker_System"

echo ========================================
echo     GitHub'a Gonderim Baslatiliyor
echo ========================================
echo.

set /p msg="Lutfen commit mesajini yazin (orn: hata duzeltildi): "

echo.
echo Degisiklikler ekleniyor...
git add .

echo.
echo Kaydediliyor...
git commit -m "%msg%"

echo.
echo GitHub'a gonderiliyor...
git push

echo.
echo ========================================
echo     Islem Tamamlandi!
echo ========================================
pause