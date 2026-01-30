@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo    WisperAI Installer Builder
echo ============================================
echo.

:: Шаг 1: Сборка PyInstaller
echo [1/2] Сборка приложения через PyInstaller...
echo.

if exist "dist\WisperAI" (
    echo Удаление предыдущей сборки...
    rmdir /s /q "dist\WisperAI"
)

..\venv\Scripts\pyinstaller --clean --noconfirm WisperAI_installer.spec

if errorlevel 1 (
    echo.
    echo ОШИБКА: PyInstaller завершился с ошибкой!
    pause
    exit /b 1
)

echo.
echo Копирование FFmpeg в корень сборки...
copy "dist\WisperAI\_internal\ffmpeg.exe" "dist\WisperAI\ffmpeg.exe" >nul 2>&1
copy "dist\WisperAI\_internal\ffprobe.exe" "dist\WisperAI\ffprobe.exe" >nul 2>&1

echo.
echo PyInstaller сборка завершена успешно!
echo.

:: Шаг 2: Сборка Inno Setup
echo [2/2] Создание установщика через Inno Setup...
echo.

:: Проверяем наличие Inno Setup
set "ISCC="

:: Стандартные пути установки Inno Setup
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)

if "!ISCC!"=="" (
    echo.
    echo ВНИМАНИЕ: Inno Setup не найден!
    echo Скачайте и установите Inno Setup 6 с https://jrsoftware.org/isdl.php
    echo.
    echo После установки запустите этот скрипт снова.
    echo.
    echo Файлы приложения готовы в папке: dist\WisperAI
    echo Вы можете собрать установщик вручную, открыв:
    echo   installer\WisperAI_setup.iss
    echo.
    pause
    exit /b 0
)

echo Найден Inno Setup: !ISCC!
echo.

"!ISCC!" "installer\WisperAI_setup.iss"

if errorlevel 1 (
    echo.
    echo ОШИБКА: Inno Setup завершился с ошибкой!
    pause
    exit /b 1
)

echo.
echo ============================================
echo    СБОРКА ЗАВЕРШЕНА УСПЕШНО!
echo ============================================
echo.
echo Установщик создан: dist\WisperAI_Setup.exe
echo.
pause
