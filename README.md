# Project NewSight – Unified Backend API

This backend service powers **Project NewSight**, combining features:
1. **Emergency Contact and Alert System** - Allows users to register trusted contacts and automatically send location, photo, and alert messages during emergencies
2. **Familiar Face Detection** - Real-time face recognition to identify familiar contacts using DeepFace and WebSocket connections
3. **Voice Command** - Allows users to speak through the Android phone's microphone to send voice commands to activate features. The feature can also be activated using a wake word "Hey Guide"
4. **Voice-Activated Navigation** - Provides real-time, step-by-step walking directions with voice announcements and AR-style visual overlay, fully hands-free for visually impaired users

## Overview

The backend is built with **FastAPI** and integrates with:
- **AWS S3** – for securely storing emergency photos and familiar face images
- **PostgreSQL (via SQLAlchemy)** – for managing user contact data
- **Vonage SMS API** – for sending alerts to trusted contacts
- **DeepFace** – for face recognition and matching
- **WebSocket** – for real-time face recognition processing and navigation updates
- **Groq STT** - for converting speech to text
- **Groq llama** - for deciding which feature to execute based on user command
- **Google Maps API** – for walking directions, place search, and real-time navigation

The system ensures that in an emergency, user data is safely transmitted, messages are delivered quickly, and photos are uploaded to a secure cloud location. Additionally, it provides real-time face recognition capabilities to identify familiar contacts. Users can also interact with the system via voice commands, allowing hands-free operation to trigger features including fully voice-activated turn-by-turn navigation. 

---

## Features

### Emergency Contact Feature
- Add, view, or delete trusted emergency contacts
- Automatically send an alert (GPS + photo + message) to all trusted contacts for a user
- Store uploaded emergency photos in **AWS S3**
- SMS notifications via Vonage API

### Familiar Face Detection Feature
- Real-time face recognition via WebSocket connections
- Match faces against a gallery stored in AWS S3
- Configurable face recognition models (VGG-Face, Facenet, ArcFace, etc.)
- Automatic synchronization of familiar faces from S3 to local cache
- Confidence scoring and distance thresholds for matches

### Voice Commands
- Activate system features hands-free using voice
- Supports wake word "Hey Guide" for instant activation
- Converts speech to text using **Groq STT**
- Determines appropriate action with **Groq LLaMa**
- Acts as supervisor for navigation requests

### Voice-Activated Navigation
- **Hands-Free Operation**: Simply say "Hey Guide, nearest CVS" or "Give me directions to Starbucks" from any screen
- **Smart Place Recognition**: Recognizes generic places (CVS, Starbucks, bus stops, etc.) and finds the nearest location
- **Real-Time GPS Tracking**: Continuous location monitoring via WebSocket for accurate positioning
- **Turn-by-Turn Voice Guidance**: Announces upcoming turns with distance (e.g., "In 50 feet, turn right on Main Street")
- **AR-Style Visual Overlay**: Shows distance, directional arrows, and current instruction on camera feed
- **Automatic Navigation Start**: No need to repeat the destination - navigation starts immediately when NavigateActivity opens
- **Google Maps Integration**: 
  - Uses Google Directions API for walking routes
  - Places API for finding nearby locations
  - Geocoding API for address resolution
- **Proximity Detection**: Automatically advances to the next step as you walk
- **Voice Announcements at Key Points**: 100m, 50 feet, 25 feet before turns

### Shared Infrastructure
- Clean, modular structure for easy integration with the Project NewSight mobile frontend
- CORS middleware enabled for cross-origin requests
- Unified API documentation via FastAPI's automatic docs

---

## Project Structure

