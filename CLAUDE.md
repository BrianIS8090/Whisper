# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Язык общения

- Всё общение с пользователем ведётся **только на русском языке**.
- Комментарии в коде пишутся **только на русском языке**.

## Project Overview

Wisper is a Windows speech-to-text toolkit combining local OpenAI Whisper models with cloud APIs (Groq, Yandex SpeechKit). It provides both a CLI (global F8 hotkey dictation) and a modern PyQt6 GUI with Fluent Design (Windows 11 style). Primary language context is Russian.

## Build & Run Commands

```powershell
# Environment setup (automated — installs Python 3.13, FFmpeg, venv, deps)
setup.bat

# Manual environment setup
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Verify FFmpeg (required by Whisper)
ffmpeg -version

# Run GUI
Frontend\WisperGUI.bat
# or compiled: Frontend\dist\WisperAI.exe

# Run CLI dictation (hold F8 to record, release to transcribe)
start_whisper.bat
# or: .\venv\Scripts\python global_speech.py

# Run CLI file transcription
.\venv\Scripts\python transcribe.py "path\to\audio.mp3" small

# Build EXE with PyInstaller
cd Frontend && ..\venv\Scripts\activate && build.bat
# Output: Frontend\dist\WisperAI.exe
```

## Testing

No automated test suite. Manual verification:
1. Launch dictation, hold/release F8 — overlay should show red (recording) then yellow (recognizing), text pastes into active window.
2. Test short (<60s) and near-60s recordings for timeout handling.
3. Run `python transcribe.py sample.wav small` — confirm `.txt` output alongside audio.

If tests are added, place them in `tests/` mirroring script names (e.g., `test_global_speech.py`).

## Architecture

**Three transcription backends** switchable at runtime:
- **Local Whisper** (offline) — models: tiny, base, small, medium, large, turbo
- **Groq API** (cloud) — whisper-large-v3, requires `GROQ_API_KEY`
- **Yandex SpeechKit** (cloud) — with YandexGPT post-processing for grammar/punctuation, requires `YANDEX_API_KEY` + `YANDEX_FOLDER_ID`

**Two interfaces:**
- **CLI** (`global_speech.py`) — standalone F8 hotkey listener with Tkinter overlay (`overlay.py`), clipboard paste automation
- **GUI** (`Frontend/`) — PyQt6 + PyQt-Fluent-Widgets with three tabs: Dictation, File Transcription, Settings

**GUI threading model** (`Frontend/workers.py`):
- Main thread handles only UI rendering
- `GlobalSpeechWorker` and `TranscribeWorker` (QObject subclasses) run in QThreads
- Workers communicate via Qt Signals (`text_ready`, `status_changed`, `error_occurred`) — never modify UI directly

**Key file roles:**
| File | Role |
|------|------|
| `global_speech.py` | CLI hotkey engine: F8 listener, recording, transcription, clipboard paste |
| `overlay.py` | Tkinter recording indicator (red=recording, yellow=recognizing) |
| `transcribe.py` | CLI batch file transcription |
| `Frontend/main.py` | GUI entry point, FluentWindow with navigation tabs |
| `Frontend/home_interface.py` | Dictation tab — mode selector, status log, worker control |
| `Frontend/transcribe_interface.py` | File transcription tab with drag-and-drop |
| `Frontend/settings_interface.py` | Settings tab — API keys, model selection, .env persistence |
| `Frontend/workers.py` | QThread workers for dictation and transcription |

## Configuration

`.env` file in project root (or `%APPDATA%/WisperAI/.env` for compiled EXE):
- `GROQ_API_KEY`, `YANDEX_API_KEY`, `YANDEX_FOLDER_ID` — API credentials
- `MODEL_SIZE` — local Whisper model (default: `small`)
- `DEFAULT_MODE` — startup mode: `local`, `api`, or `yandex`

CLI constants (`HOTKEY`, `MODEL_SIZE`, `LANGUAGE`) are at the top of `global_speech.py`.

## Coding Conventions

- Python 3.10+, PEP 8, 4-space indents
- `lowercase_with_underscores` for functions/variables, `CapWords` for classes
- Use existing `log()` helper for timestamped logging
- Keep user-facing text concise; comments ASCII and purposeful
- Commit messages: `feat: ...`, `fix: ...` style, small atomic changes
- Windows-specific: uses `ctypes.windll` for console/taskbar, `CREATE_NO_WINDOW` for subprocess calls

## Platform Notes

- **Windows only** — relies on `keyboard` library global hooks, `ctypes.windll`, VBS scripts
- Audio: 44.1kHz mono 16-bit WAV (CLI), 48kHz (GUI/Yandex compatibility)
- Yandex API: strips 44-byte WAV header, sends raw LPCM
- Memory: explicit `gc.collect()` and variable deletion after transcription to free VRAM
