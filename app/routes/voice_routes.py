from fastapi import APIRouter, UploadFile, File
from app.services.voice_service import SpeechToText
from app.services.voice_agent import VoiceCommandAgent
import tempfile
import os

# route for the api
router = APIRouter(prefix="/voice", tags=["voice Commands"])

transcriber = SpeechToText()
agent = VoiceCommandAgent()

# listens for wake word
@router.post("/wake-word")
async def check_wake_word(audio: UploadFile = File(...)):
    """ 
    Check if wake word ('Hey Guide') is present in audio
    """
    try:
        # Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(await audio.read())
            tmp_path = tmp.name
        
        # Transcribe audio
        result = transcriber.speech_to_text(tmp_path, prompt="Listen for the wake word 'Hey Guide'")
        os.remove(tmp_path)

        text = result.get("text", "").strip().lower()
        wake_word_detected = ("hey" in text and "guide" in text) or "hey guide" in text

        print(f"🎯 Wake word check: '{text}' -> {wake_word_detected}")

        return {"text": text, "wake_word_detected": wake_word_detected}
    
    except Exception as e:
        print(f"❌ Error in wake-word: {str(e)}")
        return {"error": str(e), "wake_word_detected": False}

@router.post("/transcribe")
async def process_voice_command(audio: UploadFile = File(...)):
    """
    Receive audio, transcribe it, process with agent, and return JSON response
    """
    try:
        # Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(await audio.read())
            tmp_path = tmp.name

        # Transcribe audio with Groq Whisper
        result = transcriber.speech_to_text(
            tmp_path,
            prompt="Transcribe clearly, with correct spelling for US road names, highways, cities names, and landmarks."
        )
        os.remove(tmp_path)

        text = result.get("text", "").strip()
        
        if not text:
            print("⚠️ Empty transcription - no speech detected")
            return {
                "confidence": 0.0,
                "extracted_params": {
                    "feature": None,
                    "query": ""
                },
                "TTS_Output": {
                    "message": "I am sorry, I couldn't process your request. Please try again later."
                }
            }
        
        print(f"🎤 User said: {text}")

        # Get agent response
        agent_response = agent.route_command(text)

        # Filter and structure the response
        def filter_agent_response(agent_response):
            feature = agent_response.get("feature")
            extracted = agent_response.get("extracted_params", {})
            filtered = {"feature": feature}

            if feature == "NAVIGATION":
                filtered["destination"] = extracted.get("destination")
                filtered["query"] = extracted.get("query")
                if "sub_features" in extracted:
                    filtered["sub_features"] = extracted["sub_features"]
            
            elif feature == "EMERGENCY_CONTACT":
                filtered["query"] = extracted.get("query")
                if "sub_features" in extracted:
                    filtered["sub_features"] = extracted["sub_features"]
            
            else:
                filtered["query"] = extracted.get("query")
            
            return filtered
        
        filtered_response = filter_agent_response(agent_response)
        print(f"🤖 Agent response: {filtered_response}")

        # Build JSON response
        if agent_response.get("feature"):
            response_data = {
                "confidence": agent_response.get("confidence", 0.0),
                "extracted_params": filtered_response,
                "TTS_Output": {
                    "message": "Processing your request"
                }
            }
        else:
            response_data = {
                "confidence": 0.0,
                "extracted_params": {
                    "feature": None,
                    "query": text
                },
                "TTS_Output": {
                    "message": "I am sorry, I couldn't process your request. Please try again later."
                }
            }

        print(f"📤 Sending JSON response: {response_data}")
        return response_data
        
    except Exception as e:
        print(f"❌ Error in /voice/transcribe: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "confidence": 0.0,
            "extracted_params": {
                "feature": None,
                "query": "",
                "error": str(e)
            },
            "TTS_Output": {
                "message": "I am sorry, I couldn't process your request. Please try again later."
            }
        }