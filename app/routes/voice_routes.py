from fastapi import APIRouter, UploadFile, File, Depends, Form
#from app.services.voice_service import SpeechToText
#from fastapi import APIRouter, UploadFile, File
#from app.services.voice_service import SpeechToText
#from app.services.voice_agent import VoiceCommandAgent
from app.services.voice_add_item_flow import AddItemFlowHandler
from app.services.voice_memory import AddItemState
from app.services.ocr_service import extract_text_from_image
from app.services.voice_memory import AddItemState
from app.services.appropriateness_engine import OccasionAppropriatenessEngine
import tempfile
import os
from app.db import get_db
from sqlalchemy.orm import Session



# route for the api
router = APIRouter(prefix="/voice", tags=["voice Commands"])

#transcriber = SpeechToText()
#agent = VoiceCommandAgent()

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

        flow_response = AddItemFlowHandler.handle(text)
        if flow_response:
            # Convert flow response into your API format style
            response_data = {
                "confidence": 1.0,
                "extracted_params": {
                    "feature": "ADD_ITEM_FLOW",
                    "step": flow_response["step"],
                    "query": text
                },
                "TTS_Output": {
                    "message": flow_response["TTS"]
                }
            }

            print(f"📤 Sending ADD_ITEM_FLOW step response: {response_data}")
            return response_data
        
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
            elif feature == "IDENTIFY_ITEM":
                filtered["query"] = extracted.get("query")
            else:
                filtered["query"] = extracted.get("query")
            
            return filtered
        
        filtered_response = filter_agent_response(agent_response)
        print(f"🤖 Agent response: {filtered_response}")

        # Build JSON response
        if agent_response.get("feature"):
            if agent_response["feature"] == "IDENTIFY_ITEM":
                response_data = {
                    "confidence": agent_response.get("confidence", 0.0),
                    "extracted_params": filtered_response,
                    "TTS_Output": {
                        "message": "Okay. Hold the item in front of the camera and say 'capture' when you are ready."
                    }
                }
                print(f"📤 Sending JSON response: {response_data}")
                return response_data
            
            if agent_response["feature"] == "SAVE_ITEM":
                response_data = {
                    "confidence": agent_response.get("confidence", 0.0),
                    "extracted_params": filtered_response,
                    "TTS_Output": {
                        "message": "Alright. I will save this item. Say 'capture' when you want me to take the photo."
                    }
                }
                print(f"📤 Sending JSON response: {response_data}")
                return response_data
            if agent_response["feature"] == "ADD_ITEM_FLOW":
                response_data = {
                    "confidence": agent_response.get("confidence", 0.0),
                    "extracted_params": filtered_response,
                    "TTS_Output": {
                        "message": (
                            "Okay. Lay the clothing item flat on a table or bed in a well-lit area. "
                            "Make sure the whole item is visible. When you're ready, say 'capture' "
                            "to take the first photo."
                        )
                    }
                }
                print(f"📤 Sending JSON response: {response_data}")
                return response_data

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
   