```
CIS4398-Project-NewSight-Backend/
│
├── app/
│   ├── __init__.py
│   ├── db.py                    # Database connection and session
│   ├── models.py                # SQLAlchemy models (EmergencyContact)
│   ├── schemas.py               # Pydantic schemas (includes navigation models)
│   ├── main.py                  # FastAPI entry point (unified app)
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── contacts.py          # CRUD endpoints for emergency contacts
│   │   ├── emergency_alert.py   # Endpoint for sending emergency alerts
│   │   ├── sms_routes.py        # SMS endpoint
│   │   ├── familiar_face.py     # Face recognition WebSocket handlers
│   │   ├── voice_routes.py      # Voice command endpoints (supervisor for navigation)
│   │   ├── location_routes.py   # Location tracking WebSocket endpoint
│   │   └── navigation_routes.py # Navigation endpoints and WebSocket for turn-by-turn updates
│   │
│   └── services/
│       ├── sms_service.py       # Handles Vonage SMS integration
│       ├── contact_lookup.py    # Contact lookup service
│       ├── voice_agent.py       # Decides which feature to use based on user's command
│       ├── voice_service.py     # Translates user's speech to text
│       └── navigation_service.py # Google Maps integration and navigation logic
│
├── .env                         # Environment variables (not committed)
├── .env.example                 # Example environment variables
├── .gitignore
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## Setup Instructions

### 1. Create and Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql+psycopg2://username:password@host:port/dbname

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-2
AWS_S3_BUCKET_NAME=newsight-storage
AWS_S3_FOLDER_NAME=emergency-uploads

# AWS S3 Configuration for Familiar Face Detection
S3_PREFIX=familiar_img/

# Vonage (SMS) Configuration
VONAGE_API_KEY=your-vonage-key
VONAGE_API_SECRET=your-vonage-secret
VONAGE_FROM_NUMBER=your-vonage-phone

# Groq AI Configuration
GROQ_API_KEY=your-groq-key

# Google Maps API Configuration (for Navigation Feature)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
```

**Important for Navigation Feature:**
- Enable **Directions API**, **Places API**, and **Geocoding API** in Google Cloud Console
- Set up billing for your Google Cloud project (required for Maps APIs)
- The API key needs permissions for all three APIs

---

## Running the Server

### Command

```bash
uvicorn app.main:app --reload
```

### Server Details

- **Server runs at**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs
- **Alternative docs**: http://127.0.0.1:8000/redoc

---

## API Endpoints

### Root Endpoint
- **GET** `/` - Returns API status and available features

### Emergency Contact Endpoints

- **POST** `/contacts/` - Add a new emergency contact
  - Requires: `user_id`, `name`, `phone` (Form data)
  - Optional: `relationship`, `address`, `image_url`

- **GET** `/contacts/{user_id}` - Get all contacts for a user

- **DELETE** `/contacts/{contact_id}` - Delete a contact by ID

- **POST** `/emergency_alert/{user_id}` - Send emergency alert
  - Requires: `latitude`, `longitude` (Form data)
  - Optional: `photo` (UploadFile)
  - Sends SMS to all registered contacts for the user

- **POST** `/sms/send` - Send SMS message
  - Query params: `to_number`, `message`

### Familiar Face Detection Endpoints

- **WebSocket** `/ws` - Face recognition WebSocket connection
- **WebSocket** `/ws/verify` - Alternative face verification WebSocket connection

**WebSocket Protocol:**
- Send binary JPEG frames for real-time face recognition
- Or send JSON messages:
  - `{"type": "ping"}` - Keep-alive ping
  - `{"type": "hello", "feature": "familiar_face"}` - Initialize connection
  - `{"type": "frame", "image_b64": "..."}` - Base64 encoded image frame

**Response Format:**
```json
{
  "ok": true,
  "match": true/false,
  "contactName": "Name or Unknown",
  "confidence": 0.0-1.0,
  "distance": 0.0-1.0,
  "note": "match_status"
}
```

### Voice Command Endpoints

**POST** `/voice/wake-word` - Looks for the wake word "Hey, Guide"
- Accepts: Audio file (WAV format)
- Returns: `{"wake_word_detected": true/false}`

