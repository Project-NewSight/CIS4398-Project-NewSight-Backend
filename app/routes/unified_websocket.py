"""
Unified WebSocket Handler
Routes WebSocket messages to appropriate feature handlers based on message format
Supports: Familiar Face Detection and Text Detection
"""

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import json
import base64
import cv2
import numpy as np
from app.routes import familiar_face
from app.services.text_detection_service import TextDetector
import os
import time
import re
from collections import deque, Counter
from typing import Optional

# Text detection configuration
MIN_CONF = float(os.environ.get("MIN_CONF", "0.5"))
STABILITY_WINDOW = int(os.environ.get("STABILITY_WINDOW", "3"))
STABILITY_COUNT = int(os.environ.get("STABILITY_COUNT", "2"))
CLEAR_BUFFER_THRESHOLD = 2

# Lazy-load text detector
_text_detector: Optional[TextDetector] = None


def get_text_detector():
    """Lazy initialization of text detector"""
    global _text_detector
    if _text_detector is None:
        print("[Unified WS] Initializing EasyOCR TextDetector...")
        _text_detector = TextDetector(languages=['en'], gpu=False)
        print("[Unified WS] ✓ TextDetector ready!")
    return _text_detector


def normalize_text(text: str) -> str:
    """Normalize text for stability comparison"""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text)).strip().lower()


async def unified_websocket_handler(websocket: WebSocket):
    """
    Unified WebSocket handler that routes to feature handlers based on message format
    
    Message formats:
    1. Familiar Face Detection:
       - {"type": "hello", "feature": "familiar_face"}
       - {"type": "frame", "image_b64": "..."}
       - Or raw binary JPEG bytes
    
    2. Text Detection:
       - {"feature": "text_detection", "frame": "base64_image"}
    """
    await websocket.accept()
    print(f"[Unified WS] Client connected to {websocket.url.path}")
    
    # State tracking
    current_feature = None
    text_detection_state = {
        "recent_buffer": deque(maxlen=STABILITY_WINDOW),
        "consecutive_empty_frames": 0,
        "last_sent_text": ""  # Track last sent text to avoid repeating
    }
    
    # For familiar face detection, we'll delegate to the existing handler
    # But first we need to detect which feature is being used
    
    try:
        while True:
            message = await websocket.receive()
            
            # Handle text messages (JSON)
            if "text" in message and message["text"] is not None:
                txt = message["text"]
                
                # Handle ping/pong
                if txt == "ping":
                    await websocket.send_text("pong")
                    continue
                
                try:
                    data = json.loads(txt)
                    msg_type = data.get("type")
                    feature = data.get("feature")
                    
                    # Detect feature type
                    if msg_type == "hello":
                        current_feature = feature
                        print(f"[Unified WS] Feature detected: {current_feature}")
                        await websocket.send_text(
                            json.dumps({"ok": True, "note": "hello_ack", "feature": current_feature})
                        )
                        continue
                    
                    # Route to appropriate handler
                    if feature == "text_detection" or (current_feature == "text_detection"):
                        # Handle text detection
                        try:
                            await handle_text_detection(websocket, data, text_detection_state)
                        except WebSocketDisconnect:
                            # Connection closed, exit loop
                            raise
                        continue
                    
                    elif msg_type == "frame" and "image_b64" in data:
                        # Handle familiar face detection (JSON format)
                        current_feature = "familiar_face"
                        jpeg_bytes = base64.b64decode(data.get("image_b64") or "")
                        await websocket.send_text(json.dumps({"ok": True, "note": "received", "len": len(jpeg_bytes)}))
                        
                        # Delegate to familiar face handler
                        await familiar_face.process_face_recognition(
                            jpeg_bytes, websocket, time.time(), 1.2
                        )
                        continue
                
                except json.JSONDecodeError:
                    print("[Unified WS] Invalid JSON, ignoring")
                    continue
                except RuntimeError as e:
                    if "close message has been sent" in str(e) or "disconnect message" in str(e):
                        print(f"[Unified WS] Connection closed during processing")
                        break
                    print(f"[Unified WS] Runtime error: {e}")
                    continue
                except Exception as e:
                    print(f"[Unified WS] Error processing text message: {e}")
                    continue
            
            # Handle binary messages (raw JPEG for familiar face)
            if "bytes" in message and message["bytes"] is not None:
                current_feature = "familiar_face"
                jpeg_bytes = message["bytes"]
                
                # Delegate to familiar face handler
                await familiar_face.process_face_recognition(
                    jpeg_bytes, websocket, time.time(), 1.2
                )
                continue
    
    except WebSocketDisconnect:
        print(f"[Unified WS] Client disconnected (feature: {current_feature})")
    except Exception as e:
        print(f"[Unified WS] Error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "ok": False, "error": f"server_exception: {e}"
            }))
        except Exception:
            pass


