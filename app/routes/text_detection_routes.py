"""
Text Detection Routes
Provides WebSocket endpoint for real-time text detection using EasyOCR
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.text_detection_service import TextDetector
import base64
import cv2
import numpy as np
import json
import os
import time
import re
from collections import deque, Counter
from typing import Dict, List

router = APIRouter(prefix="/text-detection", tags=["Text Detection"])

# Minimum confidence threshold for returning recognized text
MIN_CONF = float(os.environ.get("MIN_CONF", "0.5"))

# Stability parameters
STABILITY_WINDOW = int(os.environ.get("STABILITY_WINDOW", "3"))
STABILITY_COUNT = int(os.environ.get("STABILITY_COUNT", "2"))

# Initialize text detector (shared across connections)
detector = None


def get_detector():
    """Lazy initialization of text detector"""
    global detector
    if detector is None:
        print("Initializing EasyOCR TextDetector...")
        detector = TextDetector(languages=['en'], gpu=False)
        print("✓ TextDetector ready!")
    return detector


def normalize_text(text: str) -> str:
    """Normalize text for stability comparison"""
    # lowercase, strip spaces, remove punctuation
    normalized = re.sub(r'\W+', '', text.lower())
    return normalized


@router.websocket("/ws")
async def text_detection_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time text detection
    
    Expected message format:
    {
        "feature": "text_detection",
        "frame": "base64_encoded_image"
    }
    
    Response format:
    {
        "ok": true,
        "stable_text": "detected text",
        "confidence": 0.95,
        "is_stable": true,
        "detections": [...]
    }
    """
    await websocket.accept()
    print("Text Detection WebSocket: Client connected")
    
    # Get detector instance
    text_detector = get_detector()
    
    # Per-connection buffer for stability tracking
    recent_buffer = deque(maxlen=STABILITY_WINDOW)
    consecutive_empty_frames = 0
    CLEAR_BUFFER_THRESHOLD = 2
    
    try:
        while True:
            try:
                # Receive message from client
                msg = await websocket.receive_text()
                data = json.loads(msg)
                
                feature = data.get("feature")
                frame_b64 = data.get("frame")
                
                if not frame_b64:
                    continue
                
                # Decode base64 frame
                frame_bytes = base64.b64decode(frame_b64)
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    print("Warning: Failed to decode frame")
                    continue
                
                # Run OCR detection
                detections = text_detector.detect_text_image(frame)
                
                # Aggregate detected words
                words = []
                max_conf = 0.0
                for d in detections:
                    txt = d.get("text", "").strip()
                    conf = d.get("confidence", 0.0)
                    if txt and conf >= MIN_CONF:
                        words.append(txt)
                        if conf > max_conf:
                            max_conf = conf
                
                # Join words into phrase
                frame_phrase = " ".join(words) if words else ""
                
                # Update stability buffer
                if frame_phrase:
                    recent_buffer.append(frame_phrase)
                    consecutive_empty_frames = 0
                else:
                    consecutive_empty_frames += 1
                    if consecutive_empty_frames >= CLEAR_BUFFER_THRESHOLD:
                        recent_buffer.clear()
                        consecutive_empty_frames = 0
                
                # Determine stability
                is_stable = False
                stable_text = ""
                stable_confidence = 0.0
                
                if len(recent_buffer) >= STABILITY_COUNT:
                    # Normalize and count occurrences
                    normalized_texts = [normalize_text(t) for t in recent_buffer]
                    counter = Counter(normalized_texts)
                    most_common_norm, count = counter.most_common(1)[0]
                    
                    if count >= STABILITY_COUNT:
                        is_stable = True
                        # Find original (non-normalized) text
                        for original in recent_buffer:
                            if normalize_text(original) == most_common_norm:
                                stable_text = original
                                stable_confidence = max_conf
                                break
                
                # Send response matching frontend expectations
                # Frontend looks for "text_string" (primary) and "detections" (fallback)
                response = {
                    "text_string": stable_text,  # Frontend looks for this field
                    "detections": detections if detections else [],  # Frontend looks for this array
                    # Additional fields for compatibility
                    "full_text": frame_phrase,
                    "stable_text": stable_text,
                    "is_stable": is_stable,
                    "confidence": stable_confidence,
                    "feature": "text_detection"
                }
                
                await websocket.send_json(response)
                
            except json.JSONDecodeError:
                print("Error: Invalid JSON received")
                continue
            except Exception as e:
                print(f"Error processing frame: {e}")
                continue
                
    except WebSocketDisconnect:
        print("Text Detection WebSocket: Client disconnected")
    except Exception as e:
        print(f"Text Detection WebSocket error: {e}")
    finally:
        print("Text Detection WebSocket: Connection closed")


@router.get("/")
def text_detection_info():
    """Get information about text detection feature"""
    return {
        "feature": "Text Detection (OCR)",
        "description": "Real-time text detection using EasyOCR",
        "websocket_endpoint": "/text-detection/ws",
        "configuration": {
            "min_confidence": MIN_CONF,
            "stability_window": STABILITY_WINDOW,
            "stability_count": STABILITY_COUNT
        },
        "supported_languages": ["en"],
        "model": "EasyOCR (CRAFT + CRNN)"
    }

