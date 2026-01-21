# Wisper Project Context

## Project Overview
**Wisper** is a versatile speech recognition toolkit for Windows. It started as a CLI tool powered by OpenAI's Whisper but has evolved into a full-fledged GUI application supporting multiple engines:
1.  **Local Whisper:** Runs completely offline using OpenAI's models (tiny, base, small, medium, large, turbo).
2.  **Groq API:** Cloud-based lightning-fast transcription using `whisper-large-v3` on LPU hardware.
3.  **Yandex SpeechKit:** Low-latency cloud recognition optimized for Russian language (v1 API).

## Key Components

### 1. Modern GUI (Frontend)
Located in `Frontend/`, this is now the primary interface for the application.
-   **Tech Stack:** Python, PyQt6, PyQt-Fluent-Widgets.
-   **Style:** Native Windows 11 design (Mica material, fluent icons).
-   **Features:**
    *   **Dictation Tab:** Toggle global F8 hotkey listener, switch between Local/Groq/Yandex modes on the fly, view live logs.
    *   **Transcribe Tab:** Drag & drop file transcription with progress bar.
    *   **Settings Tab:** Configure API keys (Groq, Yandex), select local Whisper model size, set default startup mode.
-   **Executable:** Compiled into a standalone `WisperAI.exe` (with icon) for ease of use.

### 2. Core Logic (Backend)
-   **`Frontend/workers.py`:** Handles threading for recording and transcription to keep the UI responsive. Implements the logic for switching between engines.
-   **`global_speech.py`:** The legacy CLI version (still functional) for headless operation.
-   **`transcribe.py`:** CLI script for batch file processing.

### 3. Configuration
Settings are stored in a `.env` file in the root directory.
-   `GROQ_API_KEY`: Key for Groq cloud API.
-   `YANDEX_API_KEY`: API Key for Yandex Cloud.
-   `YANDEX_FOLDER_ID`: Folder ID for Yandex Cloud (required for permissions).
-   `MODEL_SIZE`: Preferred local model (e.g., `small`, `turbo`).
-   `DEFAULT_MODE`: Startup mode (`api`, `yandex`, or `local`).

## Usage Guide

### Running the GUI
1.  Navigate to `Frontend/dist/` (or wherever you placed `WisperAI.exe`).
2.  Ensure `.env` is present in the same folder.
3.  Run **`WisperAI.exe`**.
    *   *Alternative:* Run `Frontend/WisperGUI.bat` to launch from source code without a console window.

### Modes
-   **Groq API:** Requires internet. Extremely fast (near real-time). Best for long dictation with perfect punctuation.
-   **Yandex SpeechKit:** Requires internet. Very low latency. Best for short, rapid commands. Note: Does not auto-punctuate in v1 mode.
-   **Local Whisper:** Offline. Privacy-focused. Speed depends on CPU/GPU. Supports `turbo` model for speed/quality balance.

### Building from Source
To compile the GUI into an EXE:
1.  Activate venv: `.\venv\Scripts\activate`
2.  Run the build script: `Frontend\build.bat`
3.  The output will be in `Frontend\dist\WisperAI.exe`.

---

## Recent Changes (January 2026)

### 3. GUI & Multi-Engine Support
-   **Frontend Implementation:** Created a PyQt6-based GUI with Fluent Design.
-   **Groq Integration:** Added support for Groq API (`whisper-large-v3`) for ultra-fast cloud transcription.
-   **Yandex Integration:** Added support for Yandex SpeechKit v1 (`stt:recognize`) with proper 48kHz PCM handling and Folder ID support.
-   **Settings Management:** Implemented a robust settings interface that saves to `.env`. Users can now select default modes and models visually.
-   **Executable Build:** Configured `PyInstaller` to build a single-file executable (`WisperAI.exe`) with a custom icon, hiding the console window (`noconsole`).
-   **Autostart:** Added `install_autostart.vbs` to easily add the application to Windows startup.

### 4. Stability Improvements
-   **Thread Safety:** Moved all heavy lifting (recording, network requests, model loading) to background `QThread` workers to prevent GUI freezing.
-   **Dependency Fixes:** Resolved conflicts between PyQt5 and PyQt6 by enforcing `PyQt6-Fluent-Widgets`.
-   **Error Handling:** Added visual InfoBars for errors (e.g., missing keys, network issues) instead of crashing.
