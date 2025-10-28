# NewSight — Text Detection → Speech (macOS)

## Setup
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
brew install tesseract   # if not already installed

## Run
python ocr_to_speech.py path/to/image.png
