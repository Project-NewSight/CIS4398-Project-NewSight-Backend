# Unified API for NewSight Backend
# Combines Emergency Contact, Familiar Face Detection, Voice Command, and Color Cue features

import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not key_path or not os.path.exists(key_path):
    raise FileNotFoundError(f"Google Vision key not found at {key_path}")
app = FastAPI()
# from fastapi.staticfiles import StaticFiles  # Not used currently

from app.routes import sms_routes
from app.routes import contacts
from app.routes import emergency_alert
from app.routes import familiar_face
from app.routes import voice_routes
from app.routes import object_detection_backend
from app.routes import colorcue
from app.routes import voice_routes
app.include_router(voice_routes.router)

# FastAPI app initialization
app = FastAPI(
    title="NewSight API",
    version="1.1",
    description="Backend API for Emergency Contact, Familiar Face Detection, Voice Commands, Object Detection, and Color Cue (Clothing Recognition)"
)

# CORS middleware for mobile/web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(sms_routes.router)
app.include_router(contacts.router)
app.include_router(emergency_alert.router)
#app.include_router(object_detection_backend.router)
app.include_router(voice_routes.router)
app.include_router(colorcue.router)

# Familiar Face WebSocket handling
try:
    print("Familiar face detection enabled.")
except Exception as e:
    print("⚠ Familiar face detection disabled:", e)

@app.get("/")
def root():
    return {
        "message": "NewSight Backend API Running Successfully!",
        "features": [
            "Emergency Contact Management",
            "Familiar Face Detection",
            "Voice Command",
            "Object Detection Backend",
            "Color Cue"
        ]
    }
