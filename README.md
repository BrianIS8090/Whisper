# Wisper — Speech Recognition Toolkit для Windows

Wisper — набор инструментов для распознавания речи на базе OpenAI Whisper с графическим интерфейсом и CLI.

## Основные возможности
- Современный GUI (PyQt6/Fluent) в `Frontend/` для диктовки и транскрибации файлов.
- Локальный Whisper (offline): модели `tiny`/`base`/`small`/`medium`/`large`/`turbo`.
- Groq API: сверхбыстрая облачная транскрибация (`whisper-large-v3`).
- Yandex SpeechKit: низкая задержка для русского языка (v1 API).
- Глобальная горячая клавиша **F8** для живой диктовки.

---

## Быстрый старт
1. Установите FFmpeg и добавьте `bin` в `PATH`.
   - Проверка: `ffmpeg -version`
2. Запустите автоматическую настройку: `setup.bat`.
3. Запуск GUI (рекомендуется):
   - Из исходников: `Frontend\WisperGUI.bat`
   - Из сборки: `Frontend\dist\WisperAI.exe`
4. Запуск CLI-диктовки:
   - `start_whisper.bat` или `python global_speech.py`

---

## Ручная установка (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## Использование

### 1) GUI (Frontend)
- Основной интерфейс приложения.
- Вкладки: диктовка, транскрибация файлов, настройки.
- Для EXE убедитесь, что рядом лежит `.env` с ключами (если используются API).

### 2) CLI: живая диктовка
- Запуск: `start_whisper.bat` или `python global_speech.py`.
- Удерживайте **F8** → говорите → отпустите для распознавания.

### 3) CLI: транскрибация файлов
```powershell
.\venv\Scripts\python.exe transcribe.py "path\to\audio.mp3" small
```
Текст сохраняется рядом с аудио.

---

## Настройки (.env)
Файл `.env` хранится в корне и используется для GUI и API-режимов:
- `GROQ_API_KEY` — ключ Groq.
- `YANDEX_API_KEY` — ключ Yandex SpeechKit.
- `YANDEX_FOLDER_ID` — folder ID для Yandex.
- `MODEL_SIZE` — локальная модель Whisper (например, `small`, `turbo`).
- `DEFAULT_MODE` — режим запуска (`api`, `yandex`, `local`).

Для CLI-версии базовые параметры находятся в начале `global_speech.py`:
- `HOTKEY`, `MODEL_SIZE`, `LANGUAGE`.

---

## Сборка GUI
```powershell
.\venv\Scripts\activate
Frontend\build.bat
```
Готовый EXE: `Frontend\dist\WisperAI.exe`.

---

## Автозапуск
- Добавить GUI в автозапуск: `install_autostart.vbs`.
- Запуск в фоне без окна консоли: `silent_start.vbs`.

---

## Структура проекта
- `global_speech.py` — CLI-диктовка по горячей клавише.
- `overlay.py` — индикатор статуса записи.
- `transcribe.py` — пакетная транскрибация файлов.
- `Frontend/` — GUI и сборка приложения.
- `requirements.txt` — зависимости.

---

## Если что-то не работает
- Проверьте FFmpeg в `PATH` (`ffmpeg -version`).
- Убедитесь, что микрофон доступен в настройках Windows.
- Для облачных режимов проверьте ключи в `.env`.