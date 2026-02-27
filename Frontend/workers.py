import time
import os
import tempfile
import threading
import wave
import base64
import math
import shutil
import keyboard
import pyaudio
import pyperclip
import gc
import hashlib
import json
import re
import requests
import subprocess
import sys
import traceback
import urllib.request
import warnings
from groq import Groq
from PyQt6.QtCore import QObject, pyqtSignal, QThread

try:
    import pymorphy3
except ImportError:
    pymorphy3 = None

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
                 use_groq=False, use_yandex=False, yandex_key=None, yandex_folder_id=None,
                 prompt_text="", dictionary_path=None):
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
        self.prompt_text = prompt_text.strip() if prompt_text else ""
        self.dictionary_path = dictionary_path or self.get_default_dictionary_path()
        self._morph_analyzer = None
        self._morph_checked = False
        self._morph_warning_shown = False

    @staticmethod
    def get_default_dictionary_path():
        """Возвращает путь к файлу словаря."""
        if getattr(sys, 'frozen', False):
            appdata_dir = os.path.join(os.environ.get('APPDATA', ''), 'WisperAI')
            os.makedirs(appdata_dir, exist_ok=True)
            return os.path.join(appdata_dir, "dictionary.json")
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, "dictionary.json")

    def load_user_dictionary(self):
        """Загружает правила словаря из файла."""
        if not self.dictionary_path or not os.path.exists(self.dictionary_path):
            return []
        try:
            with open(self.dictionary_path, "r", encoding="utf-8") as dict_file:
                payload = json.load(dict_file)
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                entries = payload.get("entries", [])
                return entries if isinstance(entries, list) else []
        except Exception as e:
            self.event_message.emit(f"Не удалось загрузить словарь: {e}")
        return []

    def get_morph_analyzer(self):
        """Лениво инициализирует морфологический анализатор."""
        if self._morph_checked:
            return self._morph_analyzer

        self._morph_checked = True
        if pymorphy3 is None:
            return None

        try:
            self._morph_analyzer = pymorphy3.MorphAnalyzer()
        except Exception as e:
            if not self._morph_warning_shown:
                self._morph_warning_shown = True
                self.event_message.emit(f"Не удалось запустить pymorphy3: {e}")
            self._morph_analyzer = None
        return self._morph_analyzer

    @staticmethod
    def extract_words(phrase):
        """Извлекает только словесные токены."""
        return re.findall(r"[A-Za-zА-Яа-яЁё0-9\-]+", phrase)

    @staticmethod
    def parse_text_words(text):
        """Возвращает список слов с их позициями в строке."""
        words = []
        for match in re.finditer(r"[A-Za-zА-Яа-яЁё0-9\-]+", text):
            words.append({
                "token": match.group(0),
                "start": match.start(),
                "end": match.end()
            })
        return words

    @staticmethod
    def lemma_token(token, morph):
        """Возвращает лемму токена."""
        if not token:
            return ""
        if morph is None:
            return token.lower()
        parsed = morph.parse(token)
        if not parsed:
            return token.lower()
        return parsed[0].normal_form

    def apply_dictionary_exact(self, text, entries):
        """Прямые замены без лемматизации."""
        normalized_text = text
        sorted_entries = sorted(
            entries,
            key=lambda item: len(str(item.get("source", ""))),
            reverse=True
        )
        for item in sorted_entries:
            source = str(item.get("source", "")).strip()
            target = str(item.get("target", "")).strip()
            if not source:
                continue

            escaped_source = re.escape(source)
            if any(char.isspace() for char in source):
                pattern = escaped_source
            else:
                pattern = rf"\b{escaped_source}\b"
            normalized_text = re.sub(
                pattern,
                lambda _match: target,
                normalized_text,
                flags=re.IGNORECASE
            )
        return normalized_text

    def apply_dictionary_lemma(self, text, entries):
        """Замены по леммам, чтобы покрывать окончания слов."""
        morph = self.get_morph_analyzer()
        if morph is None:
            if not self._morph_warning_shown:
                self._morph_warning_shown = True
                self.event_message.emit(
                    "pymorphy3 не установлен. Применяются только точные замены словаря."
                )
            return text

        lemma_entries = []
        for item in entries:
            source = str(item.get("source", "")).strip()
            target = str(item.get("target", "")).strip()
            source_words = self.extract_words(source)
            if not source_words:
                continue
            source_lemmas = [self.lemma_token(word, morph) for word in source_words]
            lemma_entries.append({
                "lemmas": source_lemmas,
                "target": target
            })

        if not lemma_entries:
            return text

        lemma_entries.sort(key=lambda item: len(item["lemmas"]), reverse=True)
        text_words = self.parse_text_words(text)
        if not text_words:
            return text

        text_lemmas = [self.lemma_token(item["token"], morph) for item in text_words]

        cursor = 0
        output_parts = []
        i = 0
        while i < len(text_words):
            matched_entry = None
            matched_len = 0
            for entry in lemma_entries:
                entry_lemmas = entry["lemmas"]
                entry_len = len(entry_lemmas)
                if i + entry_len > len(text_lemmas):
                    continue
                if text_lemmas[i:i + entry_len] == entry_lemmas:
                    matched_entry = entry
                    matched_len = entry_len
                    break

            if matched_entry is None:
                i += 1
                continue

            start_pos = text_words[i]["start"]
            end_pos = text_words[i + matched_len - 1]["end"]
            output_parts.append(text[cursor:start_pos])
            output_parts.append(matched_entry["target"])
            cursor = end_pos
            i += matched_len

        output_parts.append(text[cursor:])
        return "".join(output_parts)

    def apply_user_dictionary(self, text):
        """Применяет пользовательский словарь к распознанному тексту."""
        if not text:
            return text

        entries = self.load_user_dictionary()
        if not entries:
            return text

        normalized_text = self.apply_dictionary_lemma(text, entries)
        normalized_text = self.apply_dictionary_exact(normalized_text, entries)
        return normalized_text
        
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
                    request_data = {
                        "file": (filename, file.read()),
                        "model": "whisper-large-v3",
                        "temperature": 0,
                        "language": "ru",
                        "response_format": "verbose_json",
                    }
                    if self.prompt_text:
                        request_data["prompt"] = self.prompt_text
                    transcription = self.groq_client.audio.transcriptions.create(**request_data)
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
                initial_prompt = self.prompt_text or "Привет, это проба пера. Пишем текст на русском языке."
                result = self.model.transcribe(
                    filename,
                    language="ru",
                    fp16=False,
                    initial_prompt=initial_prompt
                )
                text = result["text"].strip()
        except Exception as e:
            self.error_occurred.emit(f"Transcription Error: {e}")
        
        if text:
            text = self.apply_user_dictionary(text)

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
            if self.prompt_text:
                prompt_instruction += (
                    "\nДополнительный пользовательский контекст для диктовки:\n"
                    f"{self.prompt_text}"
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
    status = pyqtSignal(str)
    finished = pyqtSignal(str) # Возвращает текст
    error = pyqtSignal(str)
    
    def __init__(self, file_path, yandex_key=None, yandex_folder_id=None, prompt=""):
        super().__init__()
        self.file_path = file_path
        self.yandex_key = yandex_key
        self.yandex_folder_id = yandex_folder_id
        self.prompt = prompt.strip() if prompt else ""

    @staticmethod
    def pretty_api_error(response):
        """Возвращает структурированную ошибку Yandex API."""
        try:
            data = response.json()
        except Exception:
            return response.text

        if "error" in data and isinstance(data["error"], dict):
            err = data["error"]
            code = err.get("code", "unknown")
            msg = err.get("message", "no message")
            details = err.get("details", [])
            return f"API Error [{code}]: {msg}\nDetails: {json.dumps(details, ensure_ascii=False, indent=2)}"
        if "error_code" in data or "error_message" in data:
            code = data.get("error_code", "unknown")
            msg = data.get("error_message", "no message")
            return f"API Error [{code}]: {msg}\nRaw: {json.dumps(data, ensure_ascii=False, indent=2)}"
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def build_exception_details(exc):
        """Формирует полную ошибку с traceback для отображения в UI."""
        return (
            f"{type(exc).__name__}: {exc}\n\n"
            f"Traceback:\n{traceback.format_exc()}"
        )

    @staticmethod
    def detect_container_audio_type(file_path):
        """Определяет тип аудиоконтейнера для Yandex STT v3."""
        ext = os.path.splitext(file_path.lower())[1]
        mapping = {
            ".mp3": "MP3",
            ".wav": "WAV",
            ".ogg": "OGG_OPUS",
            ".opus": "OGG_OPUS"
        }
        return mapping.get(ext, "")

    @staticmethod
    def extract_transcription_text(raw_payload):
        """Извлекает текст из alternatives ответа getRecognition (JSON/NDJSON)."""
        candidates = []
        seen = set()

        def add_candidate(value):
            if not isinstance(value, str):
                return
            text_value = " ".join(value.split()).strip()
            if not text_value:
                return
            if text_value in seen:
                return
            seen.add(text_value)
            candidates.append(text_value)

        def walk_for_alternatives(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "alternatives" and isinstance(value, list):
                        for alt in value:
                            if isinstance(alt, dict):
                                add_candidate(alt.get("text", ""))
                    else:
                        walk_for_alternatives(value)
            elif isinstance(node, list):
                for item in node:
                    walk_for_alternatives(item)

        parsed_any = False
        try:
            parsed = json.loads(raw_payload)
            parsed_any = True
            walk_for_alternatives(parsed)
        except Exception:
            pass

        if not parsed_any:
            for line in raw_payload.splitlines():
                stripped = line.strip().strip(",")
                if not stripped:
                    continue
                try:
                    parsed_line = json.loads(stripped)
                    walk_for_alternatives(parsed_line)
                    parsed_any = True
                except Exception:
                    continue

        if not candidates:
            return raw_payload.strip()

        # Убираем однословные токены и промежуточные дубли длинных фрагментов.
        filtered = []
        filtered_norm = []
        for text_value in candidates:
            if len(text_value.split()) < 3:
                continue
            norm_value = text_value.lower()
            replaced = False
            for i, existing_norm in enumerate(filtered_norm):
                if norm_value in existing_norm:
                    replaced = True
                    break
                if existing_norm in norm_value:
                    filtered[i] = text_value
                    filtered_norm[i] = norm_value
                    replaced = True
                    break
            if not replaced:
                filtered.append(text_value)
                filtered_norm.append(norm_value)

        if filtered:
            return "\n\n".join(filtered).strip()
        return "\n\n".join(candidates).strip()

    def yandex_gpt_correct(self, text):
        """Постобработка текста через YandexGPT (опционально)."""
        if not text or not self.yandex_folder_id:
            return text

        try:
            gpt_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
            gpt_headers = {
                "Authorization": f"Api-key {self.yandex_key}",
                "x-folder-id": self.yandex_folder_id,
                "Content-Type": "application/json"
            }
            prompt_instruction = (
                "Входной текст нужно исправить по грамматике, пунктуации и орфографии. "
                "Верни корректный русский литературный текст."
            )
            if self.prompt:
                prompt_instruction += (
                    "\nДополнительный пользовательский контекст для расшифровки:\n"
                    f"{self.prompt}"
                )
            gpt_data = {
                "modelUri": f"gpt://{self.yandex_folder_id}/yandexgpt-lite/latest",
                "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 2000},
                "messages": [
                    {"role": "system", "text": prompt_instruction},
                    {"role": "user", "text": text}
                ]
            }
            gpt_response = requests.post(
                gpt_url,
                headers=gpt_headers,
                json=gpt_data,
                verify=False,
                timeout=120
            )
            if gpt_response.status_code != 200:
                print("YandexGPT File Correction Error:")
                print(self.pretty_api_error(gpt_response))
                return text

            alternatives = gpt_response.json().get("result", {}).get("alternatives", [])
            if not alternatives:
                return text
            corrected = alternatives[0].get("message", {}).get("text", "").strip()
            return corrected if corrected else text
        except Exception:
            print("YandexGPT File Correction Exception:")
            traceback.print_exc()
            return text

    def run(self):
        try:
            self.status.emit("Проверка файла...")
            if not os.path.exists(self.file_path):
                self.error.emit(f"Файл не найден: {self.file_path}")
                return
            if not self.yandex_key:
                self.error.emit("Не задан YANDEX_API_KEY.")
                return
            if not self.yandex_folder_id:
                self.error.emit("Не задан YANDEX_FOLDER_ID.")
                return

            container_type = self.detect_container_audio_type(self.file_path)
            if not container_type:
                self.error.emit(
                    "Неподдерживаемый формат файла. Используйте mp3, wav, ogg или opus."
                )
                return

            self.status.emit("Чтение аудиофайла...")
            with open(self.file_path, "rb") as audio_file:
                audio_bytes = audio_file.read()

            self.status.emit("Подготовка асинхронного запроса Yandex SpeechKit...")
            request_data = {
                "content": base64.b64encode(audio_bytes).decode("utf-8"),
                "recognitionModel": {
                    "model": "general",
                    "audioFormat": {
                        "containerAudio": {
                            "containerAudioType": container_type
                        }
                    },
                    "languageRestriction": {
                        "restrictionType": "WHITELIST",
                        "languageCode": ["ru-RU"]
                    },
                    "textNormalization": {
                        "textNormalization": "TEXT_NORMALIZATION_ENABLED",
                        "phoneFormattingMode": "PHONE_FORMATTING_MODE_DISABLED",
                        "profanityFilter": True,
                        "literatureText": True
                    }
                },
                "speakerLabeling": {
                    "speakerLabeling": "SPEAKER_LABELING_DISABLED"
                }
            }

            headers = {
                "Authorization": f"Api-key {self.yandex_key}",
                "x-folder-id": self.yandex_folder_id
            }

            create_url = "https://stt.api.cloud.yandex.net/stt/v3/recognizeFileAsync"
            create_response = requests.post(
                create_url,
                headers=headers,
                json=request_data,
                verify=False,
                timeout=120
            )
            if create_response.status_code != 200:
                api_error = self.pretty_api_error(create_response)
                print("Yandex SpeechKit Error:")
                print(api_error)
                self.error.emit(f"Yandex Error: {create_response.status_code}\n{api_error}")
                return

            operation_id = create_response.json().get("id")
            if not operation_id:
                self.error.emit("Yandex SpeechKit не вернул operation id.")
                return

            self.status.emit(f"Операция создана: {operation_id}. Ожидание завершения...")
            operation_url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"

            while True:
                operation_response = requests.get(
                    operation_url,
                    headers=headers,
                    verify=False,
                    timeout=120
                )
                if operation_response.status_code != 200:
                    api_error = self.pretty_api_error(operation_response)
                    raise RuntimeError(
                        f"Ошибка проверки операции: {operation_response.status_code}\n{api_error}"
                    )

                operation_data = operation_response.json()
                if operation_data.get("done"):
                    if "error" in operation_data:
                        raise RuntimeError(
                            "Операция завершилась с ошибкой:\n"
                            f"{json.dumps(operation_data['error'], ensure_ascii=False, indent=2)}"
                        )
                    break

                self.status.emit("Yandex SpeechKit обрабатывает файл, ожидаем результат...")
                time.sleep(3)

            self.status.emit("Получение результата распознавания...")
            result_response = requests.get(
                "https://stt.api.cloud.yandex.net/stt/v3/getRecognition",
                headers=headers,
                params={"operationId": operation_id},
                verify=False,
                timeout=120
            )
            if result_response.status_code != 200:
                api_error = self.pretty_api_error(result_response)
                raise RuntimeError(
                    f"Ошибка получения результата: {result_response.status_code}\n{api_error}"
                )

            text = self.extract_transcription_text(result_response.text)
            if self.prompt and text:
                self.status.emit("Постобработка текста через YandexGPT...")
                text = self.yandex_gpt_correct(text)

            self.status.emit("Распознавание через Yandex SpeechKit завершено.")
            self.finished.emit(text)
            
        except Exception as e:
            print("TranscribeWorker Exception:")
            traceback.print_exc()
            self.error.emit(self.build_exception_details(e))


class ChunkedTranscribeWorker(TranscribeWorker):
    def __init__(
        self,
        file_path,
        yandex_key=None,
        yandex_folder_id=None,
        prompt="",
        max_part_mb=25,
        target_part_mb=24,
        mp3_bitrate_kbps=96
    ):
        super().__init__(
            file_path=file_path,
            yandex_key=yandex_key,
            yandex_folder_id=yandex_folder_id,
            prompt=prompt
        )
        self.max_part_bytes = max_part_mb * 1024 * 1024
        self.target_part_bytes = target_part_mb * 1024 * 1024
        self.mp3_bitrate_kbps = mp3_bitrate_kbps

    @staticmethod
    def get_audio_duration_seconds(ffprobe_bin, file_path):
        """Возвращает длительность аудио в секундах через ffprobe."""
        command = [
            ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                "Не удалось определить длительность файла через ffprobe:\n"
                f"{result.stderr.strip()}"
            )
        try:
            return float(result.stdout.strip())
        except ValueError as exc:
            raise RuntimeError("ffprobe вернул некорректную длительность файла.") from exc

    @staticmethod
    def convert_part_to_mp3(ffmpeg_bin, input_path, output_path, start_sec, duration_sec, bitrate_kbps):
        """Конвертирует часть исходного файла в mp3 с заданным битрейтом."""
        command = [
            ffmpeg_bin,
            "-y",
            "-ss",
            f"{start_sec:.3f}",
            "-t",
            f"{duration_sec:.3f}",
            "-i",
            input_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            f"{bitrate_kbps}k",
            output_path
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                "Ошибка ffmpeg при конвертации части файла:\n"
                f"{result.stderr.strip()}"
            )

    def transcribe_part(self, part_path, part_number, total_parts):
        """Отправляет одну mp3-часть в Yandex SpeechKit Async v3."""
        with open(part_path, "rb") as part_file:
            part_bytes = part_file.read()

        headers = {
            "Authorization": f"Api-key {self.yandex_key}",
            "x-folder-id": self.yandex_folder_id
        }
        request_data = {
            "content": base64.b64encode(part_bytes).decode("utf-8"),
            "recognitionModel": {
                "model": "general",
                "audioFormat": {
                    "containerAudio": {
                        "containerAudioType": "MP3"
                    }
                },
                "languageRestriction": {
                    "restrictionType": "WHITELIST",
                    "languageCode": ["ru-RU"]
                },
                "textNormalization": {
                    "textNormalization": "TEXT_NORMALIZATION_ENABLED",
                    "phoneFormattingMode": "PHONE_FORMATTING_MODE_DISABLED",
                    "profanityFilter": True,
                    "literatureText": True
                }
            },
            "speakerLabeling": {
                "speakerLabeling": "SPEAKER_LABELING_DISABLED"
            }
        }

        self.status.emit(f"Отправка части {part_number}/{total_parts} в Yandex SpeechKit...")
        create_response = requests.post(
            "https://stt.api.cloud.yandex.net/stt/v3/recognizeFileAsync",
            headers=headers,
            json=request_data,
            verify=False,
            timeout=120
        )
        if create_response.status_code != 200:
            api_error = self.pretty_api_error(create_response)
            raise RuntimeError(
                f"Yandex Error: {create_response.status_code}\n"
                f"Часть: {part_number}/{total_parts}\n{api_error}"
            )

        operation_id = create_response.json().get("id")
        if not operation_id:
            raise RuntimeError(f"Yandex не вернул operation id для части {part_number}/{total_parts}.")

        operation_url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"
        while True:
            operation_response = requests.get(
                operation_url,
                headers=headers,
                verify=False,
                timeout=120
            )
            if operation_response.status_code != 200:
                api_error = self.pretty_api_error(operation_response)
                raise RuntimeError(
                    f"Ошибка проверки операции для части {part_number}/{total_parts}: "
                    f"{operation_response.status_code}\n{api_error}"
                )

            operation_data = operation_response.json()
            if operation_data.get("done"):
                if "error" in operation_data:
                    raise RuntimeError(
                        f"Операция завершилась с ошибкой для части {part_number}/{total_parts}:\n"
                        f"{json.dumps(operation_data['error'], ensure_ascii=False, indent=2)}"
                    )
                break

            self.status.emit(
                f"Yandex обрабатывает часть {part_number}/{total_parts}, ожидаем результат..."
            )
            time.sleep(2)

        result_response = requests.get(
            "https://stt.api.cloud.yandex.net/stt/v3/getRecognition",
            headers=headers,
            params={"operationId": operation_id},
            verify=False,
            timeout=120
        )
        if result_response.status_code != 200:
            api_error = self.pretty_api_error(result_response)
            raise RuntimeError(
                f"Ошибка получения результата для части {part_number}/{total_parts}: "
                f"{result_response.status_code}\n{api_error}"
            )

        text = self.extract_transcription_text(result_response.text).strip()
        if self.prompt and text:
            self.status.emit(f"Постобработка части {part_number}/{total_parts} через YandexGPT...")
            text = self.yandex_gpt_correct(text)
        return text

    def run(self):
        try:
            self.status.emit("Проверка параметров обработки...")
            if not os.path.exists(self.file_path):
                self.error.emit(f"Файл не найден: {self.file_path}")
                return
            if not self.yandex_key:
                self.error.emit("Не задан YANDEX_API_KEY.")
                return
            if not self.yandex_folder_id:
                self.error.emit("Не задан YANDEX_FOLDER_ID.")
                return

            ffmpeg_bin = shutil.which("ffmpeg")
            ffprobe_bin = shutil.which("ffprobe")
            if not ffmpeg_bin or not ffprobe_bin:
                self.error.emit(
                    "Не найдены ffmpeg/ffprobe. Установите ffmpeg и добавьте его в PATH."
                )
                return

            duration_seconds = self.get_audio_duration_seconds(ffprobe_bin, self.file_path)
            if duration_seconds <= 0:
                self.error.emit("Не удалось определить длительность аудиофайла.")
                return

            part_duration_seconds = max(
                60,
                int((self.target_part_bytes * 8) / (self.mp3_bitrate_kbps * 1000))
            )
            total_parts = max(1, math.ceil(duration_seconds / part_duration_seconds))

            self.status.emit(
                f"Запущена обработка большого файла: частей {total_parts}, цель <= 25MB на часть."
            )

            transcribed_parts = []
            with tempfile.TemporaryDirectory(prefix="wisper_chunks_") as temp_dir:
                for part_index in range(total_parts):
                    start_sec = part_index * part_duration_seconds
                    remaining = max(0.0, duration_seconds - start_sec)
                    if remaining <= 0:
                        continue
                    current_duration = min(part_duration_seconds, remaining)

                    part_number = part_index + 1
                    part_path = os.path.join(temp_dir, f"part_{part_number:03d}.mp3")
                    self.status.emit(
                        f"Конвертация части {part_number}/{total_parts} в mp3 "
                        f"({self.mp3_bitrate_kbps} kbps)..."
                    )
                    self.convert_part_to_mp3(
                        ffmpeg_bin=ffmpeg_bin,
                        input_path=self.file_path,
                        output_path=part_path,
                        start_sec=start_sec,
                        duration_sec=current_duration,
                        bitrate_kbps=self.mp3_bitrate_kbps
                    )

                    part_size = os.path.getsize(part_path)
                    if part_size > self.max_part_bytes:
                        reduced = False
                        for fallback_bitrate in [80, 64, 48, 32]:
                            if fallback_bitrate >= self.mp3_bitrate_kbps:
                                continue
                            self.status.emit(
                                f"Часть {part_number}/{total_parts} > 25MB, повторная конвертация "
                                f"с битрейтом {fallback_bitrate} kbps..."
                            )
                            self.convert_part_to_mp3(
                                ffmpeg_bin=ffmpeg_bin,
                                input_path=self.file_path,
                                output_path=part_path,
                                start_sec=start_sec,
                                duration_sec=current_duration,
                                bitrate_kbps=fallback_bitrate
                            )
                            part_size = os.path.getsize(part_path)
                            if part_size <= self.max_part_bytes:
                                reduced = True
                                break
                        if not reduced and part_size > self.max_part_bytes:
                            raise RuntimeError(
                                f"Не удалось уменьшить часть {part_number}/{total_parts} до 25MB. "
                                f"Текущий размер: {part_size} байт."
                            )

                    part_text = self.transcribe_part(
                        part_path=part_path,
                        part_number=part_number,
                        total_parts=total_parts
                    )
                    if part_text:
                        transcribed_parts.append(part_text)

            final_text = "\n\n".join(transcribed_parts).strip()
            if not final_text:
                self.error.emit("Распознавание завершено, но текст пустой.")
                return

            self.status.emit("Склейка частей завершена.")
            self.finished.emit(final_text)
        except Exception as exc:
            print("ChunkedTranscribeWorker Exception:")
            traceback.print_exc()
            self.error.emit(self.build_exception_details(exc))
