import logging
import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException

from ..services.asl_service import ASLModel

logger = logging.getLogger("asl_http")
logger.setLevel(logging.DEBUG)

router = APIRouter()


@router.post("/asl/image")
async def asl_image_upload(file: UploadFile = File(...)):
    """Accept an uploaded image (JPEG/PNG) and return ASL prediction.

    Use this endpoint for mobile clients that prefer HTTP multipart upload.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    np_frame = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)

    if img is None:
        logger.debug("[ASL HTTP] Uploaded file could not be decoded as image")
        raise HTTPException(status_code=400, detail="Unable to decode image")

    # Run inference (blocking) in sync function; ASLModel handles internal preprocessing
    try:
        model = ASLModel()
        letter, conf = model.predict_letter_from_image(img)
    except Exception as e:
        logger.exception("[ASL HTTP] Inference error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            model.close()
        except Exception:
            pass

    return {"letter": letter, "confidence": float(conf) if conf is not None else None}