**POST** `/voice/transcribe` - Transcribes audio and determines which feature to activate
- Accepts: Audio file (WAV format)
- Headers: `X-Session-Id` (required for navigation feature)
- Returns: Feature identification with extracted parameters

**Response Format:**
```json
{
  "confidence": 0.0-1.0,
  "extracted_params": {
    "feature": "NAVIGATION",
    "destination": "CVS Pharmacy",
    "query": "nearest CVS",
    "directions": {
      "status": "OK",
      "destination": "CVS Pharmacy",
      "origin": {"lat": 40.123, "lng": -75.456},
      "total_distance": "0.5 mi",
      "total_duration": "10 mins",
      "steps": [
        {
          "instruction": "Head north on Main St",
          "distance": "500 ft",
          "duration": "2 mins",
          "distance_meters": 152,
          "start_location": {"lat": 40.123, "lng": -75.456},
          "end_location": {"lat": 40.124, "lng": -75.456}
        }
      ]
    }
  },
  "TTS_Output": {
    "message": "Starting navigation to CVS Pharmacy"
  }
}
```

**Note:** For NAVIGATION feature, if `X-Session-Id` header is provided and user location is available, the response includes full `directions` object with turn-by-turn steps from Google Maps API.

### Location Tracking Endpoints

**WebSocket** `/location/ws` - Continuous GPS location tracking
- Accepts JSON messages:
  ```json
  {
    "session_id": "uuid-string",
    "latitude": 40.123456,
    "longitude": -75.123456,
    "timestamp": 1234567890
  }
  ```
- Used by navigation feature to track user's real-time position
- Location is stored server-side and accessible to other routes via session ID

### Navigation Endpoints

**POST** `/navigation/start` - Start a navigation session
- Request body:
  ```json
  {
    "session_id": "uuid-string",
    "destination": "CVS Pharmacy"
  }
  ```
- Returns: Full directions response with steps
- Requires user location to be available via location WebSocket

**WebSocket** `/navigation/ws?session_id=uuid` - Real-time turn-by-turn navigation updates
- Query param: `session_id` (required)
- Receives location updates from client
- Sends navigation updates:
  ```json
  {
    "status": "navigating",
    "current_step": 1,
    "total_steps": 5,
    "instruction": "Head north on Main St",
    "distance_to_next": 152.4,
    "should_announce": true,
    "announcement": "In 50 feet, turn right on Main Street"
  }
  ```
- Status values: `"navigating"`, `"step_completed"`, `"arrived"`
- Automatically advances steps based on GPS proximity
- Announces turns at 100m, 50 feet, and 25 feet

---

## Navigation Feature Architecture

### Complete Flow

1. **User initiates navigation** (from any activity - Home, Communicate, Observe):
   - User says: "Hey Guide, nearest CVS"
   - Audio is captured and sent to `/voice/transcribe` endpoint with `X-Session-Id` header

2. **Backend processing** (`voice_routes.py` acts as supervisor):
   - Transcribes audio using Groq Whisper
   - Voice agent identifies `NAVIGATION` feature and extracts destination ("CVS")
   - Retrieves user's current location from `location_routes.py` storage (populated by location WebSocket)
   - Calls `navigation_service.py` to:
     - Clean destination (removes "nearest", "the", etc.)
     - Detect if generic place name (CVS, Starbucks, bus stops, etc.)
     - If generic: Use Places API to find nearest matching location
     - If specific: Use Geocoding API to resolve address
     - Call Directions API with origin and destination for walking route
     - Parse and structure turn-by-turn steps
   - Returns complete directions in response

3. **Frontend receives response**:
   - HomeActivity/CommunicateActivity/ObserveActivity receives JSON with `directions` object
   - Launches NavigateActivity with directions passed via Intent extras
   - NavigateActivity automatically starts navigation without user needing to speak again

