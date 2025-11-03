# Unified API for NewSight Backend
# Combines Emergency Contact and Familiar Face Detection features
import os
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routes import sms_routes
from app.routes import contacts
from app.routes import emergency_alert
from app.routes import familiar_face

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

# Mount static files for temporary photos
app.mount("/temp_photos", StaticFiles(directory="temp_photos"), name="temp_photos")

# Include routers for both features
# Emergency Contact Feature Routes
app.include_router(sms_routes.router)
app.include_router(contacts.router)
app.include_router(emergency_alert.router)

# Familiar Face Detection Feature Routes
# Register WebSocket routes directly to maintain original paths (/ws, /ws/verify)
app.websocket("/ws")(familiar_face.ws_verify)
app.websocket("/ws/verify")(familiar_face.ws_verify)

@app.get("/")
def root():
    return {
        "message": "NewSight Backend API Running Successfully!",
        "features": [
            "Emergency Contact Management",
            "Familiar Face Detection"
        ]
    }