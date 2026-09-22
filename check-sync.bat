@echo off
chcp 65001 >nul
title Broker - Sync Kontrol
color 0A
cd /d C:\Users\kadir.kumas\Desktop\Broker_System

echo.
echo  =====================================================
echo    BROKER SYNC KONTROL - Cloud vs Local
echo  =====================================================
echo.
echo  Karsilastiriliyor... (5-10 sn)
echo.

py Patch\yeni\check_sync_diff.py

echo.
echo  =====================================================
echo   Kontrol tamamlandi.
echo  =====================================================
echo.
pause