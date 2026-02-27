# README Technical

Техническая документация по проекту Wisper AI.

## Обзор проекта

Wisper AI — приложение для распознавания речи с GUI и CLI интерфейсами.

- GUI: PyQt6 + PyQt-Fluent-Widgets.
- Режимы распознавания:
  - локальные модели Whisper;
  - Groq API (глобальная диктовка);
  - Yandex SpeechKit (асинхронная транскрибация файлов).
- Дополнительные функции:
  - транскрибация больших файлов с автоматической разбивкой;
  - сохранение результата в Markdown;
  - словарь пользовательских замен;
  - лемматизация словаря через `pymorphy3` (с fallback на точные замены).

## Стек

- Python 3.10+
- PyQt6
- PyQt-Fluent-Widgets
- openai-whisper
- requests
- groq
- pymorphy3
- ffmpeg / ffprobe (в `PATH` для вкладки больших файлов)

## Установка из исходников

```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Запуск

### GUI

```powershell
.\venv\Scripts\python.exe Frontend\main.py
```

### CLI: глобальная диктовка

```powershell
.\venv\Scripts\python.exe global_speech.py
```

### CLI: транскрибация файла

```powershell
.\venv\Scripts\python.exe transcribe.py "path\to\audio.mp3" small
```

## Конфигурация

Используется `.env`:

- в режиме запуска из исходников: в корне проекта;
- в установленной версии: `%APPDATA%\WisperAI\.env`.

Поддерживаемые параметры:

- `GROQ_API_KEY`
- `YANDEX_API_KEY`
- `YANDEX_FOLDER_ID`
- `MODEL_SIZE`
- `DEFAULT_MODE`
- `HOTKEY`
- `DICTATION_PROMPT`

## Ограничения и поведение Yandex SpeechKit

- Асинхронное распознавание файла использует `recognizeFileAsync`.
- Для файла по `uri` действуют ограничения размера на стороне API.
- Для больших файлов используется отдельная вкладка с:
  - конвертацией в mp3;
  - разбиением на части;
  - пакетной отправкой частей;
  - объединением текста в один Markdown-файл.

## Структура проекта

Ключевые файлы:

- `Frontend/main.py` — точка входа GUI.
- `Frontend/home_interface.py` — глобальная диктовка.
- `Frontend/chunked_transcribe_interface.py` — транскрибация больших файлов.
- `Frontend/dictionary_interface.py` — словарь замен.
- `Frontend/settings_interface.py` — настройки.
- `Frontend/workers.py` — фоновые воркеры и API-интеграции.
- `transcribe.py` — CLI транскрибация.
- `global_speech.py` — CLI диктовка.

## Сборка EXE и установщика

### Сборка EXE

```powershell
.\venv\Scripts\activate
Frontend\build.bat
```

Результат: `Frontend\dist\WisperAI.exe`.

### Сборка установщика

```powershell
.\venv\Scripts\activate
cd Frontend
build_installer.bat
```

Результат: `Frontend\dist\WisperAI_Setup.exe`.

В проекте используются:

- `Frontend/WisperAI.spec`
- `Frontend/WisperAI_installer.spec`
- `Frontend/installer/WisperAI_setup.iss`

## Проверка зависимостей в сборке

После сборки проверьте:

- наличие `ffmpeg.exe` и `ffprobe.exe` в `_internal`;
- включение пакетов `pymorphy3` и `pymorphy3_dicts_ru`;
- корректность запуска вкладки транскрибации больших файлов;
- корректность работы вкладки словаря и применения правил в диктовке.

## Диагностика

- Ошибки API выводятся в интерфейсе с полными сообщениями.
- Для сложных случаев используйте консольный вывод и логи worker-потоков.
- Если `ffmpeg` или `ffprobe` не найдены, в UI показывается явная ошибка.
