# Project NewSight – Unified Backend API

This backend service powers **Project NewSight**, combining features:
1. **Emergency Contact and Alert System** - Allows users to register trusted contacts and automatically send location, photo, and alert messages during emergencies
2. **Familiar Face Detection** - Real-time face recognition to identify familiar contacts using DeepFace and WebSocket connections
3. **Voice Command** - Allows users to speak through the Android phone's microphone to send voice commands to activate features. The feature can also be activated using a wake word "Hey Guide"
4. **Voice-Activated Navigation** - Provides real-time, step-by-step walking directions with voice announcements and AR-style visual overlay, fully hands-free for visually impaired users
5. **Text Detection (OCR)** - Real-time text detection and recognition using EasyOCR for reading street signs, labels, and environmental text
6. **Object / Obstacle Detection** – Runs a YOLOv8 model on camera frames to detect nearby obstacles (people, cars, bikes, etc.), groups them into left / front / right regions, and returns a short, TTS-friendly summary like “Person in front about 2 meters away”.

## Overview

The backend is built with **FastAPI** and integrates with:
- **AWS S3** – for securely storing emergency photos and familiar face images
- **PostgreSQL (via SQLAlchemy)** – for managing user contact data
- **Vonage SMS API** – for sending alerts to trusted contacts
- **DeepFace** – for face recognition and matching
- **WebSocket** – for real-time face recognition processing, navigation updates, and text detection
- **Groq STT** - for converting speech to text
- **Groq llama** - for deciding which feature to execute based on user command
- **Google Maps API** – for walking directions, place search, and real-time navigation
- **EasyOCR** - for text detection and optical character recognition
- **Ultralytics YOLOv8** – for real-time object and obstacle detection on camera frames

The system ensures that in an emergency, user data is safely transmitted, messages are delivered quickly, and photos are uploaded to a secure cloud location. Additionally, it provides real-time face recognition capabilities to identify familiar contacts. Users can also interact with the system via voice commands, allowing hands-free operation to trigger features including fully voice-activated turn-by-turn navigation and text detection for reading environmental text.

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

### Text Detection (OCR) Feature
- **Real-Time OCR**: Detect and read text from camera feed in real-time using EasyOCR
- **WebSocket Support**: Live text detection via WebSocket for continuous camera frame processing
- **High Accuracy**: Uses CRAFT (Character Region Awareness For Text detection) and CRNN (Convolutional Recurrent Neural Network)
- **Multilingual Support**: Supports 80+ languages (currently configured for English)
- **Stability Detection**: Filters flickering results by requiring consistent text across multiple frames
- **Confidence Thresholds**: Configurable minimum confidence for text detection
- **Optimized Performance**: Supports GPU acceleration and frame skipping for better performance
- **Use Cases**: Reading street signs, labels, product information, environmental text

### Object / Obstacle Detection Feature

- **Purpose**: Detects nearby obstacles (people, cars, bikes, strollers, etc.) in a single camera frame and summarizes what is around the user (left / front / right) in a way that is easy to turn into speech.
- **Model**: Uses **Ultralytics YOLOv8** with configurable weights (default: `object_detection_backend_yolov8n.pt`).
- **Obstacle Awareness**:
  - Treats certain classes (person, car, bicycle, motorcycle, bus, truck, stroller, etc.) as “obstacles”
  - Measures bounding box size and screen position to decide whether something is big and centered enough to be a priority obstacle
- **Region Logic**:
  - Splits the frame into three regions: **left**, **front**, **right** (based on normalized box center `x`)
  - Stores at most one “best” obstacle and one “best” generic object per region
  - Chooses a single highest-priority detection for messaging, with priority:
    1. Obstacle in front  
    2. Obstacle on left/right  
    3. Object in front  
    4. Object on left/right
- **Summary Output**:
  - Builds a compact `summary` object for the Android app that includes:
    - `high_priority_warning` – whether there is something important to warn about
    - `message` – human-readable summary like “Person in front about 2 meters away”
    - `class_counts` – counts of each detected class
    - `closest` – info about the closest relevant detection
    - `processing_ms` – how long the frame took to process
    - `TTS_Output.messages` – list of messages ready for TTS

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
│   │   └── object_detection_backend.py # Object / obstacle detection HTTP endpoints (YOLOv8)
│   │
│   └── services/
│       ├── sms_service.py       # Handles Vonage SMS integration
│       ├── contact_lookup.py    # Contact lookup service
│       ├── voice_agent.py       # Decides which feature to use based on user's command
│       ├── voice_service.py     # Translates user's speech to text
│       └── navigation_service.py # Google Maps integration and navigation logic
│
├── text_detection.py            # TextDetector class (EasyOCR wrapper)
├── test_local.py                # CLI for testing OCR on static images
├── live_camera.py               # Live camera OCR demo script (optional)
├── main_ws.py                   # Standalone WebSocket server for text detection (optional)
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

