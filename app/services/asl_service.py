# app/services/asl_service.py

import os
from typing import Optional, Tuple
import logging

import cv2
import numpy as np

logger = logging.getLogger("asl_service")

# Optional preprocessing flag (configured in app/config.py)
try:
    from app.config import PREPROCESSING_ENABLED
except Exception:
    PREPROCESSING_ENABLED = False


# Resolve model path from environment or config if present
_default_model = os.path.join("app", "models", "handmodel", "sign-language.tflite")
try:
    from app.config import ASL_MODEL_PATH as CONFIG_MODEL_PATH
except Exception:
    CONFIG_MODEL_PATH = None

MODEL_PATH = os.getenv("ASL_MODEL_PATH") or CONFIG_MODEL_PATH or _default_model


def index_to_letter(idx: int) -> str:
    if 0 <= idx <= 25:
        return chr(ord("A") + idx)
    return "?"


class ASLModel:
    """Wrapper around a TFLite interpreter used for ASL prediction.

    Instantiating this class will load the TFLite model. Loading is deferred
    until an instance is created so importing the module doesn't fail if the
    model or TensorFlow are not available.
    """

    def __init__(self, model_path: str = MODEL_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"TFLite model not found at: {model_path}")

        self.model_path = model_path
        # Import TensorFlow lazily; if it's not available, raise a clear error
        try:
            import tensorflow as tf
        except Exception as e:
            raise RuntimeError(f"tensorflow import failed: {e}")

        self._tf = tf
        self.interpreter = self._tf.lite.Interpreter(model_path=self.model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def predict(self, image: np.ndarray) -> Tuple[str, float]:
        logger.debug(f"[ASL] predict() called with image shape: {image.shape}")
        # Expect image in BGR (OpenCV default). Convert to grayscale for a 1-channel model
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 and image.shape[2] == 3 else image
        logger.debug(f"[ASL] Grayscale image shape: {gray.shape}")

        # Optional preprocessing (apply CLAHE to improve local contrast on
        # grayscale camera frames). Then resize to model input size.
        proc = gray
        if PREPROCESSING_ENABLED:
            try:
                if proc.ndim != 2:
                    proc = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                proc = clahe.apply(proc)
                logger.debug("[ASL] Applied CLAHE preprocessing")
            except Exception as e:
                logger.debug("[ASL] CLAHE preprocessing failed: %s", e)

        # Resize to model input size
        h, w = int(self.input_details[0]["shape"][1]), int(self.input_details[0]["shape"][2])
        resized = cv2.resize(proc, (w, h))
        logger.debug(f"[ASL] Resized to: {resized.shape}")

        input_data = np.expand_dims(resized.astype(np.float32) / 255.0, axis=-1)
        input_data = np.expand_dims(input_data, axis=0)
        logger.debug(f"[ASL] Input tensor shape: {input_data.shape}")

        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]["index"])[0]
        logger.debug(f"[ASL] Raw output shape: {output.shape}, first 5 values: {output[:5]}")

        idx = int(np.argmax(output))
        confidence = float(np.max(output))
        letter = index_to_letter(idx)
        logger.info(f"[ASL] Prediction: letter={letter}, index={idx}, confidence={confidence:.4f}")
        return letter, confidence

    # Backwards-compatible instance method name used elsewhere
    def predict_letter_from_image(self, image: np.ndarray) -> Tuple[str, float]:
        return self.predict(image)


# Lazy-shared model (created on first prediction) to preserve simple API
_shared_model: Optional[ASLModel] = None


def _get_shared_model() -> ASLModel:
    global _shared_model
    if _shared_model is None:
        _shared_model = ASLModel()
    return _shared_model


def predict_letter_from_image(image: np.ndarray) -> Optional[Tuple[str, float]]:
    """Compatibility helper used by routes: returns (letter, confidence) or None.

    This function will lazily load the shared model the first time it's called.
    """
    try:
        model = _get_shared_model()
        return model.predict(image)
    except Exception:
        # Avoid raising during request handling — routes will handle None result
        return None