4. **Real-time navigation** (NavigateActivity):
   - Opens camera for AR overlay
   - Connects to `/navigation/ws` WebSocket with session ID
   - Sends GPS updates every 2 seconds via location WebSocket
   - Backend calculates:
     - Distance to next turn using Haversine formula
     - Whether to advance to next step (within 20 meters of turn)
     - Whether to announce (at 100m, 50 feet, 25 feet thresholds)
   - Frontend displays:
     - Current instruction (e.g., "Turn right on Main St")
     - Distance to next turn (formatted as feet/miles)
     - Directional arrow (straight, left, right, slight left/right)
     - Voice announcements via text-to-speech

5. **Navigation completion**:
   - When user reaches destination (within 20m), backend sends `"arrived"` status
   - Frontend announces "You have arrived at your destination"
   - Navigation session cleaned up

### Key Design Decisions

- **`voice_routes.py` as supervisor**: All voice commands route through here first, including navigation
- **Complete directions in initial response**: User doesn't need to speak again in NavigateActivity
- **Dual WebSocket architecture**:
  - `/location/ws`: Continuous background GPS tracking
  - `/navigation/ws`: Real-time turn-by-turn updates during active navigation
- **Generic place recognition**: System understands "nearest CVS" and automatically finds closest location
- **Distance from API, not calculations**: Display and announcements use Google Maps API distances, only internal proximity detection uses Haversine

---

## Testing the Navigation Feature

### Android App Testing

1. **Backend Setup**:
   - Start backend server on your local network:
     ```bash
     python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
     ```
   - Note your local IP address (e.g., 192.168.1.254)

2. **Android Setup** (if on physical device):
   - Update WebSocket URLs in Android code to use your local IP
   - Or use ADB port forwarding (see instructions below)

3. **Test Flow**:
   - Open app → HomeActivity/CommunicateActivity/ObserveActivity
   - Say: "Hey Guide, nearest CVS" (or any destination)
   - NavigateActivity should open with navigation already started
   - Walk around to see real-time updates

### Common Test Destinations

- **Generic places**: "nearest CVS", "Starbucks", "bus stop", "ATM", "pharmacy"
- **Specific places**: "Temple University", "City Hall Philadelphia"
- **Addresses**: "1801 N Broad St, Philadelphia"

---

## Additional Instructions

### For Apple Silicon Mac Users Testing with Physical Android Device

These instructions are relevant if:
- You are using an Apple Silicon Mac
- You are testing with a physical Android phone connected via USB to the Mac in Android Studio

#### 1. Check if ADB is installed

```bash
ls ~/Library/Android/sdk/platform-tools
```

If adb exists, temporarily add it to your PATH:

```bash
export PATH=$PATH:$HOME/Library/Android/sdk/platform-tools
```

Then confirm installation:

```bash
adb version
```

#### 2. Connect your Android device via USB

Plug the device into your Mac and run:

```bash
adb devices
```

Expected output:

```
List of devices attached
2S98115AA11A2500505	device
emulator-5554	device
```

#### 3. Set up port forwarding

Run the following command to link your Mac's backend to your phone:

```bash
adb -s <device_serial> reverse tcp:8000 tcp:8000
```

For specific device (example):

```bash
adb -s 2S98115AA11A2500505 reverse tcp:8000 tcp:8000
```

Verify with:

```bash
adb -s 2S98115AA11A2500505 reverse --list
```

#### 4. (Optional) Remove port forwarding when finished

```bash
adb -s <device_serial> reverse --remove tcp:8000
```

---

## Architecture Notes

### Feature Independence

Features are designed to run independently:
- **Emergency Contact** routes are prefixed and organized under `/contacts`, `/emergency_alert`, `/sms`
- **Familiar Face Detection** uses WebSocket endpoints at `/ws` and `/ws/verify`
- **Voice Commands** routes are prefixed and organized under `/voice/wake-word`, `/voice/transcribe`
- **Navigation** routes are organized under `/navigation/start` with WebSocket at `/navigation/ws`
- **Location Tracking** uses WebSocket endpoint at `/location/ws` (shared by navigation)
- No route conflicts or overlapping functionality
- Shared infrastructure (CORS, WebSocket, database) is unified

