"""
Configuration settings for the ASL Backend
"""
import os

# WebSocket Configuration
WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8000"))

# Model Configuration
ASL_MODEL_REPO = "handmodel/sign-language"
FACIAL_EXPRESSION_MODEL_REPO = "HardlyHumans/Facial-expression-detection"

# Model Paths (will be downloaded on first run)
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
ASL_MODEL_PATH = os.path.join(MODELS_DIR, "handmodel", "sign-language.tflite")

# Processing Configuration
HAND_LANDMARK_IMAGE_SIZE = 64  # ASL model expects 64x64 images
# Note: the actual model input size is read from the TFLite model at runtime
# (`app/services/asl_service.ASLModel` reads interpreter input_details). Keep
# this value only as a hint for downstream processing.
CONFIDENCE_THRESHOLD = 0.15  # Minimum confidence for predictions (production)

# Testing helpers
# Set `PREPROCESSING_ENABLED=True` to enable lightweight preprocessing (CLAHE)
# before resizing. This can improve contrast for grayscale camera frames.
PREPROCESSING_ENABLED = True

# If you need to temporarily relax the confidence threshold for testing only,
# set `USE_TEST_THRESHOLD=True` and adjust `TEST_CONFIDENCE_THRESHOLD`.
USE_TEST_THRESHOLD = False
TEST_CONFIDENCE_THRESHOLD = 0.12


# ASL Character Mapping (26 letters + space + other gestures)
ASL_CHARACTERS = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    'space', 'del', 'nothing'
]