**Note:** First installation may take several minutes as EasyOCR downloads pretrained models (~500MB) on first run.

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

# Text Detection Configuration (Optional)
MIN_CONF=0.6                    # Minimum confidence for OCR detections
STABILITY_WINDOW=5              # Number of frames for stability check
STABILITY_COUNT=3               # Minimum occurrences for stable text
WS_RAW_DIR=ws_raw               # Directory for saved frames
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

### Object / Obstacle Detection Endpoint
**HTTP Endpoint**

- **POST** `/object-detection/detect`
  - **Content-Type**: `multipart/form-data`
  - **Form fields**:
    - `file` (required): image frame (JPEG/PNG)
    - `frame_id` (optional, int): client frame index
    - `device_id` (optional, string): identifier of the sending device

## Text Detection (OCR) Feature

### Testing OCR on Static Images

```bash
python test_local.py
```

**Options:**
1. **Test with sample image** - Auto-generates a test image with text
2. **Test with your own image** - Provide path to your street sign or document image
3. **Exit**

### Live Camera OCR Demo (Optional)

Run real-time text detection from your webcam:

```bash
python live_camera.py --camera 0 --skip 5 --width 640 --out live_results
```

**Controls:**
- Press `q` to quit
- Press `s` to save annotated frame

**Flags:**
- `--camera N` : Camera index (default 0)
- `--skip N` : Process every Nth frame (default 5)
- `--width W` : Resize width for OCR (default 640)
- `--out DIR` : Output directory (default `live_results`)

### Standalone WebSocket Server for OCR (Optional)

For dedicated text detection service:

```bash
# With custom configuration
MIN_CONF=0.6 STABILITY_WINDOW=5 STABILITY_COUNT=3 uvicorn main_ws:app --host 0.0.0.0 --port 8000
```

**WebSocket endpoint:** `ws://<host>:8000/ws`

### EasyOCR Technology

- **Detection Model:** CRAFT (Character Region Awareness For Text detection)
- **Recognition Model:** CRNN (Convolutional Recurrent Neural Network)
- **Languages Supported:** 80+ (currently using English)
- **Model Size:** ~500MB (downloads automatically on first run)
- **Cache Location:** `~/.EasyOCR/model/` (Windows: `C:\Users\<username>\.EasyOCR\model\`)

### Performance Tips

1. **First run:** Slow (downloads models ~500MB)
2. **Subsequent runs:** Fast (models cached)
3. **Image quality:** Higher quality = better accuracy
4. **GPU acceleration:** Available if you have NVIDIA GPU with CUDA:
   ```python
   detector = TextDetector(gpu=True)
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
- **Text Detection** available via standalone scripts (`text_detection.py`, `test_local.py`, `live_camera.py`, `main_ws.py`)
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
- **EasyOCR** - Text detection and optical character recognition
- **OpenCV** - Image processing
- **NumPy** - Numerical operations
- **WebSocket** - Real-time bidirectional communication (face recognition, location tracking, navigation, text detection)
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

## Troubleshooting

### Navigation Issues

#### "Google Maps API error: NOT_FOUND"
- **Cause**: API key not configured or APIs not enabled
- **Fix**: 
  1. Check `.env` file has `GOOGLE_MAPS_API_KEY=your-key`
  2. Verify Directions API, Places API, and Geocoding API are enabled in Google Cloud Console
  3. Restart backend server after updating `.env`

#### "Location not available" or no directions returned
- **Cause**: Location WebSocket not connected before voice command
- **Fix**:
  1. Wait 2-3 seconds after opening app for location to initialize
  2. Check Android logs for "Location WebSocket connected"
  3. Verify location permissions are granted on device

### Text Detection Issues

#### "No text detected" in image
- Check image quality (lighting, focus)
- Ensure text is clearly visible
- Try lowering confidence threshold: `min_confidence=0.3`
- Make sure image file exists and path is correct

#### First run is very slow
- This is normal - EasyOCR downloads models (~500MB)
- Only happens once, models are cached
- Subsequent runs are much faster

#### Out of memory errors
- Reduce image size before processing
- Close other applications
- Consider using a machine with more RAM
- Lower the `--width` parameter in live camera mode

### General Issues

#### Virtual environment activation fails (Windows PowerShell)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Pip installation fails
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

---

## Development

The unified backend maintains clean separation between features while sharing common infrastructure. Features can be developed and tested independently, and the modular structure makes it easy to extend with additional features in the future.

### Running with Uvicorn + Nginx (Production)

In production, we recommend running Uvicorn on localhost and putting **Nginx** in front
as a reverse proxy. Nginx will:

- Listen on port 80 (and optionally 443 with TLS)
- Proxy HTTP traffic to Uvicorn (`127.0.0.1:8000`)
- Handle **WebSockets** for `/ws`, `/ws/verify`, `/location/ws`, `/navigation/ws`
- Allow larger uploads for image frames (object / obstacle detection and text detection)