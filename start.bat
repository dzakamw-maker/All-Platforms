@echo off
title All Platforms
cd /d "%~dp0"

echo ========================================================
echo                  ALL PLATFORMS LAUNCHER
echo ========================================================
echo.

set PYTHON_BIN=python
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set PYTHON_BIN="%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
)

%PYTHON_BIN% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan di sistem kamu!
    echo Silakan install Python 3.10+ terlebih dahulu dari https://python.org
    echo Pastikan mencentang "Add Python to PATH" saat instalasi.
    pause
    exit /b
)

echo Menjalankan aplikasi...
%PYTHON_BIN% run.py

pause
