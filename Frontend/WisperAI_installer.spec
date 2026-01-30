# -*- mode: python ; coding: utf-8 -*-
# Spec-файл для сборки WisperAI в директорию (для установщика)
import os
from PyInstaller.utils.hooks import collect_all

# Путь к FFmpeg (нужен для whisper)
ffmpeg_path = r"C:\Users\Brian\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin"

datas = [('assets', 'assets')]
binaries = [
    (os.path.join(ffmpeg_path, 'ffmpeg.exe'), '.'),
    (os.path.join(ffmpeg_path, 'ffprobe.exe'), '.'),
]
hiddenimports = ['pyaudio', 'keyboard', 'groq', 'requests']

# Собираем все зависимости qfluentwidgets
tmp_ret = collect_all('qfluentwidgets')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Собираем все зависимости whisper
tmp_ret = collect_all('whisper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Сборка в директорию (не onefile) - быстрее запуск, меньше размер установщика
exe = EXE(
    pyz,
    a.scripts,
    [],  # Пустой список - binaries и datas будут в отдельных файлах
    exclude_binaries=True,  # Важно для сборки в директорию
    name='WisperAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\asteroid.ico'],
)

# Сборка в директорию COLLECT
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WisperAI',
)
