# Project NewSight - Backend API

Project NewSight is an assistive technology backend service designed to help visually impaired users with AI-powered features including face recognition, voice navigation, object detection, text reading, emergency alerts, ASL detection, and smart clothing recognition.

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Features](#features)
4. [Tech Stack](#tech-stack)
5. [Requirements](#requirements)
6. [Build, Install & Configuration](#build-install--configuration)
7. [Running the Servers](#running-the-servers)
8. [Testing](#testing)
9. [Environment Variables](#environment-variables)
10. [Known Issues](#known-issues)
11. [Future Work](#future-work)

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
├── tests/                        # Test suite
│   ├── conftest.py              # Pytest configuration and fixtures
│   ├── test_contacts.py         # Emergency contacts tests
│   ├── test_emergency_alert.py  # Emergency alert tests
│   ├── test_familiar_face.py    # Face recognition tests
│   ├── test_voice_commands.py    # Voice command tests
│   ├── test_navigation.py       # Navigation tests
│   ├── test_location.py         # Location/GPS tests
│   ├── test_text_detection.py  # OCR tests
│   ├── test_object_detection.py # Object detection tests
│   ├── test_sms_routes.py      # SMS route tests
│   ├── test_websocket.py       # WebSocket handler tests
│   ├── test_asl_detection.py  # ASL detection unit tests
│   └── test_color_cue.py       # Color-cue unit tests
├── run_all_tests.py             # Test runner with coverage
├── .coveragerc                   # Coverage configuration
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
- **pytest** - Testing framework
- **pytest-cov** - Coverage plugin for pytest
- **coverage** - Code coverage reporting

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

## Build, Install & Configuration

This section provides detailed instructions to build, install, and configure the entire Project NewSight backend on target devices.

### Prerequisites

Before beginning installation, ensure you have:
- Python 3.11 or higher installed
- PostgreSQL 12+ installed and running
- Git installed for cloning the repository
- Internet connection for downloading dependencies
- Admin/sudo privileges for installing system packages

### Target Devices

This backend can be deployed on:
- **Development machines** (Windows, macOS, Linux) for local testing
- **Physical Android devices** connected via USB (for mobile app testing)
- **Cloud servers** (AWS EC2, DigitalOcean, etc.) for production deployment

---

### Main dev-branch - Build & Install

**1. Clone Repository**

```bash
git clone <repository-url>
cd CIS4398-Project-NewSight-Backend
```

**2. Create Virtual Environment**

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

**Note:** Testing dependencies (pytest, pytest-cov, coverage) are included in `requirements.txt` and will be installed automatically.

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

### AslBackend - Build & Install

**1. Navigate to AslBackend Directory**

```bash
# From repository root
cd CIS4398-Project-NewSight-Backend
cd AslBackend
```

**2. Create Isolated Virtual Environment**

Note: AslBackend requires a separate virtual environment due to TensorFlow dependency conflicts.

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

### color-cue - Build & Install

**1. Navigate to color-cue Directory**

```bash
# From repository root
cd CIS4398-Project-NewSight-Backend
cd color-cue
```

**2. Create Isolated Virtual Environment**

Note: color-cue requires a separate virtual environment due to Roboflow and Google Vision dependency conflicts.

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

### Build Automation

**Note on Makefiles:** This project does not currently use Makefiles or build automation scripts. All dependencies are managed through Python's pip package manager via `requirements.txt` files.

For streamlined setup, you can create a simple build script:

**Linux/Mac (setup.sh):**
```bash
#!/bin/bash
# Main backend setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# AslBackend setup
cd AslBackend
python3 -m venv venv_asl
source venv_asl/bin/activate
pip install -r requirements.txt
cd ..

# color-cue setup
cd color-cue
python3 -m venv venv_colorcue
source venv_colorcue/bin/activate
pip install -r requirements.txt
cd ..
```

**Windows (setup.bat):**
```batch
@echo off
REM Main backend setup
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt

REM AslBackend setup
cd AslBackend
python -m venv venv_asl
call venv_asl\Scripts\activate
pip install -r requirements.txt
cd ..

REM color-cue setup
cd color-cue
python -m venv venv_colorcue
call venv_colorcue\Scripts\activate
pip install -r requirements.txt
cd ..
```

---

### Configuring for Target Devices

#### Android Device Testing

To test with a physical Android device connected to your development machine:

**1. Install Android Debug Bridge (ADB)**

ADB is included with Android Studio. Verify installation:

```bash
# Mac/Linux
export PATH=$PATH:$HOME/Library/Android/sdk/platform-tools  # Mac
export PATH=$PATH:$HOME/Android/Sdk/platform-tools           # Linux

# Verify
adb version
```

**2. Enable USB Debugging on Android Device**

On your Android device:
- Go to Settings > About Phone
- Tap "Build Number" 7 times to enable Developer Mode
- Go to Settings > Developer Options
- Enable "USB Debugging"

**3. Connect Device and Verify**

```bash
# Connect device via USB
adb devices

# Expected output:
# List of devices attached
# ABC123456789    device
```

**4. Setup Port Forwarding**

Forward backend ports from your development machine to the Android device:

```bash
# Forward main backend
adb reverse tcp:8000 tcp:8000

# Forward AslBackend (if running)
adb reverse tcp:8001 tcp:8001

# Forward color-cue (if running)
adb reverse tcp:8002 tcp:8002

# Verify forwarding
adb reverse --list
```

**5. Test Connection from Android**

The Android app can now access the backend at:
- Main backend: `http://localhost:8000`
- AslBackend: `http://localhost:8001`
- color-cue: `http://localhost:8002`

**6. Remove Port Forwarding (when done)**

```bash
adb reverse --remove-all
```

#### Production Server Deployment

For deploying to a production server (AWS, DigitalOcean, etc.):

**1. Install System Dependencies**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3-pip python3-venv postgresql

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**2. Clone and Setup**

Follow the standard setup instructions above, but use production environment variables.

**3. Run Servers**

```bash
# Run main backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run AslBackend (in separate terminal)
cd AslBackend
uvicorn app.main:app --host 0.0.0.0 --port 8001

# Run color-cue (in separate terminal)
cd color-cue
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

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

## Testing

This project includes a comprehensive test suite covering all major features of the backend. Tests use pytest with coverage reporting to ensure code quality and reliability.

### What We're Testing

The test suite covers all main features with unit and integration tests:

- **Emergency Contacts & Alerts** (`test_contacts.py`, `test_emergency_alert.py`)
  - Contact CRUD operations
  - Emergency alert sending with location and photos
  - SMS integration
  - Database error handling

- **Familiar Face Detection** (`test_familiar_face.py`)
  - Gallery synchronization from S3
  - Face recognition logic
  - Gallery management operations

- **Voice Commands** (`test_voice_commands.py`)
  - Wake word detection ("Hey Guide")
  - Speech-to-text transcription
  - Command routing to features
  - Navigation and emergency command recognition

- **Navigation** (`test_navigation.py`)
  - Navigation session start/stop
  - Directions retrieval
  - Health check endpoints
  - Session validation

- **Location/GPS** (`test_location.py`)
  - GPS coordinate retrieval
  - Reverse geocoding
  - Permission handling
  - Accuracy validation

- **Text Detection (OCR)** (`test_text_detection.py`)
  - Text detection service info
  - Text normalization
  - Stability filtering
  - Confidence threshold filtering

- **Object Detection** (`test_object_detection.py`)
  - Obstacle detection logic
  - Direction identification (left/front/right)
  - Confidence threshold filtering

- **SMS Routes** (`test_sms_routes.py`)
  - SMS sending functionality
  - Error handling

- **WebSocket Handlers** (`test_websocket.py`)
  - Message routing
  - Error handling
  - Connection management

- **ASL Detection** (`test_asl_detection.py`)
  - Letter mapping logic
  - Confidence threshold validation
  - Unit tests for ASL backend

- **Color-Cue** (`test_color_cue.py`)
  - Color detection logic
  - Multi-color detection
  - Clothing category classification
  - Pattern detection

### Testing Tools

- **pytest** (v7.4.3) - Primary testing framework
- **pytest-cov** (v4.1.0) - Coverage plugin for pytest
- **pytest-asyncio** (v0.21.1) - Async test support
- **coverage** - Code coverage reporting and HTML generation

### Running Tests

#### Basic Test Execution

Run all tests with verbose output:

```bash
cd CIS4398-Project-NewSight-Backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pytest tests/ -v
```

#### Run Tests with Coverage

Use the provided test runner script to generate comprehensive coverage reports:

```bash
python run_all_tests.py
```

This will:
- Run all tests from the `tests/` directory
- Generate coverage for main app, AslBackend, and color-cue
- Create an HTML coverage report in `htmlcov_combined/`
- Display a terminal coverage report

#### Run Individual Test Files

Test specific features:

```bash
# Test emergency contacts
pytest tests/test_contacts.py -v

# Test voice commands
pytest tests/test_voice_commands.py -v

# Test navigation
pytest tests/test_navigation.py -v
```

#### Run Specific Test Functions

```bash
# Run a specific test
pytest tests/test_contacts.py::test_add_contact -v
```

### Coverage Reports

After running tests with coverage, you can view reports in two ways:

#### HTML Coverage Report

```bash
# Generate HTML report (included in run_all_tests.py)
coverage html -d htmlcov_combined

# Open the report
# Windows: start htmlcov_combined\index.html
# Mac: open htmlcov_combined/index.html
# Linux: xdg-open htmlcov_combined/index.html
```

The HTML report provides:
- Line-by-line coverage for all files
- Percentage coverage per module
- Missing line indicators
- Interactive file browsing

#### Terminal Coverage Report

```bash
# Generate terminal report
coverage report --skip-empty
```

This displays a summary table showing:
- Coverage percentage per file
- Number of statements, missing lines, and excluded lines

### Test Structure

The test suite is organized in the `tests/` directory:

- **`conftest.py`** - Pytest configuration and shared fixtures:
  - `db_session` - In-memory SQLite database for each test
  - `client` - FastAPI TestClient with database override
  - `sample_user_id` - Sample user ID fixture
  - `sample_contact_data` - Sample contact data fixture

- **Test Files** - Each feature has a corresponding test file:
  - Tests use mocking for external services (AWS S3, Vonage SMS, Google APIs)
  - Database tests use in-memory SQLite for isolation
  - WebSocket tests are marked as skipped (require real-time connection)
  - Some ML model tests are skipped (require heavy dependencies)

### Test Configuration

Coverage configuration is defined in `.coveragerc`:
- Excludes virtual environments, migrations, and generated files
- Includes all app modules and test files
- Configures HTML report output directory

### Notes

- Some tests are marked with `@pytest.mark.skip` for features requiring:
  - Real-time connections (WebSocket tests)
  - Heavy ML dependencies (DeepFace, YOLO)
  - External API keys (Google Vision, Roboflow)
- Database tests use in-memory SQLite for fast, isolated testing
- External services (S3, SMS, APIs) are mocked using `unittest.mock`
- Coverage reports combine all three backends (main, AslBackend, color-cue)

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

## Known Issues

This section documents known bugs and limitations in the current release.

### Main dev-branch Issues

**1. EasyOCR First Run Delay**
- **Issue:** First time running text detection takes 5-10 minutes to download models (~500MB)
- **Workaround:** Pre-download models by running `python -c "import easyocr; easyocr.Reader(['en'])"`
- **Severity:** Low - only affects first run

**2. WebSocket Connection Timeout**
- **Issue:** WebSocket connections may timeout after 5 minutes of inactivity
- **Workaround:** Mobile app sends periodic ping messages to keep connection alive
- **Severity:** Low - handled by app reconnection logic

**3. Transit API Limited Coverage**
- **Issue:** TransitApp API may not have data for all cities/regions
- **Workaround:** System falls back to walking navigation when transit data unavailable
- **Severity:** Medium - depends on user location

**4. Face Recognition Performance**
- **Issue:** DeepFace face matching can be slow on CPU-only systems (2-3 seconds per frame)
- **Workaround:** Enable GPU acceleration if available, or reduce frame processing rate
- **Severity:** Medium - affects real-time performance

**5. Google Maps API Rate Limits**
- **Issue:** Free tier has daily request limits (may affect heavy usage)
- **Workaround:** Implement caching for frequent routes, or upgrade to paid tier
- **Severity:** Low - only affects high-volume testing

### AslBackend Issues

**1. TensorFlow Version Conflicts**
- **Issue:** TensorFlow 2.12 conflicts with main branch dependencies
- **Workaround:** Run in separate virtual environment on different port
- **Severity:** High - requires separate deployment

**2. Hand Tracking Lighting Requirements**
- **Issue:** MediaPipe hand tracking requires good lighting conditions
- **Workaround:** Users should ensure adequate lighting for best results
- **Severity:** Medium - affects detection accuracy

### color-cue Issues

**1. Dependency Conflicts**
- **Issue:** Roboflow and Google Vision dependencies conflict with main branch
- **Workaround:** Run in separate virtual environment on different port
- **Severity:** High - requires separate deployment

**2. Google Vision API Costs**
- **Issue:** Google Cloud Vision API charges per request after free tier
- **Workaround:** Monitor API usage and implement request caching
- **Severity:** Medium - cost consideration for production

**3. Roboflow API Key Hardcoded**
- **Issue:** Roboflow API key is hardcoded in `colorcue_service.py` instead of environment variable
- **Workaround:** Manually update key in code or move to .env file
- **Severity:** Medium - security concern for production

### General Issues

**1. Database Connection Pool Exhaustion**
- **Issue:** Under heavy load, database connection pool may exhaust
- **Workaround:** Increase pool size in database configuration
- **Severity:** Low - only affects high-concurrency scenarios

**2. Large Image Upload Size**
- **Issue:** Uploading very large images (>10MB) may cause timeout
- **Workaround:** Compress images before upload, or increase timeout settings
- **Severity:** Low - rare occurrence

**3. Multiple Simultaneous Navigation Sessions**
- **Issue:** Running multiple navigation sessions on same server may cause session confusion
- **Workaround:** Ensure unique session IDs for each user
- **Severity:** Low - proper session management handles this

### Planned Fixes

The following issues are planned to be addressed in future releases:
- Merge AslBackend and color-cue into main branch (resolve dependency conflicts)
- Implement proper API key management for all services
- Add connection pooling and caching layers
- Optimize model loading and inference times
- Add comprehensive error handling and logging

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

**Testing Infrastructure:** The project includes a comprehensive test suite (`tests/`) with pytest-based unit and integration tests. Tests use in-memory SQLite for database operations and mock external services. Coverage reports combine all three backends for unified reporting.

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
