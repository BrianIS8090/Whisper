import whisper
import sys
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def save_markdown(file_path, text, prompt=""):
    """Сохраняет результат в Markdown файл рядом с исходным аудио."""
    output_file = os.path.splitext(file_path)[0] + ".md"
    file_title = os.path.basename(file_path)

    lines = [f"# Расшифровка: {file_title}", ""]
    if prompt:
        lines.extend(["## Промт", prompt, ""])
    lines.extend(["## Текст", text, ""])

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nTranscription saved to '{output_file}'")


def transcribe_audio(file_path, model_name="base", use_api=False, prompt=""):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    text = ""
    if use_api:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("Error: GROQ_API_KEY not found in environment variables or .env file.")
            return
        
        print(f"Transcribing '{file_path}' via Groq API (whisper-large-v3)...")
        try:
            client = Groq(api_key=api_key)
            with open(file_path, "rb") as file:
                request_data = {
                    "file": (file_path, file.read()),
                    "model": "whisper-large-v3",
                    "temperature": 0,
                    "language": "ru",
                    "response_format": "verbose_json",
                }
                if prompt:
                    request_data["prompt"] = prompt
                transcription = client.audio.transcriptions.create(
                    **request_data
                )
                text = transcription.text
        except Exception as e:
            print(f"Error during Groq API transcription: {e}")
            return
    else:
        print(f"Loading model '{model_name}'...")
        model = whisper.load_model(model_name)
        
        print(f"Transcribing '{file_path}' locally...")
        transcribe_args = {"fp16": False, "language": "ru"}
        if prompt:
            transcribe_args["initial_prompt"] = prompt
        result = model.transcribe(file_path, **transcribe_args)
        text = result["text"]
    
    if not text:
        print("Transcription failed or returned empty text.")
        return

    print("\nTranscription result:\n")
    print(text)
    
    save_markdown(file_path, text, prompt=prompt)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file_path> [model_name/api] [prompt]")
        print("Example (Local): python transcribe.py my_audio.mp3 small \"интервью про IT\"")
        print("Example (API):   python transcribe.py my_audio.mp3 api \"важны имена и термины\"")
    else:
        file_path = sys.argv[1]
        arg2 = sys.argv[2] if len(sys.argv) > 2 else "base"
        prompt = sys.argv[3] if len(sys.argv) > 3 else ""
        
        if arg2.lower() == "api":
            transcribe_audio(file_path, use_api=True, prompt=prompt)
        else:
            transcribe_audio(file_path, model_name=arg2, prompt=prompt)
