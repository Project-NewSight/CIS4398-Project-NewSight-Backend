# Project NewSight – Unified Backend API

This backend service powers **Project NewSight**, combining two major features:
1. **Emergency Contact and Alert System** - Allows users to register trusted contacts and automatically send location, photo, and alert messages during emergencies
2. **Familiar Face Detection** - Real-time face recognition to identify familiar contacts using DeepFace and WebSocket connections

## Overview

The backend is built with **FastAPI** and integrates with:
- **AWS S3** – for securely storing emergency photos and familiar face images
- **PostgreSQL (via SQLAlchemy)** – for managing user contact data
- **Vonage SMS API** – for sending alerts to trusted contacts
- **DeepFace** – for face recognition and matching
- **WebSocket** – for real-time face recognition processing

The system ensures that in an emergency, user data is safely transmitted, messages are delivered quickly, and photos are uploaded to a secure cloud location. Additionally, it provides real-time face recognition capabilities to identify familiar contacts.

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

### Shared Infrastructure
- Clean, modular structure for easy integration with the Project NewSight mobile frontend
- CORS middleware enabled for cross-origin requests
- Static file serving for temporary photos
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
│   ├── schemas.py               # Pydantic schemas
│   ├── main.py                  # FastAPI entry point (unified app)
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── contacts.py          # CRUD endpoints for emergency contacts
│   │   ├── emergency_alert.py  # Endpoint for sending emergency alerts
│   │   ├── sms_routes.py        # SMS endpoint
│   │   └── familiar_face.py     # Face recognition WebSocket handlers
│   │
│   └── services/
│       ├── sms_service.py       # Handles Vonage SMS integration
│       └── contact_lookup.py   # Contact lookup service
│
├── .env                         # Environment variables (not committed)
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
```

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

### Static Files

- `/temp_photos/` - Static file serving for temporary photos

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

Both features are designed to run independently:
- **Emergency Contact** routes are prefixed and organized under `/contacts`, `/emergency_alert`, `/sms`
- **Familiar Face Detection** uses WebSocket endpoints at `/ws` and `/ws/verify`
- No route conflicts or overlapping functionality
- Shared infrastructure (CORS, static files, database) is unified

### Modular Design

- Routes are organized in separate modules for easy maintenance
- Services are separated from route handlers for better code organization
- Easy to add new features following the existing router pattern

---

## Technologies Used

- **FastAPI** - Modern, fast web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Relational database
- **AWS S3** - Cloud storage
- **Vonage API** - SMS messaging
- **DeepFace** - Face recognition library
- **OpenCV** - Image processing
- **NumPy** - Numerical operations
- **WebSocket** - Real-time bidirectional communication
- **Boto3** - AWS SDK for Python
- **Pydantic** - Data validation
- **gTTS** - Text-to-speech (for future features)

---

## Development

The unified backend maintains clean separation between features while sharing common infrastructure. Both features can be developed and tested independently, and the modular structure makes it easy to extend with additional features in the future.
