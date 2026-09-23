@echo off
cd /d "C:\Users\kadir.kumas\Desktop\Broker_System"
py -m uvicorn backend.main:app --reload
pause