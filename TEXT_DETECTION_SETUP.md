# Text Detection Feature - Frontend Integration

## Overview

The text detection feature has been integrated into the unified NewSight backend API and is compatible with the `textdetecttest` frontend branch.

## WebSocket Endpoint

**URL**: `ws://YOUR_BACKEND_IP:8000/ws`

The unified WebSocket endpoint at `/ws` now supports **both** features:
- **Familiar Face Detection** - Existing functionality
- **Text Detection (OCR)** - New functionality ✨

The backend automatically routes to the correct feature handler based on the message format.

## Message Format

### Text Detection Request

```json
{
  "feature": "text_detection",
  "frame": "base64_encoded_jpeg_image"
}
```

### Text Detection Response

```json
{
  "text_string": "detected stable text",
  "detections": [
    {
      "text": "word",
      "confidence": 0.95,
      "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    }
  ],
  "full_text": "all detected text from current frame",
  "stable_text": "text that appeared consistently",
  "feature": "text_detection"
}
```

## Frontend Configuration

The frontend (`ReadTextActivity.java`) is already configured correctly:

### For Android Emulator:
```java
private static final String SERVER_WS_URL = "ws://10.0.2.2:8000/ws";
```

### For Physical Device:
Update to your computer's local IP:
```java
private static final String SERVER_WS_URL = "ws://192.168.1.XXX:8000/ws";
```

## How It Works

1. **Feature Detection**: The backend detects which feature to use based on the message format:
   - Messages with `{"feature": "text_detection", "frame": "..."}` → Text Detection
   - Messages with `{"type": "hello", "feature": "familiar_face"}` → Familiar Face
   - Binary JPEG bytes → Familiar Face

2. **Text Stability**: The backend implements a stability buffer:
   - Tracks the last N frames (default: 3)
   - Requires text to appear in M frames (default: 2)
   - Prevents flickering results
   - Automatically clears stale detections

3. **Reading Order**: Detected words are sorted top-to-bottom, left-to-right for natural reading order

## Configuration

Environment variables (optional):

```env
# Text Detection Configuration
MIN_CONF=0.5              # Minimum confidence threshold (0.0-1.0)
STABILITY_WINDOW=3        # Number of frames to track
STABILITY_COUNT=2         # Minimum occurrences for stable text
```

## Testing

### 1. Start Backend Server

```bash
# Navigate to backend directory
cd CIS4398-Project-NewSight-Backend

# Activate virtual environment
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Test with Frontend

1. Open Android Studio
2. Checkout `textdetecttest` branch
3. Update `SERVER_WS_URL` in `ReadTextActivity.java` if using physical device
4. Run app on emulator or device
5. Navigate to "Read Text" feature
6. Point camera at text (signs, labels, etc.)
7. Tap "Start Detection"

### 3. Expected Behavior

- ✅ Connection status shows "✓ Connected"
- ✅ Detected text appears in real-time
- ✅ Text-to-speech reads detected text automatically
- ✅ Text stabilizes after appearing in multiple frames
- ✅ Display clears when no text is visible

## Troubleshooting

### "✗ Disconnected" Status
- **Cause**: Cannot reach backend server
- **Fix**: 
  - Verify backend is running: `curl http://localhost:8000/`
  - For physical device: Check firewall allows port 8000
  - For physical device: Verify IP address is correct

### No Text Detected
- **Cause**: Low lighting, blurry image, or text too small
- **Fix**:
  - Improve lighting conditions
  - Hold camera steady
  - Move closer to text
  - Lower `MIN_CONF` in backend (restart required)

### Text Keeps Changing (Flickering)
- **Cause**: Stability settings too loose
- **Fix**: Increase `STABILITY_COUNT` to 3 or 4

### Text Appears Too Slowly
- **Cause**: Stability settings too strict
- **Fix**: Decrease `STABILITY_COUNT` to 2 or `STABILITY_WINDOW` to 3

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ Frontend (Android - textdetecttest branch)          │
│  ├─ ReadTextActivity.java                           │
│  ├─ FrameAnalyzer.java (captures & sends frames)    │
│  └─ WebSocketManager.java (handles connection)      │
└────────────────┬────────────────────────────────────┘
                 │ WebSocket: {"feature": "text_detection", "frame": "..."}
                 ▼
┌─────────────────────────────────────────────────────┐
│ Backend (Python - txt2dev branch)                   │
│  ├─ app/main.py (FastAPI app)                       │
│  ├─ app/routes/unified_websocket.py                 │
│  │   └─ Routes to text or face detection            │
│  ├─ app/routes/text_detection_routes.py             │
│  └─ app/services/text_detection_service.py          │
│      └─ TextDetector (EasyOCR wrapper)              │
└─────────────────┬───────────────────────────────────┘
                 │ Response: {"text_string": "...", "detections": [...]}
                 ▼
┌─────────────────────────────────────────────────────┐
│ Frontend receives and displays text                 │
│  ├─ Updates UI with detected text                   │
│  └─ Speaks text via TTS automatically               │
└─────────────────────────────────────────────────────┘
```

## Compatibility

✅ **Compatible with**: Frontend `textdetecttest` branch
✅ **Backward compatible**: Existing familiar face detection still works
✅ **Unified endpoint**: Both features use `/ws` - no frontend changes needed

## Alternative: Standalone Server

If you prefer to run text detection as a standalone service (original design):

```bash
# Run standalone text detection server
uvicorn main_ws:app --reload --host 0.0.0.0 --port 8000
```

This provides text detection only at `/ws` without other features.

## Next Steps

- ✅ Backend merged and organized
- ✅ Frontend compatibility ensured
- ✅ Unified WebSocket handler implemented
- **Ready to create PR to dev-branch!**

