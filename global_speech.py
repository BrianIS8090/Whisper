import whisper
import keyboard
import pyaudio
import wave
import os
import pyperclip
import time
import tempfile
import threading
import ctypes
import msvcrt
import gc
from datetime import datetime
from overlay import RecordingOverlay
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def disable_quick_edit():
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        h_stdin = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(h_stdin, ctypes.byref(mode)):
            new_mode = mode.value & ~0x0040  # ENABLE_QUICK_EDIT_MODE
            new_mode |= 0x0080  # ENABLE_EXTENDED_FLAGS
            kernel32.SetConsoleMode(h_stdin, new_mode)
    except Exception:
        pass


# --- НАСТРОЙКИ ---
HOTKEY = 'F8'          # Клавиша, которую нужно удерживать для записи
MODEL_SIZE = "small"   # Модель (tiny, base, small, medium, large)
LANGUAGE = "ru"        # Язык распознавания
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # API ключ для Groq (если есть)
# -----------------

def record_audio(filename, p, overlay):
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 44100
    # p = pyaudio.PyAudio() # Теперь передается извне
    stream = None
    frames = []
    
    try:
        try:
            stream = p.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
        except Exception as e:
            log(f"Ошибка открытия микрофона: {e}")
            return False

        log(f"Запись идет... (Отпустите {HOTKEY} для остановки)")
        overlay.set_status("Запись...", "red")
        overlay.show()
        
        start_time = time.time()
        max_duration = 60  # Максимальная длительность записи в секундах
        
        # Записываем пока клавиша нажата
        while keyboard.is_pressed(HOTKEY):
            if time.time() - start_time > max_duration:
                log("Превышено максимальное время записи (60 сек). Остановка.")
                break
                
            try:
                # exception_on_overflow=False предотвращает краш при переполнении буфера
                data = stream.read(chunk, exception_on_overflow=False)
                frames.append(data)
            except IOError as e:
                log(f"Ошибка чтения аудиопотока: {e}")
                break

        log("Запись завершена.")
        
    except Exception as e:
        log(f"Критическая ошибка при записи: {e}")
        return False
    finally:
        # Убираем overlay.hide() отсюда, чтобы он продолжал гореть во время распознавания
        if stream:
            stream.stop_stream()
            stream.close()
        # p.terminate() # Не закрываем здесь, так как объект общий

    # Если ничего не записали, выходим
    if not frames:
        return False

    # Сохраняем в файл
    try:
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))
        wf.close()
    except Exception as e:
        log(f"Ошибка сохранения файла: {e}")
        return False
        
    return True

