@echo off
title Doctor Aslan Bot
echo ============================================
echo   Doctor Aslan - Telegram Bot
echo ============================================
echo.

echo [1/2] Installing dependencies...
"C:\Users\samad\AppData\Local\Python\bin\python.exe" -m pip install -r requirements.txt
echo.

echo [2/2] Starting bot...
echo.
"C:\Users\samad\AppData\Local\Python\bin\python.exe" main.py

echo.
echo Bot stopped.
pause
