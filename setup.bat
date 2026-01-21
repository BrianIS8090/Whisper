@echo off
title Wisper Full Setup (Auto-Install)
cd /d "%~dp0"

:: -----------------------------------------------------
:: 1. CHECK ADMINISTRATOR PRIVILEGES
:: -----------------------------------------------------
fltmc >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Requesting Administrator privileges to install dependencies...
    powershell Start-Process -FilePath "%0" -Verb RunAs
    exit /b
)

echo ======================================================
echo   Wisper: Complete Environment Setup
echo ======================================================
echo.

:: -----------------------------------------------------
:: 2. CHECK AND INSTALL PYTHON (3.13)
:: -----------------------------------------------------
echo [Check] Searching for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [MISSING] Python not found. Installing Python 3.13...
    winget install -e --id Python.Python.3.13 --scope machine --accept-package-agreements --accept-source-agreements
    
    echo.
    echo [IMPORTANT] Python installed.
    echo Windows requires a RESTART of this script to recognize the new Python command.
    echo Please close this window and run 'setup.bat' again.
    pause
    exit
) else (
    echo [OK] Python is found.
)

:: -----------------------------------------------------
:: 3. CHECK AND INSTALL FFMPEG
:: -----------------------------------------------------
echo [Check] Searching for FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [MISSING] FFmpeg not found. Installing via Winget...
    winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
    
    echo.
    echo [IMPORTANT] FFmpeg installed.
    echo Windows requires a RESTART of this script to recognize the new FFmpeg command.
    echo Please close this window and run 'setup.bat' again.
    pause
    exit
) else (
    echo [OK] FFmpeg is found.
)

echo.
echo ======================================================
echo   System dependencies verified.
echo   Proceeding to project setup...
echo ======================================================
echo.

:: -----------------------------------------------------
:: 4. PROJECT SETUP (VENV & LIBS)
:: -----------------------------------------------------

echo [1/3] Creating virtual environment (venv)...
if exist venv (
    echo [SKIP] Folder 'venv' already exists.
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv. Make sure you installed Python with "Add to PATH".
        pause
        exit /b
    )
)

echo [2/3] Updating pip...
venv\Scripts\python.exe -m pip install --upgrade pip

echo [3/3] Installing libraries from requirements.txt...
venv\Scripts\pip.exe install -r requirements.txt

echo.
echo ======================================================
echo   SETUP COMPLETED SUCCESSFULLY!
echo ======================================================
echo.
echo You can now run 'start_whisper.bat' or 'silent_start.vbs'
echo.
pause