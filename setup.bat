@echo off
setlocal enabledelayedexpansion
title Fit Zone Gym — System Setup

:: ── Self-elevate to Administrator ─────────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Requesting Administrator rights...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs -Wait"
    exit /b
)

:: ── Move to the folder where this script lives ────────────────────────────
cd /d "%~dp0"

:: ── Launch the PowerShell setup script ───────────────────────────────────
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_helper.ps1"
pause
