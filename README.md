# Wisper AI — Комплексное решение для распознавания речи

Wisper AI — это профессиональный инструмент для диктовки и транскрибации с:
- Локальными моделями Whisper (offline)
- Облачными API (Groq, Yandex SpeechKit)
- Полноценным графическим интерфейсом
- Командной строкой (CLI)

## 🔥 Основные возможности

### 🖥️ Графический интерфейс (GUI)
- Современный UI на PyQt6 и QFluentWidgets
- Встроенный аудио-рекордер
- История транскрипций
- Настройка горячих клавиш
- Splash screen при запуске

### 🎙️ Режимы распознавания
1. **Локальный (offline)** - модели Whisper от `tiny` до `large-v3`
2. **Облачный (Groq)** - сверхбыстрое распознавание через API
3. **Yandex SpeechKit** - оптимизировано для русского языка

### ⚡ Особенности
- Горячая клавиша **F8** для мгновенной диктовки
- Индикатор записи в системном трее
- Поддержка длинных аудио (>60 минут)
- Экспорт в TXT

---

## 📥 Установка

### Вариант 1: Установщик (рекомендуется)
1. Скачайте `WisperAI_Setup.exe` из последнего релиза
2. Запустите установщик и следуйте инструкциям
3. Запустите WisperAI через меню Пуск или ярлык на рабочем столе

### Вариант 2: Запуск из исходников
1. Установите FFmpeg и добавьте `bin` в `PATH`
   - Проверка: `ffmpeg -version`
2. Клонируйте репозиторий
3. Запустите автоматическую настройку: `setup.bat`
4. Запустите GUI: `Frontend\WisperGUI.bat`
5. Для CLI-диктовки: `start_whisper.bat` или `python global_speech.py`

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

## ⚙️ Настройки

### Конфигурация GUI
Файл `.env` хранится в:
- **Установленная версия**: `%APPDATA%\WisperAI\.env`
- **Исходники**: в корне проекта

### Параметры конфигурации
- `GROQ_API_KEY` — ключ Groq API
- `YANDEX_API_KEY` — ключ Yandex SpeechKit
- `YANDEX_FOLDER_ID` — folder ID для Yandex
- `MODEL_SIZE` — локальная модель Whisper (`tiny`, `base`, `small`, `medium`, `large`, `turbo`)
- `DEFAULT_MODE` — режим запуска (`api`, `yandex`, `local`)

### CLI-версия
Для CLI базовые параметры находятся в начале `global_speech.py`:
- `HOTKEY` — горячая клавиша (по умолчанию F8)
- `MODEL_SIZE` — размер модели
- `LANGUAGE` — язык распознавания

---

## 🛠️ Сборка

### Сборка EXE
```powershell
.\venv\Scripts\activate
Frontend\build.bat
```
Результат: `Frontend\dist\WisperAI.exe`

### Сборка установщика
```powershell
.\venv\Scripts\activate
cd Frontend
build_installer.bat
```
Результат: `Frontend\dist\WisperAI_Setup.exe`

### Документация по сборке
Подробная документация по процессу сборки:
- `BUILD_INSTALLER_RU.md` — для WisperAI
- `BUILD_INSTALLER_RU_GENERIC.md` — универсальное руководство

---

## Автозапуск
- Добавить GUI в автозапуск: `install_autostart.vbs`.
- Запуск в фоне без окна консоли: `silent_start.vbs`.

---

## 📂 Структура проекта

### Корневые файлы
- `global_speech.py` — CLI-диктовка по горячей клавише
- `overlay.py` — индикатор статуса записи
- `transcribe.py` — пакетная транскрибация файлов
- `requirements.txt` — зависимости

### Графический интерфейс
- `Frontend/main.py` — точка входа GUI
- `Frontend/home_interface.py` — интерфейс диктовки
- `Frontend/transcribe_interface.py` — интерфейс транскрибации
- `Frontend/settings_interface.py` — настройки
- `Frontend/workers.py` — рабочие потоки распознавания

### Сборка
- `Frontend/WisperAI_installer.spec` — конфигурация PyInstaller
- `Frontend/installer/WisperAI_setup.iss` — скрипт Inno Setup
- `Frontend/build_installer.bat` — автоматизация сборки

---

## ❓ Решение проблем

### Общие проблемы
- **Не запускается**: Проверьте FFmpeg в `PATH` (`ffmpeg -version`)
- **Не работает микрофон**: Проверьте доступ в настройках Windows
- **Ошибки API**: Проверьте ключи в `.env`

### Установленная версия
- **Permission denied**: Проверьте права доступа к `%APPDATA%\WisperAI`
- **Не создаются файлы**: Запустите от имени администратора

### Сборка
- **Ошибки PyInstaller**: Проверьте зависимости в `requirements.txt`
- **Ошибки Inno Setup**: Установите Inno Setup 6

### Логи
- GUI: Смотрите консоль или журнал в интерфейсе
- CLI: Проверьте вывод в консоли