import whisper
import sys
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def transcribe_audio(file_path, model_name="base", use_api=False):
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
                transcription = client.audio.transcriptions.create(
                    file=(file_path, file.read()),
                    model="whisper-large-v3",
                    temperature=0,
                    language="ru",
                    response_format="verbose_json",
                )
                text = transcription.text
        except Exception as e:
            print(f"Error during Groq API transcription: {e}")
            return
    else:
        print(f"Loading model '{model_name}'...")
        model = whisper.load_model(model_name)
        
        print(f"Transcribing '{file_path}' locally...")
        result = model.transcribe(file_path, fp16=False, language="ru")
        text = result["text"]
    
    if not text:
        print("Transcription failed or returned empty text.")
        return

    print("\nTranscription result:\n")
    print(text)
    
    # Save to a text file
    output_file = os.path.splitext(file_path)[0] + ".txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\nTranscription saved to '{output_file}'")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file_path> [model_name/api]")
        print("Example (Local): python transcribe.py my_audio.mp3 small")
        print("Example (API):   python transcribe.py my_audio.mp3 api")
    else:
        file_path = sys.argv[1]
        arg2 = sys.argv[2] if len(sys.argv) > 2 else "base"
        
        if arg2.lower() == "api":
            transcribe_audio(file_path, use_api=True)
        else:
            transcribe_audio(file_path, model_name=arg2)
