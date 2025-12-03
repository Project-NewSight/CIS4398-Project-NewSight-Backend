# app/routes/asl_detector.py
from fastapi import APIRouter, UploadFile, File
import cv2
import numpy as np
import asyncio
from ..services.asl_service import predict_letter_from_image, ASLModel


router = APIRouter(prefix="/asl", tags=["ASL"])


@router.post("/predict_letter")
async def predict_letter(file: UploadFile = File(...)):
    """
    Receives an image frame and returns the predicted ASL letter.
    """
    contents = await file.read()
    np_frame = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)

    if img is None:
        return {"letter": None, "message": "Invalid image"}

    # Keep image in BGR (OpenCV default). The service expects BGR frames.
    loop = asyncio.get_running_loop()
    letter, confidence = await loop.run_in_executor(None, predict_letter_from_image, img)

    if letter is not None:
        return {"letter": letter, "confidence": float(confidence)}
    else:
        return {"letter": None, "message": "No letter detected", "confidence": float(confidence)}


@router.get("/model_status")
async def model_status():
    """Check whether the ASL TFLite model can be loaded and return basic info.

    This runs model initialization in a thread pool to avoid blocking the event loop.
    """
    loop = asyncio.get_running_loop()

    def _check():
        try:
            m = ASLModel()
            info = {
                "model_path": m.model_path,
                "input_shape": m.input_details[0]["shape"],
            }
            return {"ok": True, "info": info}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return await loop.run_in_executor(None, _check)
