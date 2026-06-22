@echo off
title Fit Zone Gym Management System
echo.
echo  =============================================
echo   FIT ZONE GYM - Management System v1.0.0
echo  =============================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

:: Install dependencies if needed
echo  Checking dependencies...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing required packages...
    pip install -r requirements.txt -q
)

pip show python-dateutil >nul 2>&1
if %errorlevel% neq 0 (
    pip install python-dateutil -q
)

echo  Starting application...
echo  Browser will open automatically at http://127.0.0.1:8000
echo.
echo  Press Ctrl+C to stop the server.
echo.

python main.py

pause
