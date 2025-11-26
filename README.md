## Live Text Detection (macOS)

This repository includes a simple text detection module (`text_detection.py`) and a live camera demo script (`live_camera.py`) that uses EasyOCR to detect text from your Mac's camera in real time.

This README explains how to set up a virtual environment, install the necessary dependencies, and run the live camera script with recommended flags and troubleshooting tips for macOS (zsh).

---

## Quick start

1) Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install minimal runtime dependencies in the venv (recommended):

```bash

# Upgrade packaging and install core deps (Pillow removed)
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install opencv-python numpy
# CPU PyTorch wheel (recommended for EasyOCR speed)
python3 -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
python3 -m pip install easyocr
 # WebSocket server
 python3 -m pip install fastapi 'uvicorn[standard]'
```

If you prefer to install everything from `requirements.txt`, run:

```bash
python3 -m pip install -r requirements.txt
```

Note: `requirements.txt` may include packages for other parts of the project (e.g., `psycopg2-binary`) that require system libs to build. If that fails, use the minimal install above.

3) Run the live camera script (defaults are sensible):

```bash
source .venv/bin/activate
python3 live_camera.py --camera 0 --skip 5 --width 640 --out live_results
```

Controls while running:
- Press `q` to quit.
- Press `s` to save the latest full-resolution annotated frame to `live_results/`.

---

## Flags and tuning

- `--camera N` : Camera index (default 0). Try other indices if you have multiple cameras.
- `--skip N` : Process every Nth frame (default 5). Increasing this reduces CPU load and lag.
- `--width W` : Resize width (in px) used for OCR (default 640). Lower values = faster OCR but coarser bounding boxes.
- `--out DIR` : Output directory where saved annotated frames are written (default `live_results`).

Recommended starting point on CPU machines: `--skip 5 --width 640`. If you have less CPU, try `--skip 8 --width 480`.

---

## How detection works (brief)

- The script captures frames with OpenCV and uses a background worker thread to run EasyOCR inference on a resized copy of the frame.
- The worker returns detected bounding boxes (relative to the small image). The main thread scales those boxes to the full-resolution frame for display and saving.
- This design keeps the UI responsive while OCR runs in the background. You will see textual updates in the terminal like:

```
Main: queued frame 5 for OCR
OCR worker: Detected: 'STOP' (432 ms)
```

---

## macOS camera permissions

If OpenCV reports: `not authorized to capture video` or `camera failed to properly initialize`:

1. Open System Settings → Privacy & Security → Camera and allow access for Terminal (or your IDE).
2. If you previously denied access, reset the permission prompt for Terminal and re-run:

```bash
tccutil reset Camera com.apple.Terminal
# then re-run the script and accept the prompt when macOS asks
```

Note: on some macOS versions the Terminal bundle ID differs. If `tccutil` does not work, use the GUI to toggle camera permissions.

---

## Troubleshooting and tips

