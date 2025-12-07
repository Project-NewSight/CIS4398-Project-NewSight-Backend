# Project NewSight - Backend API

Project NewSight is an assistive technology backend service designed to help visually impaired users with AI-powered features including face recognition, voice navigation, object detection, text reading, emergency alerts, ASL detection, and smart clothing recognition.

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Features](#features)
4. [Tech Stack](#tech-stack)
5. [Requirements](#requirements)
6. [Setup Instructions](#setup-instructions)
7. [Running the Servers](#running-the-servers)
8. [Environment Variables](#environment-variables)
9. [Future Work](#future-work)

---

## Overview

This backend consists of three separate deployments:

**Main dev-branch** - The primary unified backend with 7 integrated features (Port 8000)

**AslBackend** - ASL detection feature in a separate folder (Port 8001)

**color-cue** - Clothing recognition feature in a separate folder (Port 8002)

**Why are AslBackend and color-cue separate?**
These two features were last-minute integrations before the final merge to main. To avoid breaking the currently working features in dev-branch, we kept them in their own self-contained folders with separate dependencies. They can run on different ports and share the same database.

---

## Project Structure

```
CIS4398-Project-NewSight-Backend/
│
├── app/                          # Main dev-branch (Port 8000)
│   ├── main.py                   # FastAPI entry point
│   ├── db.py                     # Database connection
│   ├── models.py                 # SQLAlchemy models
│   ├── schemas.py                # Pydantic schemas
│   ├── routes/                   # API route handlers
│   │   ├── contacts.py
│   │   ├── emergency_alert.py
│   │   ├── sms_routes.py
│   │   ├── familiar_face.py
│   │   ├── voice_routes.py
│   │   ├── location_routes.py
│   │   ├── navigation_routes.py
│   │   ├── text_detection_routes.py
│   │   ├── object_detection_backend.py
│   │   └── unified_websocket.py
│   └── services/                 # Business logic
│       ├── sms_service.py
│       ├── contact_lookup.py
│       ├── voice_agent.py
│       ├── voice_service.py
│       ├── navigation_service.py
│       └── text_detection_service.py
│
├── AslBackend/                   # ASL Detection (Port 8001)
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── asl_http.py
│   │   │   └── asl_ws.py
│   │   └── services/
│   │       └── asl_service.py
│   └── requirements.txt
│
├── color-cue/                    # Clothing Recognition (Port 8002)
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   └── colorcue.py
│   │   └── services/
│   │       ├── colorcue_service.py
│   │       ├── google_vision_service.py
│   │       └── recommendation_service.py
│   └── requirements.txt
│
├── requirements.txt              # Main branch dependencies
└── README.md
```

---

## Features

### Main dev-branch Features (Port 8000)

#### 1. Emergency Contact & Alert System
**Status: 100% Complete**

Allows users to register trusted emergency contacts and automatically send alerts during emergencies. When triggered, the system sends SMS messages with GPS location and photo to all registered contacts.

**How it works:**
- User registers emergency contacts in the database
- During emergency, the app captures GPS coordinates and a photo
- Photo is uploaded to AWS S3
- SMS alerts are sent to all contacts via Vonage API with location link

**Impact:** Critical safety feature that gives users peace of mind, knowing help can be notified instantly in dangerous situations.

---

#### 2. Familiar Face Detection
**Status: 100% Complete**

Real-time face recognition to identify familiar contacts using camera feed. Helps users recognize friends, family, and acquaintances.

**How it works:**
- Users upload photos of familiar people to AWS S3
- Camera frames are sent via WebSocket to the backend
- DeepFace library matches faces against the gallery
- System returns the person's name and confidence score

**Impact:** Enables social interactions by helping users identify who's around them without needing to ask.

---

#### 3. Voice Command
**Status: 100% Complete**

The voice command system acts as an intelligent supervisor that routes user requests to appropriate features. Users can control the entire system hands-free by saying "Hey Guide" followed by any command.

**How it works:**
- Wake word detection listens for "Hey Guide" using Groq Whisper
- Once activated, the user's command is transcribed to text using Groq Whisper (large-v3-turbo model)
- Groq LLaMa 3.1-8b-instant acts as an intelligent router, analyzing the transcribed text to determine user intent
- The LLM identifies which feature to activate from available options:
  - OBJECT_DETECTION - "What's in front of me?"
  - TEXT_DETECTION - "Read this sign"
  - NAVIGATION - "Take me to CVS"
  - FACIAL_RECOGNITION - "Who is this person?"
  - EMERGENCY_CONTACT - "Send emergency alert"
  - ASL_DETECTOR - "Translate sign language"
  - COLOR_CUE - "What color is this shirt?"
- Sub-features automatically activate when needed:
  - HAPTIC_FEEDBACK - Vibration alerts for navigation and emergencies
  - TRANSIT_ASSIST - Public transit info when user mentions bus/train
  - OBJECT_DETECTION - Real-time obstacle detection during navigation
- The system executes the identified feature and provides voice feedback
- For navigation requests, it fetches GPS location, gets directions, and starts turn-by-turn guidance immediately

**Impact:** Transforms the entire application into a voice-first experience. Users never need to touch their phone or navigate menus, making all features instantly accessible through natural conversation. This is critical for visually impaired users who benefit from hands-free operation while walking or in situations where they can't safely interact with a touchscreen.

---

#### 4. Navigation
**Status: 100% Complete**

Provides turn-by-turn walking directions with voice guidance. Users can say "Take me to CVS" and get step-by-step walking directions.

**How it works:**
- Voice command triggers navigation with destination
- Google Maps Directions API calculates walking route
- Places API finds nearest locations for generic destinations (CVS, Starbucks)
- Geocoding API resolves addresses
- WebSocket streams real-time GPS updates to track user position
- Voice announces turns at 100m, 50 feet, and 25 feet before each turn
- Proximity detection automatically advances to next step as user walks
- AR-style overlay shows distance, direction arrows, and current instruction on camera feed

**Impact:** Gives users independence to walk anywhere confidently without assistance. The hands-free voice guidance and real-time position tracking ensure they never get lost.

---

#### 5. Transit
**Status: 100% Complete**

Public transportation navigation that guides users through bus and train journeys. Automatically activates when walking time exceeds 45 minutes or when user explicitly requests transit.

**How it works:**
- TransitApp API finds nearest bus/train stops based on user location
- Plans complete transit journey with multiple route options
- Provides schedules, arrival times, and estimated travel duration
- Shows real-time service alerts and delays
- Determines transit mode automatically (bus, train, subway) or based on user request
- Combines walking navigation to the stop with transit route guidance
- Gives step-by-step instructions: "Walk to Main St bus stop, take Bus 23 northbound for 3 stops"
- Smart navigation automatically switches from walking to transit when walking time > 45 minutes

**Impact:** Expands user mobility far beyond walking distance. Users can navigate entire cities independently using public transportation, opening up job opportunities, social activities, and essential services that would otherwise be inaccessible.

---

#### 6. Text Detection (OCR)
**Status: 100% Complete**

Real-time text detection and reading from camera feed. Helps users read signs, labels, documents, and any environmental text.

**How it works:**
- Camera frames sent via WebSocket
- EasyOCR library detects and recognizes text using CRAFT + CRNN models
- Stability filters ensure consistent text across multiple frames to avoid false readings
- Detected text is read aloud via text-to-speech

**Impact:** Allows users to read anything in their environment independently, from street signs to product labels.

---

#### 7. Object / Obstacle Detection
**Status: 100% Complete**

Detects nearby obstacles like people, cars, bikes, and strollers in real-time using YOLOv8. Warns users about potential hazards in their path.

**How it works:**
- Camera frames analyzed by YOLOv8 model
- Objects classified and distance estimated based on bounding box size
- Frame divided into left/front/right regions
- Priority given to obstacles directly in front
- TTS-ready output like "Person in front about 2 meters away"

**Impact:** Critical safety feature that prevents collisions and helps users navigate crowded environments safely.

---

### AslBackend Features (Port 8001)

#### 8. ASL (American Sign Language) Detection
**Status: 90% Complete (Separate Deployment)**

Real-time ASL hand sign recognition to convert sign language into text/letters. Uses TensorFlow Lite model with MediaPipe hand tracking.

**How it works:**
- Camera frames sent via HTTP or WebSocket
- MediaPipe detects and tracks hand landmarks
- TensorFlow Lite model classifies the hand sign
- Returns predicted letter with confidence score

**Impact:** Enables communication between sign language users and the system, expanding accessibility beyond visual impairment.

**Why separate:** TensorFlow 2.12 dependency conflicts with main branch requirements. Last-minute integration kept isolated to preserve dev-branch stability.

---

### color-cue Features (Port 8002)

#### 9. Color Cue (Clothing Recognition & Virtual Closet)
**Status: 100% Complete (Separate Deployment)**

Smart clothing detection and virtual closet management. Helps users identify their clothing, organize their wardrobe, and get outfit suggestions.

**How it works:**
- User uploads photos of clothing items (front + tag photos)
- Multiple Roboflow models detect color, pattern, and category
- Google Cloud Vision API provides additional color analysis
- OCR extracts washing instructions and material from tags
- Items stored in database with metadata
- AI suggests outfit combinations based on occasion, weather, and style

**Impact:** Helps users maintain independence in choosing their outfits and ensures appropriate clothing for different occasions.

**Why separate:** Roboflow and Google Cloud Vision dependencies conflict with main branch. Last-minute integration kept isolated to avoid breaking working features.

---

## Tech Stack

### Main dev-branch
- **FastAPI** - Web framework
- **PostgreSQL + SQLAlchemy** - Database
- **AWS S3** - Image storage
- **DeepFace** - Face recognition
- **EasyOCR** - Text detection
- **Ultralytics YOLOv8** - Object detection
- **Vonage API** - SMS messaging
- **Groq API** - Speech-to-text and LLM
- **Google Maps APIs** - Directions, Places, Geocoding (for Navigation)
- **TransitApp API** - Public transit routes, schedules, and alerts (for Transit)
- **WebSocket** - Real-time communication

### AslBackend
- **FastAPI**
- **TensorFlow 2.12**
- **TensorFlow Lite** - Mobile inference
- **MediaPipe** - Hand tracking

### color-cue
- **FastAPI**
- **Google Cloud Vision API** - Color and pattern detection
- **Roboflow Inference SDK** - Custom clothing models
- **ColorThief** - Dominant color extraction
- **AWS S3** - Image storage
- **PostgreSQL** - Database

---

## Requirements

### System Requirements
- Python 3.11+
- PostgreSQL 12+
- 8GB RAM minimum (16GB recommended)
- 5GB free disk space
- Internet connection for API calls

### Cloud Services Required
- AWS account with S3 bucket
- PostgreSQL database (local or cloud)
- Vonage account for SMS
- Groq API account
- Google Cloud account:
  - Google Maps APIs (Directions, Places, Geocoding)
  - Vision API (for color-cue only)
- TransitApp API account
- Roboflow account (for color-cue only)

---

## Setup Instructions

### Main dev-branch Setup

**1. Create Virtual Environment**

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

**2. Install Dependencies**

```bash
pip install -r requirements.txt
```

Note: First run downloads EasyOCR models (~500MB), this is normal.

**3. Setup PostgreSQL**

```bash
createdb newsight_db
```

**4. Create .env File**

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/newsight_db

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=us-east-2
AWS_S3_BUCKET_NAME=newsight-storage
AWS_S3_FOLDER_NAME=emergency-uploads
S3_PREFIX=familiar_img/

# Vonage SMS
VONAGE_API_KEY=your-vonage-api-key
VONAGE_API_SECRET=your-vonage-api-secret
VONAGE_FROM_NUMBER=+1234567890

# Groq AI
GROQ_API_KEY=your-groq-api-key

# Google Maps
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# TransitApp API
TRANSIT_API_KEY=your-transit-api-key

# Text Detection (Optional - has defaults)
MIN_CONF=0.6
STABILITY_WINDOW=5
STABILITY_COUNT=3
```

**Important:** Enable Directions API, Places API, and Geocoding API in Google Cloud Console and set up billing.

---

### AslBackend Setup

**1. Navigate to AslBackend**

```bash
cd CIS4398-Project-NewSight-Backend
cd AslBackend
```

**2. Create Virtual Environment**

```bash
python -m venv venv_asl
source venv_asl/bin/activate  # Mac/Linux
venv_asl\Scripts\activate     # Windows
```

**3. Install Dependencies**

```bash
pip install -r requirements.txt
```

**4. Verify Model Exists**

```bash
ls app/models/*.tflite
```

The TensorFlow Lite model file should be present in `app/models/`.

---

### color-cue Setup

**1. Navigate to color-cue**

```bash
cd CIS4398-Project-NewSight-Backend
cd color-cue
```

**2. Create Virtual Environment**

```bash
python -m venv venv_colorcue
source venv_colorcue/bin/activate  # Mac/Linux
venv_colorcue\Scripts\activate     # Windows
```

**3. Install Dependencies**

```bash
pip install -r requirements.txt
```

**4. Setup Google Cloud Vision**

- Create a Google Cloud Project
- Enable Cloud Vision API
- Create a Service Account and download JSON key file
- Save the key file in a secure location

**5. Create .env File**

Create `.env` in the `color-cue/` folder:

```env
# Database (shared)
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/newsight_db

# AWS S3 (shared)
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=us-east-2
AWS_S3_BUCKET_NAME=newsight-storage

# Google Cloud Vision
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google-vision-key.json

# Roboflow (currently hardcoded in colorcue_service.py)
ROBOFLOW_API_KEY=your-roboflow-api-key
```

Note: The Roboflow API key is currently hardcoded in `app/services/colorcue_service.py` around line 21-27. For production, update it to read from environment variables.

---

## Running the Servers

### Main dev-branch (Port 8000)

```bash
cd CIS4398-Project-NewSight-Backend
source venv/bin/activate  # or venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Access at: http://127.0.0.1:8000  
API Docs: http://127.0.0.1:8000/docs

---

### AslBackend (Port 8001)

```bash
cd CIS4398-Project-NewSight-Backend
cd AslBackend
source venv_asl/bin/activate  # or venv_asl\Scripts\activate
uvicorn app.main:app --reload --port 8001
```

Access at: http://127.0.0.1:8001  
API Docs: http://127.0.0.1:8001/docs

---

### color-cue (Port 8002)

```bash
cd CIS4398-Project-NewSight-Backend
cd color-cue
source venv_colorcue/bin/activate  # or venv_colorcue\Scripts\activate
uvicorn app.main:app --reload --port 8002
```

Access at: http://127.0.0.1:8002  
API Docs: http://127.0.0.1:8002/docs

---

### Running All Three Together

You can run all three backends simultaneously in separate terminal windows. They share the same PostgreSQL database but run on different ports.

---

## Environment Variables

### Main dev-branch Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `AWS_ACCESS_KEY_ID` | Yes | AWS access key for S3 |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS secret key for S3 |
| `AWS_REGION` | Yes | AWS region (e.g., us-east-2) |
| `AWS_S3_BUCKET_NAME` | Yes | S3 bucket name |
| `AWS_S3_FOLDER_NAME` | Yes | Emergency photos folder |
| `S3_PREFIX` | Yes | Familiar faces folder |
| `VONAGE_API_KEY` | Yes | Vonage API key for SMS |
| `VONAGE_API_SECRET` | Yes | Vonage API secret |
| `VONAGE_FROM_NUMBER` | Yes | Vonage phone number |
| `GROQ_API_KEY` | Yes | Groq API key for voice |
| `GOOGLE_MAPS_API_KEY` | Yes | Google Maps API key |
| `TRANSIT_API_KEY` | Yes | TransitApp API key |
| `MIN_CONF` | No | OCR confidence threshold (default: 0.6) |
| `STABILITY_WINDOW` | No | OCR stability window (default: 5) |
| `STABILITY_COUNT` | No | OCR stability count (default: 3) |

### AslBackend Environment Variables

AslBackend has minimal dependencies and primarily uses local model inference. Database connection is optional unless you're storing ASL detection history.

### color-cue Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `AWS_ACCESS_KEY_ID` | Yes | AWS access key for S3 |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS secret key for S3 |
| `AWS_REGION` | Yes | AWS region |
| `AWS_S3_BUCKET_NAME` | Yes | S3 bucket name |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to Google Vision JSON key |
| `ROBOFLOW_API_KEY` | Yes* | Roboflow API key (*currently hardcoded) |

**Security Note:** Replace hardcoded credentials with environment variables before production deployment.

---

## Future Work

The following improvements are planned for future versions:

**Integration**
- Merge AslBackend into main unified backend
- Merge color-cue into main unified backend
- Unified WebSocket handler for all features
- Single-port deployment

**Performance**
- GPU acceleration for all ML models
- Model quantization for faster mobile inference
- Caching for frequent API calls

**Features**
- Multi-language support for OCR and voice
- Offline mode with cached models
- Indoor navigation support
- Word and phrase detection for ASL
- Wearable device integration

**Infrastructure**
- Docker containers for deployment
- CI/CD pipeline
- API authentication and rate limiting
- Monitoring and logging

---

## Architecture

```
┌─────────────────────────────────────────────┐
│         Android Frontend App                │
│    (Camera, Mic, GPS, UI)                   │
└──────────┬────────────┬────────────┬────────┘
           │            │            │
           v            v            v
    ┌──────────┐  ┌─────────┐  ┌──────────┐
    │  Main    │  │  ASL    │  │ color-   │
    │ Backend  │  │ Backend │  │  cue     │
    │ :8000    │  │ :8001   │  │ :8002    │
    └────┬─────┘  └────┬────┘  └────┬─────┘
         │             │            │
         └─────────────┴────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
           v                       v
    ┌─────────────┐         ┌─────────┐
    │ PostgreSQL  │         │  AWS S3 │
    └─────────────┘         └─────────┘
```

---

## Testing with Android

For Mac users testing with physical Android device:

```bash
# Add ADB to PATH
export PATH=$PATH:$HOME/Library/Android/sdk/platform-tools

# Check connected devices
adb devices

# Setup port forwarding
adb -s <device_serial> reverse tcp:8000 tcp:8000
adb -s <device_serial> reverse tcp:8001 tcp:8001
adb -s <device_serial> reverse tcp:8002 tcp:8002

# Verify
adb -s <device_serial> reverse --list
```

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Maps APIs](https://developers.google.com/maps/documentation)
- [TransitApp API Documentation](https://transitapp.com/apis)
- [DeepFace GitHub](https://github.com/serengil/deepface)
- [EasyOCR GitHub](https://github.com/JaidedAI/EasyOCR)
- [Ultralytics YOLOv8](https://docs.ultralytics.com/)
- [Google Cloud Vision](https://cloud.google.com/vision/docs)
- [Roboflow Documentation](https://docs.roboflow.com/)

---

**Project NewSight** - See Beyond Limits With The Help Of AI

Developed by NewSight Team 