### Feature Integration

While features are independent, some features work together:
- **Voice Commands** acts as supervisor for **Navigation** feature
  - Identifies navigation requests
  - Orchestrates the navigation initialization
  - Returns complete directions in a single API call
- **Location Tracking** provides GPS data for **Navigation** feature
  - Continuous background tracking via WebSocket
  - Location stored server-side by session ID
  - Accessible to navigation routes for real-time updates

### Modular Design

- Routes are organized in separate modules for easy maintenance
- Services are separated from route handlers for better code organization
- Easy to add new features following the existing router pattern

---

## Technologies Used

- **FastAPI** - Modern, fast web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Relational database
- **AWS S3** - Cloud storage for emergency photos and face recognition images
- **Vonage API** - SMS messaging for emergency alerts
- **DeepFace** - Face recognition library
- **OpenCV** - Image processing
- **NumPy** - Numerical operations
- **WebSocket** - Real-time bidirectional communication (face recognition, location tracking, navigation)
- **Boto3** - AWS SDK for Python
- **Pydantic** - Data validation and serialization
- **gTTS** - Text-to-speech
- **Groq API** - Speech-to-text (Whisper) and LLM (llama-3.1-8b-instant) for voice command processing
- **Google Maps APIs**:
  - **Directions API** - Walking route calculation
  - **Places API** - Finding nearby locations (CVS, Starbucks, etc.)
  - **Geocoding API** - Address resolution and location search
- **googlemaps** - Python client for Google Maps APIs
- **Haversine Formula** - GPS distance calculation for step advancement

---

## Troubleshooting Navigation

### "Google Maps API error: NOT_FOUND"
- **Cause**: API key not configured or APIs not enabled
- **Fix**: 
  1. Check `.env` file has `GOOGLE_MAPS_API_KEY=your-key`
  2. Verify Directions API, Places API, and Geocoding API are enabled in Google Cloud Console
  3. Restart backend server after updating `.env`

### "Location not available" or no directions returned
- **Cause**: Location WebSocket not connected before voice command
- **Fix**:
  1. Wait 2-3 seconds after opening app for location to initialize
  2. Check Android logs for "Location WebSocket connected"
  3. Verify location permissions are granted on device

### Navigation doesn't start from voice command in other activities
- **Cause**: Session ID not being sent or location not tracked
- **Fix**:
  1. Ensure `LocationWebSocketHelper` is initialized in HomeActivity/CommunicateActivity/ObserveActivity
  2. Check that `X-Session-Id` header is included in voice request
  3. Verify backend logs show "Location updated for [session-id]"

### App crashes when navigation starts
- **Cause**: Null values in navigation update (fixed in latest code)
- **Fix**:
  1. Ensure you have latest NavigateActivity.java with null checks
  2. Check that backend is sending valid `distance_to_next` values
  3. Review Android crash logs for specific NullPointerException

### Generic places not found (e.g., "nearest CVS")
- **Cause**: Place not in generic terms list or too far away
- **Fix**:
  1. Search radius is 10km - ensure location is within that range
  2. Try being more specific: "CVS Pharmacy" instead of just "CVS"
  3. Check `navigation_service.py` logs for "identified as generic place"

### Voice announcements not working
- **Cause**: Text-to-speech not initialized or audio permissions
- **Fix**:
  1. Verify `RECORD_AUDIO` permission granted
  2. Check that TtsHelper is initialized in NavigateActivity
  3. Test with device volume turned up

---

## Development

The unified backend maintains clean separation between features while sharing common infrastructure. Features can be developed and tested independently, and the modular structure makes it easy to extend with additional features in the future.