async def handle_text_detection(websocket: WebSocket, data: dict, state: dict):
    """
    Handle text detection WebSocket messages
    
    Expected format:
    {
        "feature": "text_detection",
        "frame": "base64_encoded_image"
    }
    """
    # Check if websocket is still connected
    if websocket.client_state != WebSocketState.CONNECTED:
        print(f"[Unified WS] WebSocket not connected (state: {websocket.client_state}), skipping frame")
        raise WebSocketDisconnect(code=1000, reason="Connection not in CONNECTED state")
    
    frame_b64 = data.get("frame")
    if not frame_b64:
        return
    
    # Get text detector
    detector = get_text_detector()
    
    # Decode frame
    frame_bytes = base64.b64decode(frame_b64)
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        print("[Unified WS] Warning: Failed to decode frame")
        return
    
    # Run OCR detection
    detections = detector.detect_text_image(frame)
    
    # Aggregate detected words
    words = []
    max_conf = 0.0
    for d in detections:
        txt = d.get("text", "").strip()
        conf = float(d.get("confidence", 0.0))
        bbox = d.get("bbox")
        
        if txt and conf >= MIN_CONF:
            # Calculate position for sorting
            min_x = 0
            min_y = 0
            # Convert bbox to native Python types for JSON serialization
            bbox_serializable = None
            if bbox:
                try:
                    # Convert numpy arrays to Python lists with native int/float
                    bbox_serializable = [[int(pt[0]), int(pt[1])] for pt in bbox]
                    xs = [pt[0] for pt in bbox_serializable]
                    ys = [pt[1] for pt in bbox_serializable]
                    if xs and ys:
                        min_x = int(min(xs))
                        min_y = int(min(ys))
                except Exception as e:
                    print(f"[Unified WS] Warning: Failed to serialize bbox: {e}")
                    bbox_serializable = None
            
            words.append({
                "text": txt,
                "confidence": float(conf),
                "bbox": bbox_serializable,
                "x": min_x,
                "y": min_y
            })
            
            if conf > max_conf:
                max_conf = conf
    
    # Sort into reading order: top-to-bottom, then left-to-right
    words_sorted = sorted(words, key=lambda w: (int(w["y"] / 20), w["x"]))
    
    # Build full text from current frame (original, not normalized)
    full_text = " ".join(w["text"] for w in words_sorted) if words_sorted else ""
    avg_conf = float((sum(w["confidence"] for w in words_sorted) / len(words_sorted))) if words_sorted else 0.0
    
    # Normalize for stability check (but keep original text separately)
    norm = normalize_text(full_text)
    
    # Update buffer - store both normalized (for comparison) and original (for output)
    recent_buffer = state["recent_buffer"]
    consecutive_empty_frames = state["consecutive_empty_frames"]
    
    if norm:
        recent_buffer.append((norm, full_text, avg_conf))  # Store: (normalized, original, confidence)
        consecutive_empty_frames = 0
    else:
        consecutive_empty_frames += 1
        if consecutive_empty_frames >= CLEAR_BUFFER_THRESHOLD:
            if len(recent_buffer) > 0:
                recent_buffer.clear()
            consecutive_empty_frames = 0
    
    state["consecutive_empty_frames"] = consecutive_empty_frames
    
    # Determine stable text (use normalized for comparison, but return original)
    normalized_texts = [t[0] for t in recent_buffer if t[0]]  # Get normalized versions
    stable_text = None
    stable_text_original = None
    
    if normalized_texts:
        counts = Counter(normalized_texts)
        most_common_normalized, count = counts.most_common(1)[0]
        
        # Get all confidences and original texts for this normalized text
        matching_entries = [entry for entry in recent_buffer if entry[0] == most_common_normalized]
        confs = [entry[2] for entry in matching_entries]
        avg_conf_buf = sum(confs) / len(confs) if confs else 0.0
        
        if count >= STABILITY_COUNT and avg_conf_buf >= MIN_CONF:
            stable_text = most_common_normalized
            # Use the most recent original version of this text
            stable_text_original = matching_entries[-1][1] if matching_entries else most_common_normalized
    
    # Determine what text to send (prefer stable original text, fallback to current full text)
    text_to_send = stable_text_original if stable_text_original else full_text
    
    # Get last sent text from state
    last_sent_text = state.get("last_sent_text", "")
    
    # Only send if text has changed OR if we're clearing (empty text after having text)
    # This prevents TTS from repeating the same text
    should_send = False
    if text_to_send and text_to_send != last_sent_text:
        # New different text detected
        should_send = True
    elif not text_to_send and last_sent_text:
        # Clear the display when no text detected after having text
        should_send = True
    
    if not should_send:
        # Skip sending - same text as before
        return
    
    # Update last sent text
    state["last_sent_text"] = text_to_send
    
    # Prepare detections array matching frontend format
    # Ensure all values are JSON-serializable (convert numpy types to Python types)
    per_frame_results = [
        {
            "text": str(w["text"]), 
            "confidence": float(w["confidence"]), 
            "bbox": w["bbox"]  # Already converted above
        }
        for w in words_sorted
    ]
    
    # Send response matching frontend expectations
    response = {
        "text_string": str(text_to_send) if text_to_send else "",  # Frontend looks for this field
        "detections": per_frame_results,  # Frontend looks for this array
        "full_text": str(full_text) if full_text else "",
        "stable_text": str(stable_text_original) if stable_text_original else None,
        "feature": "text_detection",
        "confidence": float(avg_conf) if stable_text_original else 0.0
    }
    
    try:
        # Double-check connection before sending
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_text(json.dumps(response))
            print(f"[Unified WS] Text Detection: stable='{stable_text_original}' | full='{full_text}' | sending='{text_to_send}'")
        else:
            print(f"[Unified WS] WebSocket disconnected (state: {websocket.client_state}), cannot send")
            # Raise exception to break out of the main loop
            raise WebSocketDisconnect(code=1000, reason="Connection closed")
    except WebSocketDisconnect:
        # Re-raise to be caught by main handler
        raise
    except RuntimeError as e:
        if "close message has been sent" in str(e) or "disconnect message" in str(e):
            print(f"[Unified WS] Connection closed, stopping text detection")
            raise WebSocketDisconnect(code=1000, reason="Connection closed")
        else:
            print(f"[Unified WS] Error sending response: {e}")
    except Exception as e:
        print(f"[Unified WS] Unexpected error sending response: {e}")

