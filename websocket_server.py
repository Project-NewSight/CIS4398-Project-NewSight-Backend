"""
WebSocket Server for Text Detection
Receives camera frames from Android app and returns detected text
"""

import asyncio
import base64
import json
import logging
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import the text detection module
from text_detection import TextDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Text Detection WebSocket Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize text detector (will download models on first run)
logger.info("Initializing text detector...")
text_detector = None

@app.on_event("startup")
async def startup_event():
    """Initialize the text detector when the server starts"""
    global text_detector
    try:
        text_detector = TextDetector(languages=['en'], gpu=False)
        logger.info("✓ Text detector initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize text detector: {e}")
        raise

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Text Detection WebSocket Server",
        "endpoints": {
            "websocket": "/ws",
            "health": "/"
        }
    }

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "text_detector": "ready" if text_detector else "not initialized"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for receiving frames and sending text detection results
    """
    await websocket.accept()
    client_id = id(websocket)
    logger.info(f"Client {client_id} connected")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse JSON message
                message = json.loads(data)
                feature = message.get("feature", "")
                frame_base64 = message.get("frame", "")
                
                logger.info(f"Received frame for feature: {feature}")
                
                # Check if this is a text detection request
                if feature == "text_detection" and frame_base64:
                    # Decode base64 frame
                    frame_bytes = base64.b64decode(frame_base64)
                    
                    # Convert bytes to numpy array
                    nparr = np.frombuffer(frame_bytes, np.uint8)
                    
                    # Decode image
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if image is None:
                        logger.error("Failed to decode image")
                        await websocket.send_text(json.dumps({
                            "error": "Failed to decode image",
                            "detections": [],
                            "text_string": ""
                        }))
                        continue
                    
                    logger.info(f"Image decoded: {image.shape}")
                    
                    # Perform text detection
                    try:
                        detections = text_detector.detect_text_image(image)
                        
                        # Create combined text string
                        text_string = ' '.join([d['text'] for d in detections if d.get('confidence', 0) >= 0.5])
                        
                        # Prepare response
                        response = {
                            "detections": detections,
                            "text_string": text_string,
                            "num_detections": len(detections)
                        }
                        
                        logger.info(f"Detected text: '{text_string}' ({len(detections)} elements)")
                        
                        # Send response back to client
                        await websocket.send_text(json.dumps(response))
                        
                    except Exception as e:
                        logger.error(f"Text detection error: {e}")
                        await websocket.send_text(json.dumps({
                            "error": str(e),
                            "detections": [],
                            "text_string": ""
                        }))
                else:
                    # Unknown feature or missing frame
                    logger.warning(f"Unknown feature or missing frame: {feature}")
                    await websocket.send_text(json.dumps({
                        "error": "Unknown feature or missing frame",
                        "detections": [],
                        "text_string": ""
                    }))
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                await websocket.send_text(json.dumps({
                    "error": "Invalid JSON",
                    "detections": [],
                    "text_string": ""
                }))
            except Exception as e:
                logger.error(f"Processing error: {e}")
                await websocket.send_text(json.dumps({
                    "error": str(e),
                    "detections": [],
                    "text_string": ""
                }))
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        logger.info(f"Connection closed for client {client_id}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  Text Detection WebSocket Server")
    print("="*70)
    print("\n📡 Starting server...")
    print("   WebSocket endpoint: ws://localhost:8000/ws")
    print("   Health check: http://localhost:8000/health")
    print("\n💡 Tips:")
    print("   - First run will download EasyOCR models (~500MB)")
    print("   - Use Ctrl+C to stop the server")
    print("   - Check logs for connection status and errors")
    print("\n" + "="*70 + "\n")
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,
        log_level="info"
    )

