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
pip install opencv-python numpy pillow easyocr
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
- `pillow` - Image handling
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

