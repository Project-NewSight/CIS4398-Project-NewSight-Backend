from PIL import Image, ImageOps, ImageFilter
import pytesseract
from gtts import gTTS
import subprocess, sys

IMG = sys.argv[1] if len(sys.argv) > 1 else "sample.png"

# --- Preprocess for better OCR ---
img = Image.open(IMG)

# 1) upscale for clearer glyphs
img = img.resize((img.width*2, img.height*2), Image.LANCZOS)

# 2) grayscale + autocontrast + light sharpen
gray = ImageOps.grayscale(img)
gray = ImageOps.autocontrast(gray, cutoff=1)
gray = gray.filter(ImageFilter.SHARPEN)

# 3) gentle binarization (tweak 160–190 if needed)
bw = gray.point(lambda p: 255 if p > 170 else 0)

# Use single-line mode for short lines, block mode otherwise.
# Start with psm 6 (block); if short result, retry psm 7 (single line).
def ocr(p):
    return pytesseract.image_to_string(p, config="--oem 1 --psm 6").strip()

text = ocr(bw)
if len(text.split()) < 3:  # if it looks too short, try single-line
    text = pytesseract.image_to_string(bw, config="--oem 1 --psm 7").strip()

if not text:
    text = "No readable text found."

print("----- OCR OUTPUT -----")
print(text)
print("----------------------")

mp3_path = "spoken.mp3"
gTTS(text=text, lang="en").save(mp3_path)
subprocess.run(["afplay", mp3_path], check=False)
