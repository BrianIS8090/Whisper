import time
import os
import tempfile
import threading
import wave
import keyboard
import pyaudio
import pyperclip
import gc
import hashlib
import requests
import subprocess
import sys
import urllib.request
import warnings
from groq import Groq
from PyQt6.QtCore import QObject, pyqtSignal, QThread

# Патч для скрытия консольного окна ffmpeg на Windows
if sys.platform == "win32":
    _original_popen = subprocess.Popen
    
    def _popen_no_console(*args, **kwargs):
        # Добавляем флаг CREATE_NO_WINDOW если не указан creationflags
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        return _original_popen(*args, **kwargs)
    
    subprocess.Popen = _popen_no_console

# Импортируем whisper ПОСЛЕ патча subprocess
import whisper

class GlobalSpeechWorker(QObject):
    status_changed = pyqtSignal(str)  # "initializing", "ready", "idle", "recording", "transcribing", "model_downloading:<pct>"
    text_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    event_message = pyqtSignal(str)
    
    def __init__(self, api_key=None, model_name="small", hotkey="F8", 
                 use_groq=False, use_yandex=False, yandex_key=None, yandex_folder_id=None):
        super().__init__()
        self.api_key = api_key
        self.yandex_key = yandex_key
        self.yandex_folder_id = yandex_folder_id
        self.model_name = model_name
        self.hotkey = hotkey
        self.use_groq = use_groq
        self.use_yandex = use_yandex
        self.running = False
        self.groq_client = None
        self.model = None
        self.p = None
        self.initialized = False
        self._last_download_percent = -1
        self._last_logged_bucket = -1
        
    def initialize(self):
        """Loads the model or API client. Runs in the background thread."""
        self.initialized = False
        try:
            self.status_changed.emit("initializing")
            self.p = pyaudio.PyAudio()
            self.event_message.emit("Инициализация аудио-подсистемы...")
            
            if self.use_groq and self.api_key:
                self.event_message.emit("Инициализация Groq API...")
                self.groq_client = Groq(api_key=self.api_key)
                print("Groq Client Initialized")
            elif self.use_yandex and self.yandex_key:
                self.event_message.emit("Инициализация Yandex SpeechKit...")
                print(f"Yandex SpeechKit Initialized (Folder: {self.yandex_folder_id})")
            else:
                self.event_message.emit(f"Инициализация локальной модели Whisper '{self.model_name}'...")
                self.model = self.load_local_model_with_status(self.model_name)
                print("Whisper Model Loaded")

            self.initialized = True
            self.status_changed.emit("ready")
            self.event_message.emit("Служба инициализирована и готова к диктовке (F8).")
        except Exception as e:
            self.running = False
            self.error_occurred.emit(f"Initialization Error: {e}")

    def run(self):
        self.running = True
        self.initialize()

        if not self.initialized:
            if self.p:
                self.p.terminate()
            return
        
        # Hotkey listener loop
        print(f"Worker started. Waiting for {self.hotkey}...")
        
        while self.running:
            try:
                if keyboard.is_pressed(self.hotkey):
                    self.perform_recording_cycle()
                
                time.sleep(0.05) # Prevent high CPU usage
            except Exception as e:
                self.error_occurred.emit(str(e))
                time.sleep(1)

        if self.p:
            self.p.terminate()

    def get_whisper_cache_dir(self):
        default_cache = os.path.join(os.path.expanduser("~"), ".cache")
        return os.path.join(os.getenv("XDG_CACHE_HOME", default_cache), "whisper")

    def emit_download_progress(self, downloaded_size, total_size):
        if not total_size:
            return

        percent = int((downloaded_size * 100) / total_size)
        percent = max(0, min(100, percent))

        if percent != self._last_download_percent:
            self._last_download_percent = percent
            self.status_changed.emit(f"model_downloading:{percent}")

        bucket = percent // 10
        if bucket != self._last_logged_bucket:
            self._last_logged_bucket = bucket
            self.event_message.emit(f"Скачивание модели Whisper: {percent}%")

    def load_local_model_with_status(self, model_name):
        if model_name not in whisper._MODELS:
            self.event_message.emit(f"Загрузка модели из файла: {model_name}")
            return whisper.load_model(model_name)

        download_root = self.get_whisper_cache_dir()
        model_url = whisper._MODELS[model_name]
        download_target = os.path.join(download_root, os.path.basename(model_url))

        original_download = whisper._download

        def download_with_progress(url, root, in_memory):
            os.makedirs(root, exist_ok=True)
            target = os.path.join(root, os.path.basename(url))
            expected_hash = url.split("/")[-2]

            if os.path.exists(target) and not os.path.isfile(target):
                raise RuntimeError(f"{target} exists and is not a regular file")

            if os.path.isfile(target):
                self.event_message.emit(f"Найден файл модели в кэше: {os.path.basename(target)}")
                self.status_changed.emit("model_validating")
                with open(target, "rb") as f:
                    model_bytes = f.read()
                file_hash = hashlib.sha256(model_bytes).hexdigest()
                if file_hash == expected_hash:
                    self.event_message.emit("Файл модели валиден, скачивание не требуется.")
                    self.status_changed.emit("model_loading")
                    return model_bytes if in_memory else target

                warnings.warn(
                    f"{target} exists, but the SHA256 checksum does not match; re-downloading the file"
                )
                self.event_message.emit("Найдена повреждённая модель (не совпадает SHA256), выполняется повторное скачивание.")

            self.status_changed.emit("model_downloading:0")
            self._last_download_percent = -1
            self._last_logged_bucket = -1
            self.event_message.emit(f"Скачивание модели Whisper '{model_name}'...")

            downloaded_size = 0
            with urllib.request.urlopen(url) as source, open(target, "wb") as output:
                total_size = int(source.info().get("Content-Length", "0"))
                while True:
                    buffer = source.read(8192)
                    if not buffer:
                        break
                    output.write(buffer)
                    downloaded_size += len(buffer)
                    self.emit_download_progress(downloaded_size, total_size)

            model_bytes = open(target, "rb").read()
            file_hash = hashlib.sha256(model_bytes).hexdigest()
            if file_hash != expected_hash:
                raise RuntimeError(
                    "Model has been downloaded but the SHA256 checksum does not match. Please retry loading the model."
                )

            self.status_changed.emit("model_downloading:100")
            self.event_message.emit("Скачивание модели завершено.")
            self.status_changed.emit("model_loading")
            return model_bytes if in_memory else target

        try:
            whisper._download = download_with_progress
            if os.path.isfile(download_target):
                self.event_message.emit(
                    f"Подготовка локальной модели '{model_name}' (проверка целостности и загрузка в память)..."
                )
            else:
                self.event_message.emit(
                    f"Локальная модель '{model_name}' не найдена в кэше, начнется скачивание."
                )

            model = whisper.load_model(model_name, download_root=download_root)
            if os.path.isfile(download_target):
                self.event_message.emit(f"Локальная модель '{model_name}' успешно загружена.")
            return model
        finally:
            whisper._download = original_download

    def perform_recording_cycle(self):
        self.status_changed.emit("recording")
        
        temp_filename = ""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_filename = temp_audio.name

        if self.record_audio(temp_filename):
            if os.path.getsize(temp_filename) > 2000:
                self.status_changed.emit("transcribing")
                text = self.transcribe(temp_filename)
                
                if text:
                    self.text_ready.emit(text)
                    self.paste_text(text)
            else:
                print("Audio too short, ignoring.")
        
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except:
                pass
                
        self.status_changed.emit("idle")
        # Debounce
        time.sleep(0.5)

    def record_audio(self, filename):
        chunk = 1024
        format = pyaudio.paInt16
        channels = 1
        rate = 48000 # Standard for Yandex
        frames = []
        
        try:
            stream = self.p.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
            
            start_time = time.time()
            max_duration = 30 # Yandex v1 limit is 30s
            
            while keyboard.is_pressed(self.hotkey) and self.running:
                if time.time() - start_time > max_duration:
                    break
                data = stream.read(chunk, exception_on_overflow=False)
                frames.append(data)

            stream.stop_stream()
            stream.close()
            
            if not frames:
                return False

            wf = wave.open(filename, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(self.p.get_sample_size(format))
            wf.setframerate(rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Recording Error: {e}")
            return False

    def transcribe(self, filename):
        text = ""
        try:
            if self.use_groq and self.groq_client:
                with open(filename, "rb") as file:
                    transcription = self.groq_client.audio.transcriptions.create(
                        file=(filename, file.read()),
                        model="whisper-large-v3",
                        temperature=0,
                        language="ru",
                        response_format="verbose_json",
                    )
                    text = transcription.text.strip()
            
            elif self.use_yandex and self.yandex_key:
                # Read WAV and strip 44-byte header for LPCM format
                with open(filename, "rb") as f:
                    data = f.read()[44:] 
                
                params = {
                    "lang": "ru-RU",
                    "format": "lpcm",
                    "sampleRateHertz": 48000,
                    "topic": "general"
                }
                if self.yandex_folder_id:
                    params["folderId"] = self.yandex_folder_id

                headers = {
                    "Authorization": f"Api-Key {self.yandex_key}"
                }
                
                url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
                response = requests.post(url, headers=headers, params=params, data=data)
                
                if response.status_code != 200:
                    error_msg = response.text
                    try:
                        error_msg = response.json().get("error_message", response.text)
                    except: pass
                    self.error_occurred.emit(f"Yandex Error: {error_msg}")
                else:
                    result = response.json()
                    text = result.get("result", "").strip()
                    
                    # --- YandexGPT Post-Processing ---
                    if text and self.yandex_folder_id:
                        text = self.yandex_gpt_correct(text)

            elif self.model:
                result = self.model.transcribe(filename, language="ru", fp16=False, initial_prompt="Привет, это проба пера. Пишем текст на русском языке.")
                text = result["text"].strip()
        except Exception as e:
            self.error_occurred.emit(f"Transcription Error: {e}")
        
        # Cleanup
        gc.collect()
        return text

    def yandex_gpt_correct(self, text):
        """
        Sends text to YandexGPT for grammar/punctuation correction 
        using the specific instruction provided by the user.
        """
        try:
            url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
            
            headers = {
                "Authorization": f"Api-Key {self.yandex_key}",
                "x-folder-id": self.yandex_folder_id,
                "Content-Type": "application/json"
            }
            
            prompt_instruction = (
                "Входной текст, который тебе подается, нужно проверить на грамматику, пунктуацию, "
                "на орфографию, выдать текст в правильном русском литературном формате. "
                "Если это числовые или размерные параметры, то мы пишем числа 1, 2, 3 и т.п."
            )
            
            data = {
                "modelUri": f"gpt://{self.yandex_folder_id}/yandexgpt-lite/latest",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.3, # Low temperature for more deterministic correction
                    "maxTokens": 2000
                },
                "messages": [
                    {
                        "role": "system",
                        "text": prompt_instruction
                    },
                    {
                        "role": "user",
                        "text": text
                    }
                ]
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                alternatives = result.get("result", {}).get("alternatives", [])
                if alternatives:
                    corrected_text = alternatives[0].get("message", {}).get("text", "")
                    if corrected_text:
                        print(f"YandexGPT Correction: '{text}' -> '{corrected_text}'")
                        return corrected_text.strip()
            else:
                print(f"YandexGPT Error ({response.status_code}): {response.text}")
                
        except Exception as e:
            print(f"YandexGPT Exception: {e}")
            
        return text # Return original text on failure

    def paste_text(self, text):
        try:
            pyperclip.copy(text)
            time.sleep(0.1)
            keyboard.send('ctrl+v')
        except Exception as e:
            self.error_occurred.emit(f"Paste Error: {e}")

    def stop(self):
        self.running = False

class TranscribeWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str) # returns text
    error = pyqtSignal(str)
    
    def __init__(self, file_path, api_key=None, use_groq=False, model_name="small", 
                 use_yandex=False, yandex_key=None, yandex_folder_id=None):
        super().__init__()
        self.file_path = file_path
        self.api_key = api_key
        self.use_groq = use_groq
        self.model_name = model_name
        self.use_yandex = use_yandex
        self.yandex_key = yandex_key
        self.yandex_folder_id = yandex_folder_id

    def run(self):
        try:
            if not os.path.exists(self.file_path):
                self.error.emit("File not found")
                return

            text = ""
            if self.use_groq and self.api_key:
                client = Groq(api_key=self.api_key)
                with open(self.file_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(self.file_path, file.read()),
                        model="whisper-large-v3",
                        temperature=0,
                        language="ru",
                        response_format="verbose_json",
                    )
                    text = transcription.text
            elif self.use_yandex and self.yandex_key:
                with open(self.file_path, "rb") as f:
                    data = f.read()
                
                params = {"lang": "ru-RU", "topic": "general"}
                if self.yandex_folder_id: params["folderId"] = self.yandex_folder_id
                
                headers = {"Authorization": f"Api-Key {self.yandex_key}"}
                url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
                
                if self.file_path.endswith(".wav"):
                    params["format"] = "lpcm"
                    params["sampleRateHertz"] = 48000
                    data = data[44:]

                response = requests.post(url, headers=headers, params=params, data=data)
                if response.status_code == 200:
                    text = response.json().get("result", "")
                    
                    # --- YandexGPT Post-Processing ---
                    if text and self.yandex_folder_id:
                        try:
                            # We reuse the logic. ideally this should be a shared function, 
                            # but for now we inline it to match the GlobalSpeechWorker behavior.
                            gpt_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
                            gpt_headers = {
                                "Authorization": f"Api-Key {self.yandex_key}",
                                "x-folder-id": self.yandex_folder_id,
                                "Content-Type": "application/json"
                            }
                            prompt_instruction = (
                                "Входной текст, который тебе подается, нужно проверить на грамматику, пунктуацию, "
                                "на орфографию, выдать текст в правильном русском литературном формате. "
                                "Если это числовые или размерные параметры, то мы пишем числа 1, 2, 3 и т.п."
                            )
                            gpt_data = {
                                "modelUri": f"gpt://{self.yandex_folder_id}/yandexgpt-lite/latest",
                                "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 2000},
                                "messages": [
                                    {"role": "system", "text": prompt_instruction},
                                    {"role": "user", "text": text}
                                ]
                            }
                            gpt_response = requests.post(gpt_url, headers=gpt_headers, json=gpt_data)
                            if gpt_response.status_code == 200:
                                alts = gpt_response.json().get("result", {}).get("alternatives", [])
                                if alts:
                                    corrected = alts[0].get("message", {}).get("text", "")
                                    if corrected:
                                        text = corrected.strip()
                        except Exception as val_err:
                            print(f"YandexGPT File Correction Error: {val_err}")

                else:
                    self.error.emit(f"Yandex Error: {response.text}")
                    return
            else:
                model = whisper.load_model(self.model_name)
                result = model.transcribe(self.file_path, fp16=False, language="ru")
                text = result["text"]
            
            self.finished.emit(text)
            
        except Exception as e:
            self.error.emit(str(e))
