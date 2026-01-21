# Repository Guidelines

## Project Structure & Modules
- Root Python scripts: `global_speech.py` (hotkey-based live dictation), `overlay.py` (Tk overlay indicator), `transcribe.py` (batch transcription). Keep shared constants (`HOTKEY`, `MODEL_SIZE`, `LANGUAGE`) near the top of `global_speech.py`.
- Launchers: `start_whisper.bat` (console) and `silent_start.vbs` (hidden). `setup.bat` bootstraps the environment on Windows.
- Dependencies live in `requirements.txt`; the local `venv/` is disposable and should not be committed. Media or archives (e.g., `WHISPER.7z`) stay out of source control unless intentionally versioned.

## Build, Test & Development Commands
- Create/refresh env: `python -m venv venv` then `.\venv\Scripts\activate` and `pip install -r requirements.txt`.
- Verify FFmpeg availability (required by Whisper): `ffmpeg -version`.
- Run live dictation: `python global_speech.py` (or `start_whisper.bat`); for background launch: `cscript //nologo silent_start.vbs`.
- Transcribe a file: `python transcribe.py path\to\audio.mp3 small`. Output text is saved alongside the audio.

## Coding Style & Naming Conventions
- Python 3.x, PEP 8, 4-space indents. Prefer clear, lowercase_with_underscores for functions/variables; CapWords for classes.
- Keep logging via the existing `log()` helper so timestamps stay consistent; keep user-facing text concise.
- Avoid embedding secrets or user-specific paths. Keep comments ASCII and purposeful; short docstrings for new public functions.

## Testing Guidelines
- No automated test suite yet; perform quick manual checks:
  - Launch dictation, hold/release `F8`, confirm overlay shows red (recording) then yellow (recognizing) and text pastes into the active window.
  - Try a short (<60s) and a near-60s recording to ensure the timeout path works.
  - Run `python transcribe.py sample.wav small` and confirm a `.txt` is emitted with reasonable output.
- If you add tests, keep them in a `tests/` folder and mirror the script names (e.g., `test_global_speech.py`).

## Commit & Pull Request Guidelines
- Keep changes small and atomic. Use concise messages like `feat: add overlay status update` or `fix: handle empty recording`.
- Describe manual test steps in the PR/commit description (commands run, hotkey flows verified). Attach screenshots/gifs if you change the overlay or user-visible behavior.
- Document configuration changes (hotkey, model size, language) in the PR so reviewers can reproduce.

## Security & Configuration Tips
- Ensure FFmpeg is on `PATH` before running; Whisper downloads models on first use - avoid bundling them in commits.
- Do not commit `venv/` or machine-specific files. Check in only source, scripts, and minimal assets needed to run.
- Mic access is required; if dictation silently fails, re-check audio device permissions and `LANGUAGE`/`MODEL_SIZE` settings at the top of `global_speech.py`.
