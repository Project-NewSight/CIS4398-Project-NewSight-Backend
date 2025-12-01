# Unified API for NewSight Backend
# Combines Emergency Contact, Familiar Face Detection, Voice Command, and Navigation features
import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles  # Commented out - not currently used (photos go directly to S3)
from app.routes import sms_routes
from app.routes import contacts
from app.routes import emergency_alert
from app.routes import familiar_face
from app.routes import voice_routes
from app.routes import location_routes
from app.routes import navigation_routes

# from app.routes import object_detection_backend

app = FastAPI(
    title="NewSight API",
    version="1.0",
    description="Backend API for Emergency Contact, Familiar Face Detection, Voice Command, and Navigation features"
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

# Include routers for features
# Emergency Contact Feature Routes
app.include_router(sms_routes.router)
app.include_router(contacts.router)
app.include_router(emergency_alert.router)
#app.include_router(object_detection_backend.router)

# Voice Command Feature Route
app.include_router(voice_routes.router)

# Navigation Feature Routes
app.include_router(location_routes.router)
app.include_router(navigation_routes.router)

# Familiar Face Detection Feature Routes
# Register WebSocket routes directly to maintain original paths (/ws, /ws/verify)
app.websocket("/ws")(familiar_face.ws_verify)
app.websocket("/ws/verify")(familiar_face.ws_verify)

# Navigation Feature Routes
app.include_router(location_routes.router)
app.include_router(navigation_routes.router)


@app.get("/")
def root():
    return {
        "message": "NewSight Backend API Running Successfully!",
        "features": [
            "Emergency Contact Management",
            "Familiar Face Detection",
            "Voice Command",
            "Navigation",
            "Object Detection Backend"
        ]
    }
