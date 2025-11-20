from fastapi import APIRouter, UploadFile, File, Header
from app.services.voice_service import SpeechToText
from app.services.voice_agent import VoiceCommandAgent
from app.services.navigation_service import NavigationService
from app.routes.location_routes import get_user_location
from typing import Optional
import tempfile
import os

# route for the api
router = APIRouter(prefix="/voice", tags=["voice Commands"])

transcriber = SpeechToText()
agent = VoiceCommandAgent()
nav_service = NavigationService()

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
async def process_voice_command(
    audio: UploadFile = File(...),
    x_session_id: Optional[str] = Header(None)
):
    """
    Receive audio, transcribe it, process with agent, and return JSON response
    
    For NAVIGATION feature:
    - Pulls destination from voice_agent
    - Gets location from location_routes
    - Starts navigation and returns full route
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

        # ===== NAVIGATION INTEGRATION =====
        # If voice agent identified NAVIGATION, pull destination and start navigation
        if agent_response.get("feature") == "NAVIGATION" and x_session_id:
            destination = filtered_response.get("destination")
            
            if destination:
                print(f"🗺️  NAVIGATION feature detected - destination: '{destination}'")
                
                # Get user location from location WebSocket storage
                location = get_user_location(x_session_id)
                
                if location:
                    try:
                        print(f"📍 Got location: ({location['latitude']}, {location['longitude']})")
                        
                        # Start navigation using the destination from voice_agent
                        directions = nav_service.start_navigation(
                            session_id=x_session_id,
                            origin_lat=location["latitude"],
                            origin_lng=location["longitude"],
                            destination=destination
                        )
                        
                        print(f"✅ Navigation started to: {directions['destination']}")
                        
                        # Add directions to the response
                        filtered_response["directions"] = directions
                        
                        return {
                            "confidence": agent_response.get("confidence", 0.0),
                            "extracted_params": filtered_response,
                            "TTS_Output": {
                                "message": f"Starting navigation to {directions['destination']}"
                            }
                        }
                    
                    except Exception as nav_error:
                        print(f"❌ Navigation error: {str(nav_error)}")
                        filtered_response["navigation_error"] = str(nav_error)
                        
                        return {
                            "confidence": agent_response.get("confidence", 0.0),
                            "extracted_params": filtered_response,
                            "TTS_Output": {
                                "message": f"Found {destination}, but couldn't get directions. Please try again."
                            }
                        }
                else:
                    print(f"⚠️  No location found for session {x_session_id}")
                    filtered_response["navigation_error"] = "Location not available"
                    
                    return {
                        "confidence": agent_response.get("confidence", 0.0),
                        "extracted_params": filtered_response,
                        "TTS_Output": {
                            "message": "I need your location to start navigation. Please enable GPS."
                        }
                    }

        # Build JSON response for non-navigation features or if session_id not provided
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