- If detection is too slow: increase `--skip` or decrease `--width`.
- If EasyOCR installation fails because of PyTorch issues, install a compatible PyTorch first (see https://pytorch.org) and then `pip install easyocr`.
- If `pip install -r requirements.txt` fails due to `psycopg2-binary` or other system-dependent packages, use the minimal install (above) for running the live demo.

---

## Example: Test OCR on a static image

Run a quick check that EasyOCR and the detector work on a saved image:

```bash
python3 - <<'PY'
from text_detection import TextDetector
d = TextDetector(gpu=False)
print(d.get_text_string('test_images/test_stop_sign.jpg'))
PY
```

---

## Next improvements you can enable

- Add FPS/latency overlay on the display (helpful for tuning).
- Add a multiprocessing worker for OCR to avoid GIL-related overhead.
- Toggle whether saved annotated images are full-resolution or small-resolution.

If you want, I can add any of these enhancements.

---

Files of interest
- `live_camera.py` — live capture + detection script
- `text_detection.py` — TextDetector class (EasyOCR wrapper)
- `test_local.py` — CLI for testing on single images

---

## Environment Variables (WebSocket server)

These configure `main_ws.py` when you run it with Uvicorn.

- `MIN_CONF`: Minimum confidence for a detection to be considered. Lower values accept more detections but may introduce noise.
   - Example: `MIN_CONF=0.6`

- `STABILITY_WINDOW`: Number of recent frames to consider for stability (rolling buffer size).
   - Example: `STABILITY_WINDOW=5`

- `STABILITY_COUNT`: Minimum occurrences of the same (normalized) text within the window to declare a stable phrase.
   - Example: `STABILITY_COUNT=3`

- `WS_RAW_DIR`: Output directory for saved frames (raw/annotated). Defaults to `ws_raw`.
   - Example: `WS_RAW_DIR=ws_raw`

-

### Recommended presets

- Fast lock (more jitter risk):
   ```zsh
   MIN_CONF=0.55 STABILITY_WINDOW=4 STABILITY_COUNT=2 uvicorn main_ws:app --host 0.0.0.0 --port 8000
   ```

- Faster/steadier:
   ```zsh
   MIN_CONF=0.6 STABILITY_WINDOW=5 STABILITY_COUNT=2 uvicorn main_ws:app --host 0.0.0.0 --port 8000
   ```

- Balanced:
   ```zsh
   MIN_CONF=0.65 STABILITY_WINDOW=6 STABILITY_COUNT=3 uvicorn main_ws:app --host 0.0.0.0 --port 8000
   ```

### Running the WebSocket server

Ensure the virtual environment is activated and dependencies are installed (`fastapi`, `uvicorn[standard]`, `easyocr`, `opencv-python`, `numpy`). Then run:

```zsh
source .venv/bin/activate
uvicorn main_ws:app --host 0.0.0.0 --port 8000
```

WebSocket endpoint: `ws://<host>:8000/ws`


License: MIT-style (project-specific license not included)
# Text Detection for Street Signs

Simple text detection using EasyOCR for detecting and reading text in street sign images.

## Prerequisites

- Python 3.8 or higher (tested on Python 3.11)
- Windows/Mac/Linux

## Complete Setup Instructions

### Step 1: Clone/Download the Repository

```bash
cd CIS4398-Project-NewSight-Backend
```

### Step 2: Create Virtual Environment

**On Windows (PowerShell):**
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\Activate
```

**On Windows (CMD):**
```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate
```

**On Mac/Linux:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Make sure virtual environment is activated (you should see (venv) in your terminal)

# Install all required packages
pip install -r requirements.txt

# Or install individually:
pip install opencv-python numpy easyocr
```

**Note:** First installation may take a few minutes.

### Step 4: Test the Setup

```bash
python test_local.py
```

Select option 1 to test with an auto-generated sample image.

**First run will be slower** as EasyOCR downloads pretrained models (~500MB). This only happens once.

## Testing

### Interactive Testing

```bash
python test_local.py
```

**Options:**
1. **Test with sample image** - Auto-generates a test image with text
2. **Test with your own image** - Provide path to your street sign image
3. **Exit**

### Example Test

```bash
python test_local.py
# Select option 1
# Wait for EasyOCR to initialize (first time only)
# View detected text output
```

## Project Structure

```
CIS4398-Project-NewSight-Backend/
├── text_detection.py       # Main text detection module
├── test_local.py            # Interactive testing script
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── venv/                    # Virtual environment (created by you)
├── test_images/             # Sample test images (auto-generated)
└── test_results/            # Output images with annotations (optional)
```

## Models & Technology

### EasyOCR
- **Detection Model:** CRAFT (Character Region Awareness For Text detection)
- **Recognition Model:** CRNN (Convolutional Recurrent Neural Network)
- **Languages Supported:** 80+ (currently using English)
- **Model Size:** ~500MB (downloads automatically on first run)
- **Cache Location:** `~/.EasyOCR/model/` (Windows: `C:\Users\<username>\.EasyOCR\model\`)

### Pretrained Models Sources
- [EasyOCR GitHub](https://github.com/JaidedAI/EasyOCR)
- [Roboflow Universe](https://universe.roboflow.com/) - Additional street sign datasets
- [Hugging Face](https://huggingface.co/models?pipeline_tag=image-to-text) - Various OCR models

## Troubleshooting

### Virtual Environment Issues

**Problem:** `venv\Scripts\Activate.ps1` gives permission error
```powershell
# Solution: Run this first
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Problem:** Can't find `python` command
```bash
# Try using python3 instead
python3 -m venv venv
```

### Installation Issues

**Problem:** `pip install` fails
```bash
# Solution: Upgrade pip first
python -m pip install --upgrade pip
```

**Problem:** Package installation is slow
- This is normal for first-time installation
- EasyOCR has large dependencies (PyTorch, etc.)
- Be patient, it can take 5-10 minutes

### Runtime Issues

**Problem:** "No text detected" in your image
- Check image quality (lighting, focus)
- Ensure text is clearly visible
- Try lowering confidence threshold: `min_confidence=0.3`
- Make sure image file exists and path is correct

**Problem:** First run is very slow
- This is normal - EasyOCR downloads models (~500MB)
- Only happens once, models are cached
- Subsequent runs are much faster

**Problem:** Out of memory errors
- Reduce image size before processing
- Close other applications
- Consider using a machine with more RAM

### Getting Help

If you encounter issues:
1. Make sure virtual environment is activated
2. Verify Python version: `python --version` (should be 3.8+)
3. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
4. Check if image path is correct
5. Try with the sample test first: `python test_local.py` → Option 1

## Performance Tips

1. **First run:** Slow (downloads models)
2. **Subsequent runs:** Fast (models cached)
3. **Image quality:** Higher quality = better accuracy
4. **Image size:** Larger images take longer but may be more accurate
5. **GPU acceleration:** Available if you have NVIDIA GPU with CUDA

### Enable GPU (Optional)

If you have an NVIDIA GPU with CUDA:
```python
detector = TextDetector(gpu=True)
```

## Dependencies

- `opencv-python` - Image processing
- `numpy` - Numerical operations
-- (Pillow was optional and has been removed from this project's requirements)
- `easyocr` - Text detection and recognition

See `requirements.txt` for specific versions.

## Example Output

```
Processing: test_images/test_stop_sign.jpg

TEXT OUTPUT:
--------------------------------------------------------------------------------

>>> 'STOP'

DETAILED RESULTS:
--------------------------------------------------------------------------------

Found 1 text element(s):

1. Text: 'STOP'
   Confidence: 0.956
```

---

**Questions or Issues?** Check the Troubleshooting section above or refer to the [EasyOCR documentation](https://github.com/JaidedAI/EasyOCR).

