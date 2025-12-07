"""
Test cases for Voice Command System
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


def test_wake_word_detection(client):
    """
    Test: Detect "Hey Guide" in audio
    Confirm: Returns wake_word_detected=True
    Input: Audio file with "Hey Guide"
    Result: wake_word_detected=True
    """
    with patch('app.services.voice_service.SpeechToText.speech_to_text') as mock_stt:
        mock_stt.return_value = {"text": "hey guide"}
        
        fake_audio = BytesIO(b"fake audio data")
        response = client.post(
            "/voice/wake-word",
            files={"audio": ("test.wav", fake_audio, "audio/wav")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["wake_word_detected"] is True
        assert "hey guide" in data["text"].lower()


def test_no_wake_word(client):
    """
    Test: Process audio without wake word
    Confirm: Returns wake_word_detected=False
    Input: Audio "Hello there"
    Result: wake_word_detected=False
    """
    with patch('app.services.voice_service.SpeechToText.speech_to_text') as mock_stt:
        mock_stt.return_value = {"text": "hello there"}
        
        fake_audio = BytesIO(b"fake audio data")
        response = client.post(
            "/voice/wake-word",
            files={"audio": ("test.wav", fake_audio, "audio/wav")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["wake_word_detected"] is False


def test_transcribe_audio(client):
    """
    Test: Convert speech to text using Groq Whisper
    Confirm: Returns accurate transcription
    Input: Audio "Take me to CVS"
    Result: text="Take me to CVS"
    """
    with patch('app.services.voice_service.SpeechToText.speech_to_text') as mock_stt, \
         patch('app.services.voice_agent.VoiceCommandAgent.route_command') as mock_agent:
        
        mock_stt.return_value = {"text": "Take me to CVS"}
        mock_agent.return_value = {
            "feature": "NAVIGATION",
            "confidence": 0.95,
            "extracted_params": {"destination": "CVS", "query": "Take me to CVS"}
        }
        
        fake_audio = BytesIO(b"fake audio data")
        response = client.post(
            "/voice/transcribe",
            files={"audio": ("test.wav", fake_audio, "audio/wav")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["confidence"] > 0.9


def test_route_navigation_command(client):
    """
    Test: Voice command triggers navigation
    Confirm: LLM identifies NAVIGATION, extracts destination
    Input: Audio "Navigate to Temple"
    Result: feature="NAVIGATION", destination="Temple"
    """
    with patch('app.services.voice_service.SpeechToText.speech_to_text') as mock_stt, \
         patch('app.services.voice_agent.VoiceCommandAgent.route_command') as mock_agent:
        
        mock_stt.return_value = {"text": "Navigate to Temple University"}
        mock_agent.return_value = {
            "feature": "NAVIGATION",
            "confidence": 0.95,
            "extracted_params": {
                "destination": "Temple University",
                "query": "Navigate to Temple University"
            }
        }
        
        fake_audio = BytesIO(b"fake audio data")
        response = client.post(
            "/voice/transcribe",
            files={"audio": ("test.wav", fake_audio, "audio/wav")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["extracted_params"]["feature"] == "NAVIGATION"
        assert "Temple" in data["extracted_params"]["destination"]


def test_route_emergency_command(client):
    """
    Test: Voice triggers emergency alert
    Confirm: LLM identifies EMERGENCY_CONTACT
    Input: Audio "Send emergency alert"
    Result: feature="EMERGENCY_CONTACT"
    """
    with patch('app.services.voice_service.SpeechToText.speech_to_text') as mock_stt, \
         patch('app.services.voice_agent.VoiceCommandAgent.route_command') as mock_agent:
        
        mock_stt.return_value = {"text": "Send emergency alert"}
        mock_agent.return_value = {
            "feature": "EMERGENCY_CONTACT",
            "confidence": 0.98,
            "extracted_params": {"query": "Send emergency alert"}
        }
        
        fake_audio = BytesIO(b"fake audio data")
        response = client.post(
            "/voice/transcribe",
            files={"audio": ("test.wav", fake_audio, "audio/wav")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["extracted_params"]["feature"] == "EMERGENCY_CONTACT"


def test_unrecognized_command(client):
    """
    Test: Handle unclear speech
    Confirm: Returns feature="NONE"
    Input: Mumbled audio
    Result: feature="NONE", error message
    """
    with patch('app.services.voice_service.SpeechToText.speech_to_text') as mock_stt, \
         patch('app.services.voice_agent.VoiceCommandAgent.route_command') as mock_agent:
        
        mock_stt.return_value = {"text": ""}
        mock_agent.return_value = {
            "feature": None,
            "confidence": 0.0,
            "extracted_params": {}
        }
        
        fake_audio = BytesIO(b"fake audio data")
        response = client.post(
            "/voice/transcribe",
            files={"audio": ("test.wav", fake_audio, "audio/wav")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["confidence"] == 0.0
        assert "couldn't process" in data["TTS_Output"]["message"].lower()
