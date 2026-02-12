# AGENTS.md — Руководство для агентов разработки

Правила и соглашения для работы с кодовой базой Wisper AI.

---

## Обзор проекта

**Wisper AI** — приложение для распознавания речи с GUI и CLI интерфейсами.
- **Стек**: Python 3.10+, PyQt6, PyQt-Fluent-Widgets
- **ML/Audio**: OpenAI Whisper, Groq API, Yandex SpeechKit
- **Платформа**: Windows

---

## Команды

### Установка и запуск
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# GUI
.\venv\Scripts\python.exe Frontend\main.py

# CLI диктовка (F8 для записи)
.\venv\Scripts\python.exe global_speech.py

# Транскрибация файла
.\venv\Scripts\python.exe transcribe.py "path\to\audio.mp3" small
```

### Сборка
```bash
.\venv\Scripts\activate ; cd Frontend ; .\build.bat
# Результат: Frontend\dist\WisperAI.exe
```

### Тестирование
```bash
# Формальных тестов нет. Проверяйте вручную:
# 1. Вкладка "Диктовка" — включите службу, нажмите F8
# 2. Вкладка "Транскрипция" — перетащите аудиофайл
# 3. Вкладка "Настройки" — проверьте сохранение ключей
```

### Линтинг
```bash
ruff check .
pylint Frontend/
mypy Frontend/
```

---

## Стиль кода

### Отступы и форматирование
- **Отступ**: 4 пробела
- **Длина строки**: 100 символов
- **Кодировка**: UTF-8

### Импорты
Группируются: 1) стандартная библиотека, 2) сторонние, 3) локальные модули.

```python
import os
import sys
import tempfile

from PyQt6.QtCore import Qt, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import FluentIcon as FIF

from workers import GlobalSpeechWorker
```

### Именование
| Элемент | Стиль | Пример |
|---------|-------|--------|
| Переменные/функции | snake_case | `model_name`, `load_settings()` |
| Классы | PascalCase | `HomeInterface`, `TranscribeWorker` |
| Константы | UPPER_SNAKE_CASE | `HOTKEY`, `MODEL_SIZE` |
| Сигналы/слоты Qt | snake_case | `text_ready`, `on_text_ready` |

### Типизация
Type hints опциональны (в кодовой базе не используются).

---

## Комментарии и строки

- **Комментарии**: на русском языке
- **Docstrings**: на русском (опционально)
- **Строки UI**: на русском

```python
# Патч для скрытия консольного окна ffmpeg
def get_env_path():
    """Возвращает путь к .env файлу"""
    ...

self.statusLabel.setText("Служба активна (Нажмите F8)")
```

---

## Обработка ошибок

```python
try:
    result = perform_operation()
except Exception as e:
    print(f"Ошибка: {e}")
    self.error_occurred.emit(str(e))  # для Qt воркеров
```

Воркеры не должны напрямую изменять UI — используйте сигналы:
```python
class GlobalSpeechWorker(QObject):
    error_occurred = pyqtSignal(str)
    
    def run(self):
        try:
            ...
        except Exception as e:
            self.error_occurred.emit(str(e))
```

---

## Архитектура GUI (PyQt6)

### Многопоточность
Тяжёлые операции выполняются в QThread через signals/slots:

```python
self.thread = QThread()
self.worker.moveToThread(self.thread)
self.thread.started.connect(self.worker.run)
self.worker.text_ready.connect(self.on_text_ready)
self.thread.start()
```

### Структура Frontend/
| Файл | Назначение |
|------|------------|
| `main.py` | Точка входа |
| `home_interface.py` | Вкладка "Диктовка" |
| `transcribe_interface.py` | Вкладка "Транскрипция" |
| `settings_interface.py` | Вкладка "Настройки" |
| `workers.py` | Фоновые воркеры |

### Определение режима (exe vs скрипт)
```python
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    env_path = os.path.join(os.environ.get('APPDATA', ''), 'WisperAI', '.env')
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(os.path.dirname(base_path), '.env')
```

---

## Конфигурация (.env)

| Переменная | Описание |
|------------|----------|
| `GROQ_API_KEY` | Ключ Groq API |
| `YANDEX_API_KEY` | Ключ Yandex SpeechKit |
| `YANDEX_FOLDER_ID` | Folder ID для Yandex |
| `MODEL_SIZE` | Модель: tiny, base, small, medium, large, turbo |
| `DEFAULT_MODE` | Режим: api, yandex, local |
| `HOTKEY` | Горячая клавиша: F6-F10, ctrl+space, ctrl+shift+d, alt+d |

```python
from dotenv import load_dotenv
load_dotenv(env_path, override=True)
model_size = os.getenv("MODEL_SIZE", "small")
```

---

## Windows-специфичные правила

- **НЕ используйте `&&`** в командах — используйте `;` или отдельные вызовы
- **НЕ используйте heredoc** (`<<EOF`) — PowerShell не поддерживает
- **Используйте `os.path.join`** или `pathlib` для путей

---

## Чего избегать

1. **Не коммитьте `.env`** с реальными ключами
2. **Не блокируйте GUI поток** — используйте QThread
3. **Не хардкодьте пути** — используйте `os.path` или `pathlib`
