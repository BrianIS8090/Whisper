@echo off
:: Переходим в папку проекта
cd /d "C:\Wisper"

:: Заголовок окна
title Wisper - Speech Recognition

echo Starting Wisper...
echo Please wait while the model loads...

:: Запуск скрипта
venv\Scripts\python global_speech.py

:: Если скрипт упадет, окно не закроется сразу, чтобы было видно ошибку
pause
