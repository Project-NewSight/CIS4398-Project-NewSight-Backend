# Unified API for NewSight Backend
# Combines Emergency Contact and Familiar Face Detection features
import threading
import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles  # Commented out - not currently used (photos go directly to S3)
# from app.routes import sms_routes
# from app.routes import contacts
# from app.routes import emergency_alert
# from app.routes import familiar_face
from app.routes import object_detection_backend

app = FastAPI(
    title="NewSight API",
    version="1.0",
    description="Backend API for Emergency Contact and Familiar Face Detection features"
)

# CORS middleware for WebSocket and API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for temporary photos (commented out - not currently used)
# Photos are uploaded directly to S3 and served via S3 URLs, so this mount is not needed
# app.mount("/temp_photos", StaticFiles(directory="temp_photos"), name="temp_photos")

# Include routers for both features
# Emergency Contact Feature Routes
# app.include_router(sms_routes.router)
# app.include_router(contacts.router)
# app.include_router(emergency_alert.router)
app.include_router(object_detection_backend.router)

# Familiar Face Detection Feature Routes
# Register WebSocket routes directly to maintain original paths (/ws, /ws/verify)
# app.websocket("/ws")(familiar_face.ws_verify)
# app.websocket("/ws/verify")(familiar_face.ws_verify)

# Root endpoint
@app.get("/")
def root():
    return {
        "message": "NewSight Backend API Running Successfully!",
        "features": [
            "Object Detection Backend"
        ]
    }

# Background initialization for heavy ML models
@app.on_event("startup")
async def startup_event():
    def init_heavy_models():
        try:
            # TensorFlow
            import tensorflow as tf
            print("TensorFlow imported successfully")

            # Ultralytics / YOLO
            import ultralytics
            print("Ultralytics imported successfully")

            # DeepFace
            #import deepface
            #print("DeepFace imported successfully")

            # Any additional model or weights loading
            print("Heavy ML models loaded in background")
        except Exception as e:
            print(f"Error loading models: {e}")

    # Start in a separate thread so Uvicorn binds to the port immediately
    threading.Thread(target=init_heavy_models).start()
