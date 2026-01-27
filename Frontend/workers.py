import time
import os
import tempfile
import threading
import wave
import keyboard
import pyaudio
import pyperclip
import whisper
import gc
import requests
from groq import Groq
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class GlobalSpeechWorker(QObject):
    status_changed = pyqtSignal(str)  # "idle", "recording", "transcribing"
    text_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
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
        
    def initialize(self):
        """Loads the model or API client. Runs in the background thread."""
        try:
            self.p = pyaudio.PyAudio()
            
            if self.use_groq and self.api_key:
                self.groq_client = Groq(api_key=self.api_key)
                print("Groq Client Initialized")
            elif self.use_yandex and self.yandex_key:
                print(f"Yandex SpeechKit Initialized (Folder: {self.yandex_folder_id})")
            else:
                print(f"Loading Whisper model: {self.model_name}")
                self.model = whisper.load_model(self.model_name)
                print("Whisper Model Loaded")
                
        except Exception as e:
            self.error_occurred.emit(f"Initialization Error: {e}")

    def run(self):
        self.running = True
        self.initialize()
        
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