@router.post("/capture")
async def capture_item(
    user_id: int,
    file: UploadFile = File(...),
    db = Depends(get_db)
):
    """
    IDENTIFY ITEM + ADD ITEM FLOW

    - Detect color/category/pattern
    - Create embedding
    - Find closest match
    - Return identity + similarity
    - Save features into AddItemState for the Add Item flow
    """
    import os
    from app.services.embedding_service import generate_embedding, find_closest_item
    from app.services.colorcue_service import detect_all
    from app.routes.colorcue_routes import save_temp_file
    from app.services.voice_memory import AddItemState

    # Save file temporarily
    temp_path = save_temp_file(file)

    try:
        # 1. Extract ColorCue features
        features = detect_all(temp_path)

        # 2. Create embedding
        query_vec = generate_embedding(temp_path)

        # 3. Find closest match in user's closet
        closest_item, score = find_closest_item(user_id, query_vec, features, db)

        # --- Store features for Add Item flow ---
        AddItemState.item_features = features
        AddItemState.closet_id = user_id
        AddItemState.user_id = user_id

        # Build TTS message
        if closest_item:
            message = (
                f"I see a {features['color']} {features['pattern']} {features['category']}. "
                f"It looks most similar to your item '{closest_item.color} {closest_item.category}', "
                f"with a similarity score of {score:.2f}."
            )
        else:
            message = (
                f"I see a {features['color']} {features['pattern']} {features['category']}, "
                "but I could not find anything similar in your closet."
            )

        return {
            "success": True,
            "detected_item": features,
            "closest_item": {
                "id": closest_item.item_id,
                "color": closest_item.color,
                "category": closest_item.category,
                "pattern": closest_item.pattern
            } if closest_item else None,
            "similarity": score,
            "TTS_Output": {"message": message}
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/save_item")
async def save_item(
    user_id: int,
    file: UploadFile = File(...),
    db = Depends(get_db)
):
    from app.routes.colorcue_routes import add_item

    return await add_item(
        closet_id=user_id,
        genre=AddItemState.genre,
        notes=AddItemState.notes,
        style=None,
        file=file,
        db=db,
        material=AddItemState.material,
        washing=AddItemState.washing_instructions,
        features=AddItemState.item_features
    )


@router.post("/capture_tag")
async def capture_tag(
    file: UploadFile = File(...),
):
    from app.routes.colorcue_routes import save_temp_file
    from app.services.ocr_service import extract_text_from_image
    from app.services.voice_memory import AddItemState
    
    temp_path = save_temp_file(file)
    
    ocr_data = extract_text_from_image(temp_path)
    AddItemState.material = ocr_data.get("material")
    AddItemState.washing_instructions = ocr_data.get("washing_instructions")
    AddItemState.state = "awaiting_genre"
    AddItemState.state = "tag_captured"
    AddItemState.material = ocr_data.get("material")
    AddItemState.washing_instructions = ocr_data.get("washing_instructions")


    return {
        "step": "tag_captured",
        "material": AddItemState.material,
        "washing": AddItemState.washing_instructions,
        "TTS_Output": {
            "message": "Got it. Would you like to add a genre? For example: pajamas, work clothes, exercise clothes."
        }
    }


@router.post("/analyze_item")
async def analyze_item(
    file: UploadFile = File(...),
):
    """
    Voice: item analysis – color, pattern, category, multicolor
    """
    import tempfile, os
    from app.services.colorcue_service import detect_all
    from app.services.google_vision_service import (
        detect_colors, is_multicolor, pattern_likelihood, rgb_to_simple_color
    )

    # Save temporary image
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    try:
        # Roboflow basic detection
        det = detect_all(temp_path)

        # Google Vision deep color analysis
        gv_colors = detect_colors(temp_path)
        multi = is_multicolor(gv_colors)
        pattern_prob = 1.0 if pattern_likelihood(gv_colors) else 0.0

        # Primary color
        sorted_colors = sorted(gv_colors, key=lambda c: c["pixel_fraction"], reverse=True)
        primary_simple = rgb_to_simple_color(
            sorted_colors[0]["r"], sorted_colors[0]["g"], sorted_colors[0]["b"]
        )

        spoken = (
            f"I see a {primary_simple} {det['pattern']} {det['category']}."
            f"{' It contains multiple colors.' if multi else ''}"
        )

        return {
            "success": True,
            "analysis": {
                "category": det["category"],
                "pattern": det["pattern"],
                "primary_color": primary_simple,
                "is_multicolor": multi,
                "pattern_score": pattern_prob
            },
            "TTS_Output": {"message": spoken}
        }

    finally:
        os.remove(temp_path)

@router.post("/does_this_match")
async def does_this_match(
    user_id: int,
    file: UploadFile = File(...),
    db = Depends(get_db)
):
    """
    Voice: Determine if item matches anything in the closet.
    """
    import tempfile, os
    from app.services.embedding_service import (
        generate_embedding, find_closest_item
    )
    from app.services.colorcue_service import detect_all

    # Save temp
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    try:
        features = detect_all(temp_path)
        query_vec = generate_embedding(temp_path)

        closest_item, score = find_closest_item(user_id, query_vec, features, db)

        if closest_item:
            spoken = (
                f"Yes, this matches well with your "
                f"{closest_item.primary_color or closest_item.color} "
                f"{closest_item.pattern} {closest_item.category}."
            )
        else:
            spoken = "I couldn't find anything in your closet that strongly matches this item."

        return {
            "success": True,
            "match_score": score,
            "closest_item": {
                "id": closest_item.item_id,
                "color": closest_item.color,
                "primary_color": closest_item.primary_color,
                "category": closest_item.category,
                "pattern": closest_item.pattern,
                "image_url": closest_item.image_url
            } if closest_item else None,
            "TTS_Output": {"message": spoken}
        }

    finally:
        os.remove(temp_path)

EVENT_GENRE_MAP = {
    "interview": "formal",
    "job interview": "formal",
    "wedding": "formal",
    "gym": "sport",
    "workout": "sport",
    "school": "casual",
    "class": "casual",
    "date": "smart casual",
    "dinner": "smart casual",
    "party": "party",
    "cold": "warm",
}
from app.services.appropriateness_engine import OccasionAppropriatenessEngine

@router.post("/is_appropriate")
async def is_appropriate(
    event: str = Form(...),
    weather: str = Form(...),
    mostly_outside: bool = Form(False),
    culture: str = Form("western"),
    file: UploadFile = File(...),
):
    """
    Voice: “Is this appropriate for [event]?”
    - event: e.g. "wedding", "funeral", "interview", "court", "gym", "church"
    - weather: a word ("cold", "hot") or a temperature ("35", "80")
    - mostly_outside: True/False
    - culture: "western", "hindu", "muslim", "jewish", "chinese", "yoruba", "santeria", "catholic", etc.
    """
    import tempfile, os
    from app.services.colorcue_service import detect_all
    from app.services.google_vision_service import detect_colors, rgb_to_simple_color

    # Save image temporarily
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    try:
        # ---------------------------------------
        # 1. Roboflow detection (category, pattern, color, printed_text, etc.)
        # ---------------------------------------
        det = detect_all(temp_path)

        # Extract printed text (if any)
        printed_text = det.get("printed_text", "")

        # ---------------------------------------
        # 2. Google Vision primary color
        # ---------------------------------------
        gv_colors = detect_colors(temp_path)
        primary_color = "unknown"

        if gv_colors:
            # Sort by pixel fraction
            sorted_colors = sorted(gv_colors, key=lambda c: c["pixel_fraction"], reverse=True)
            top = sorted_colors[0]
            primary_color = rgb_to_simple_color(top["r"], top["g"], top["b"])

        # ---------------------------------------
        # 3. Build Item Dict for Appropriateness Engine
        # ---------------------------------------
        item = {
            "category": det.get("category"),
            "category_unified": det.get("category_unified"),    
            "category_raw_yolo": det.get("category_raw_yolo"),    
            "pattern": det.get("pattern"),
            "color": det.get("color"),                            
            "primary_color": primary_color,                      
            "printed_text": printed_text,
        }

        # ---------------------------------------
        # 4. Run Appropriateness Engine
        # ---------------------------------------
        ok, reasons, spoken = OccasionAppropriatenessEngine.analyze(
            event=event,
            item=item,
            culture=culture,
            weather=weather,
            mostly_outside=mostly_outside,
        )

        # ---------------------------------------
        # 5. Return response
        # ---------------------------------------
        return {
            "success": True,
            "appropriate": ok,
            "event": event,
            "culture": culture,
            "weather": weather,
            "mostly_outside": mostly_outside,
            "item": item,
            "reasons": reasons,
            "TTS_Output": {"message": spoken},
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/closet_query")
async def closet_query(
    user_id: int,
    color: str = None,
    category: str = None,
    db = Depends(get_db)
):
    """
    Voice: color or category-based closet search
    """
    from app.models import ClothingItem

    q = db.query(ClothingItem).filter(ClothingItem.closet_id == user_id)

    if color:
        q = q.filter(ClothingItem.primary_color == color)

    if category:
        q = q.filter(ClothingItem.category == category)

    items = q.all()

    if not items:
        spoken = "I couldn't find anything matching that in your closet."
    else:
        spoken = f"You have {len(items)} item(s) that match your request."

    return {
        "success": True,
        "count": len(items),
        "items": [
            {
                "id": i.item_id,
                "primary_color": i.primary_color,
                "category": i.category,
                "pattern": i.pattern,
                "image_url": i.image_url
            }
            for i in items
        ],
        "TTS_Output": {"message": spoken}
    }


@router.post("/text")
async def process_text_command(
    command: str,
    db: Session = Depends(get_db)
):
    """
    TEXT COMMAND ROUTER
    ----------------------------------------
    Full development endpoint.
    Lets you type commands like:
       - "add item"
       - "capture"
       - "what is this"
       - "save item"
       - "does this match"
       - "is this appropriate for a wedding"
       - "suggest outfit for interview"
    This bypasses STT and routes text directly
    into the real ColorCue + Voice workflows.
    """
    try:
        text = command.strip().lower()
        print(f"🎤 User typed: {text}")

        # ------------------------------------------------------
        # 1. Check Add Item Flow first (genre → notes → save)
        # ------------------------------------------------------
        flow_response = AddItemFlowHandler.handle(text)
        if flow_response:
            return {
                "confidence": 1.0,
                "extracted_params": {
                    "feature": "ADD_ITEM_FLOW",
                    "step": flow_response["step"],
                    "query": text
                },
                "TTS_Output": {
                    "message": flow_response["TTS"]
                }
            }

        # ------------------------------------------------------
        # 2. Intent Parsing
        # ------------------------------------------------------
        intent = None

        if "add item" in text:
            intent = "START_ADD"

        elif text in ["capture", "identify", "what is this", "what’s this"]:
            intent = "IDENTIFY_ITEM"

        elif "appropriate" in text or "is this good for" in text:
            intent = "CHECK_APPROPRIATE"

        elif "suggest outfit" in text or "what should i wear" in text:
            intent = "SUGGEST_OUTFIT"

        elif "save item" in text:
            intent = "SAVE_ITEM"

        elif "does this match" in text or "match this" in text:
            intent = "MATCH_ITEM"


        # If no intent matched → debug mode
        if not intent:
            return {
                "confidence": 1.0,
                "extracted_params": {
                    "feature": "TEXT_DEBUG",
                    "query": text
                },
                "TTS_Output": {
                    "message": "I processed your text command."
                }
            }

        # ------------------------------------------------------
        # 3. Route Intent → Real Function Calls
        # ------------------------------------------------------
        # (We wrap calls so nothing breaks if file missing, etc.)

        # ---------- A) START ADD ITEM ----------
        if intent == "START_ADD":
            msg = AddItemFlowHandler.start_flow()
            return {
                "confidence": 1.0,
                "extracted_params": {"feature": "ADD_ITEM_FLOW"},
                "TTS_Output": {"message": msg}
            }

        # ---------- B) IDENTIFY ----------
        if intent == "IDENTIFY_ITEM":
            return {
                "confidence": 1.0,
                "extracted_params": {"feature": "IDENTIFY_ITEM"},
                "TTS_Output": {
                    "message": (
                        "Okay. Hold the item in front of the camera on your headset "
                        "and say 'capture' when you're ready."
                    )
                }
            }

        # ---------- D) APPROPRIATE ----------
        if intent == "CHECK_APPROPRIATE":

            # Extract event keyword
            event_words = [
                "interview", "wedding", "funeral", "church",
                "school", "gym", "party", "date", "dinner",
            ]

            event = next((w for w in event_words if w in text), None)
            if not event:
                event = "event"

            return {
                "confidence": 1.0,
                "extracted_params": {
                    "feature": "CHECK_APPROPRIATE",
                    "event": event
                },
                "TTS_Output": {
                    "message": f"Okay. Hold your item up and say 'capture' so I can check if it's appropriate for {event}."
                }
            }
        # ---------- F) SAVE ITEM ----------
        if intent == "SAVE_ITEM":
            return {
                "confidence": 1.0,
                "extracted_params": {"feature": "SAVE_ITEM"},
                "TTS_Output": {
                    "message": "Okay. Say 'capture' when you're ready to save this item."
                }
            }
        
        # TOP + BOTTOM MATCH
        if intent == "COMPARE_ITEMS":
            return {
                "confidence": 1.0,
                "extracted_params": {"feature": "COMPARE_ITEMS"},
                "TTS_Output": {
                    "message": "Okay. Hold your top item up and say 'capture top', then hold the bottom item up and say 'capture bottom'."
                }
            }


        # ------------------------------------------------------
        # 4. Fallback
        # ------------------------------------------------------
        return {
            "confidence": 1.0,
            "extracted_params": {"feature": "UNKNOWN"},
            "TTS_Output": {"message": "Command understood, but no action was mapped."}
        }

    except Exception as e:
        print(f"❌ Error in /voice/text: {str(e)}")
        return {
            "confidence": 0.0,
            "error": str(e),
            "TTS_Output": {"message": "An error occurred while processing your text command."}
        }


@router.post("/compare_items")
async def compare_items(
    top: UploadFile = File(...),
    bottom: UploadFile = File(...)
):
    """
    Match two clothing items (top + bottom) based on color theory.
    """
    import tempfile, os
    from app.services.colorcue_service import detect_all

    # save temp files
    with tempfile.NamedTemporaryFile(delete=False) as t:
        t.write(await top.read())
        top_path = t.name

    with tempfile.NamedTemporaryFile(delete=False) as b:
        b.write(await bottom.read())
        bottom_path = b.name

    try:
        # Detect both items
        top_det = detect_all(top_path)
        bottom_det = detect_all(bottom_path)

        top_color = top_det.get("color")
        bottom_color = bottom_det.get("color")

        # --- COLOR MATCHING LOGIC ---
        match, explanation = color_match_logic(top_color, bottom_color)

        spoken = (
            f"The top is {top_color}, and the bottom is {bottom_color}. "
            + explanation
        )

        return {
            "success": True,
            "match": match,
            "top_item": top_det,
            "bottom_item": bottom_det,
            "TTS_Output": {"message": spoken}
        }

    finally:
        for p in [top_path, bottom_path]:
            if os.path.exists(p):
                os.remove(p)
