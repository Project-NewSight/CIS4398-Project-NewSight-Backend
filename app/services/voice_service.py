import os
import requests
import json

class SpeechToText:
    """ Send audio file to Groq Wisher API and get transcription"""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")

        self.api_url = "https://api.groq.com/openai/v1/audio/transcriptions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def speech_to_text(self, audio_file: str, language: str = "en", prompt: str = None):
        """
        Transcribes audio into text using Groq Whisper.
        :param audio_file: Path to WAV or MP3 file
        :param language: Language code (default 'en')
        :param prompt: Optional context to improve transcription
        """

        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file '{audio_file}' not found")

        files = {
            "file": (os.path.basename(audio_file), open(audio_file, "rb")),
        }

        data = {
            "model": "whisper-large-v3-turbo",
            "response_format": "verbose_json",
            "language": language,
            "temperature": 0.0
        }

        if prompt:
            data["prompt"] = prompt

        response = requests.post(self.api_url, headers=self.headers, data=data, files=files)

        if response.status_code != 200:
            raise Exception(f"Transcription failed ({response.status_code}): {response.text}")

        transcription = response.json()
        text_output = transcription.get("text", "")

        print("✅ Transcription completed successfully.")
        return {"text": text_output, "raw": transcription}