def main():
    global GROQ_API_KEY
    use_groq = False
    model = None
    
    print("---------------------------------------------------------")
    print("Выберите режим работы:")
    if GROQ_API_KEY:
        print("1. Локальная модель Whisper (оффлайн)")
        print("2. Groq API (whisper-large-v3, требуется интернет)")
    else:
        print("1. Локальная модель Whisper (оффлайн)")
        print("   (Groq API недоступен, так как не найден GROQ_API_KEY)")
    
    print("Нажмите цифру 1 или 2 (если доступно). По умолчанию: 1")
    
    mode_choice = "1"
    try:
        start_time = time.time()
        while (time.time() - start_time) < 10:
            if msvcrt.kbhit():
                key = msvcrt.getwche()
                if key in ['\r', '\n']:
                    break
                mode_choice = key
                print()
                break
            time.sleep(0.05)
        else:
            print("\nВремя вышло. Выбран режим по умолчанию (Локальный).")
    except Exception:
        pass

    if GROQ_API_KEY and mode_choice == "2":
        use_groq = True
        print("Выбран режим: Groq API")
        try:
            groq_client = Groq(api_key=GROQ_API_KEY)
        except Exception as e:
            print(f"Ошибка инициализации Groq клиента: {e}")
            return
    else:
        print("Выбран режим: Локальная модель")
        print("Выберите модель Whisper:")
        print("1. tiny (самая быстрая, наименее точная)")
        print("2. base (быстрая, чуть точнее)")
        print("3. small (сбалансированная) [по умолчанию]")
        print("4. medium (медленная, высокая точность)")
        print("5. large (очень медленная, максимальная точность)")
        print("Нажмите цифру 1-5 или Enter. Автовыбор через 10 секунд...")
        
        choice = "3"
        try:
            start_time = time.time()
            while (time.time() - start_time) < 10:
                if msvcrt.kbhit():
                    key = msvcrt.getwche()
                    if key in ['\r', '\n']:
                        break
                    choice = key
                    print()
                    break
                time.sleep(0.05)
            else:
                print("\nВремя вышло. Выбрана модель по умолчанию.")
        except Exception:
            pass
        
        model_map = {
            "1": "tiny",
            "2": "base",
            "3": "small",
            "4": "medium",
            "5": "large"
        }
        
        selected_model = model_map.get(choice, MODEL_SIZE)
        print(f"Загрузка модели Whisper '{selected_model}'...")
        try:
            model = whisper.load_model(selected_model)
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            return

    # Инициализация PyAudio один раз
    p = pyaudio.PyAudio()

    disable_quick_edit()
    
    # Инициализация графического оверлея
    overlay = RecordingOverlay()

    try:
        print("---------------------------------------------------------")
        print(f"ГОТОВО К РАБОТЕ!")
        print(f"1. Поставьте курсор туда, куда хотите вставить текст.")
        print(f"2. Удерживайте клавишу '{HOTKEY}' и говорите.")
        print(f"3. Отпустите клавишу — текст напечатается автоматически.")
        print("---------------------------------------------------------")

        hotkey_event = threading.Event()
        recording_lock = threading.Lock()

        def on_hotkey():
            if recording_lock.locked():
                return
            hotkey_event.set()

        keyboard.add_hotkey(HOTKEY, on_hotkey)

        while True:
            try:
                # Ждем нажатия клавиши
                hotkey_event.wait()
                hotkey_event.clear()
                if not recording_lock.acquire(blocking=False):
                    continue
                
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                    temp_filename = temp_audio.name
                
                # Запись
                # overlay.set_color('red') # Теперь устанавливается внутри record_audio
                if record_audio(temp_filename, p, overlay):
                    
                    # Проверка на слишком короткое нажатие (случайное)
                    if os.path.getsize(temp_filename) < 2000: # ~ < 0.1 сек
                        overlay.hide()
                    else:
                        overlay.set_status("Распознавание...", "yellow")
                        log("Распознавание...")
                        
                        text = ""
                        try:
                            if use_groq:
                                with open(temp_filename, "rb") as file:
                                    transcription = groq_client.audio.transcriptions.create(
                                      file=(temp_filename, file.read()),
                                      model="whisper-large-v3",
                                      temperature=0,
                                      response_format="verbose_json",
                                    )
                                    text = transcription.text.strip()
                            else:
                                # initial_prompt помогает модели настроиться на русскую речь и пунктуацию
                                result = model.transcribe(temp_filename, language=LANGUAGE, fp16=False, initial_prompt="Привет, это проба пера. Пишем текст на русском языке.")
                                text = result["text"].strip()
                        except Exception as e:
                            log(f"Ошибка при распознавании: {e}")

                        if text:
                            log(f"Распознано: {text}")
                            
                            # Копируем в буфер и вставляем
                            original_clipboard = pyperclip.paste() # Сохраним что было
                            pyperclip.copy(text)
                            
                            # Небольшая пауза чтобы буфер успел обновиться
                            time.sleep(0.1) 
                            
                            # Эмуляция Ctrl+V
                            keyboard.send('ctrl+v')
                            
                        else:
                            log("Речь не распознана или пустой результат.")
                        
                        # Очистка памяти
                        if not use_groq:
                           try:
                               del result
                           except:
                               pass
                        del text
                        gc.collect()
                        overlay.hide()
                else:
                    overlay.hide()

                # Удаляем временный файл
                try:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                except:
                    pass

                # Анти-дребезг, чтобы не сработало повторно сразу же
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\nВыход из программы.")
                break
            except Exception as e:
                print(f"Произошла ошибка: {e}")
                time.sleep(1) # Пауза при ошибке, чтобы не спамить в консоль
            finally:
                if recording_lock.locked():
                    recording_lock.release()
    finally:
        try:
            keyboard.clear_all_hotkeys()
        except Exception:
            pass
        p.terminate()

if __name__ == "__main__":
    main()

