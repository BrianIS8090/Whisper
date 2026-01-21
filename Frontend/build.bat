@echo off
cd /d "%~dp0"
echo Building WisperAI with Icon...
..\venv\Scripts\pyinstaller --noconsole --onefile --clean ^
    --name="WisperAI" ^
    --icon="assets\asteroid.ico" ^
    --collect-all qfluentwidgets ^
    --collect-all whisper ^
    --hidden-import=pyaudio ^
    --hidden-import=keyboard ^
    --hidden-import=groq ^
    --hidden-import=requests ^
    --exclude-module PyQt5 ^
    --exclude-module PyQt5.QtCore ^
    --exclude-module PyQt5.QtGui ^
    --exclude-module PyQt5.QtWidgets ^
    --add-data "assets;assets" ^
    main.py
echo Build complete! Check the 'dist' folder.
pause