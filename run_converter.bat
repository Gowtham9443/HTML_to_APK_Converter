@echo off
title HTML to APK Builder — BEST_TEAM
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║         HTML → APK Builder  •  by BEST_TEAM          ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not on PATH.
    echo         Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check Java
java -version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Java JDK 17+ not found. Build may fail.
    echo           Download from: https://adoptium.net/
)

python converter.py
echo.
pause
