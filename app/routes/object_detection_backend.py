from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ultralytics import YOLO
from PIL import Image, UnidentifiedImageError
import io
import os
import time
import logging


# ---------- Logging configuration ----------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------- Configuration constants ----------

# Path to YOLO model weights (can be overridden via environment variable)
MODEL_PATH = os.getenv("MODEL_PATH", "object_detection_backend_yolov8n.pt")

# Confidence threshold to filter out low-score detections
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.4"))

# Optional class whitelist, e.g. "person,car,bicycle"
_target_classes_env = os.getenv("TARGET_CLASSES")
if _target_classes_env:
    TARGET_CLASSES = {c.strip() for c in _target_classes_env.split(",") if c.strip()}
else:
    TARGET_CLASSES = None  # No class filtering by default

# Distance estimation parameters
DIST_K = float(os.getenv("DIST_K", "3.0"))        # Scale factor
DIST_MIN = float(os.getenv("DIST_MIN", "0.3"))    # Minimum distance in meters
DIST_MAX = float(os.getenv("DIST_MAX", "10.0"))   # Maximum distance in meters


# ---------- Pydantic models ----------

class BBox(BaseModel):
    x_min: float  # normalized 0~1
    y_min: float
    x_max: float
    y_max: float


class Detection(BaseModel):
    cls: str
    confidence: float
    bbox: BBox
    distance_m: Optional[float] = None
    direction: Optional[str] = None


class DetectResponse(BaseModel):
    frame_id: Optional[int] = None
    detections: List[Detection]
    summary: Dict[str, Any]


# ---------- APIRouter instead of FastAPI application ----------

router = APIRouter(
    prefix="/object-detection",        # 所有路由都会带上这个前缀
    tags=["object_detection"],         # Swagger /docs 里的分组名
)


# ---------- Load YOLOv8 model (once at startup) ----------

try:
    logger.info(f"Loading YOLO model from: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    logger.info("YOLO model loaded successfully.")
except Exception as e:
    logger.exception("Failed to load YOLO model.")
    # Fail fast at startup if the model cannot be loaded
    raise


# ---------- Helper functions ----------

def estimate_distance(normalized_height: float) -> float:
    """
    Estimate an approximate real-world distance (in meters) from a normalized
    bounding-box height.

    The relationship is highly simplified and only meant for demo / relative
    ranking purposes, not precise measurement.

    Args:
        normalized_height: Bounding-box height divided by image height (0–1).

    Returns:
        A clamped distance in meters, between DIST_MIN and DIST_MAX.
        Returns a large placeholder distance (999.0) if the input is invalid.
    """
    if normalized_height <= 0:
        return 999.0

    d = DIST_K / normalized_height
    d = max(DIST_MIN, min(d, DIST_MAX))
    return round(d, 2)


def estimate_direction(normalized_center_x: float) -> str:
    """
    Map a normalized horizontal center position to a coarse direction label.

    Args:
        normalized_center_x: X coordinate of the bounding-box center, normalized
            by image width (0–1).

    Returns:
        A string representing direction:
            - "left"  if center is in the left third of the image
            - "right" if center is in the right third of the image
            - "front" otherwise
    """
    if normalized_center_x < 0.33:
        return "left"
    elif normalized_center_x > 0.66:
        return "right"
    else:
        return "front"


# ---------- Single-frame detection endpoint ----------

@router.post("/detect", response_model=DetectResponse)
async def detect(
    file: UploadFile = File(...),
    frame_id: Optional[int] = Form(None),
    device_id: Optional[str] = Form(None),
):
    """
    Run YOLO object detection on a single image frame and return structured
    detections along with a summarized view of the scene.

    This endpoint is intended for mobile / AR clients that stream frames to the
    backend. It performs the following steps:

    1. Safely decodes the uploaded image.
    2. Runs YOLO inference in a thread pool to avoid blocking the event loop.
    3. Normalizes bounding boxes, estimates distance and direction for each
       detection, and filters them by confidence (and optionally by class).
    4. Builds an aggregated summary including the closest object, counts per
       class, total processing time in milliseconds, and echoes back the
       device_id if provided by the client.
    """
    t_start = time.perf_counter()

    # 1. Read and decode image
    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except UnidentifiedImageError:
        logger.warning("Uploaded file is not a valid image.")
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")
    except Exception as e:
        logger.exception("Failed to decode uploaded image.")
        raise HTTPException(status_code=400, detail=f"Failed to decode image: {e}")

    w, h = image.size

    # 2. Run YOLO inference in a thread pool (non-blocking for the event loop)
    try:
        results_list = await run_in_threadpool(model, image, verbose=False)
        results = results_list[0]
    except Exception as e:
        logger.exception("Model inference failed.")
        raise HTTPException(status_code=500, detail=f"Inference error: {e}")

    detections: List[Detection] = []
    class_counts: Dict[str, int] = {}

    # 3. Parse detections, apply confidence and class filters
    for box in results.boxes:
        cls_id = int(box.cls[0])
        cls_name = results.names.get(cls_id, str(cls_id))
        conf = float(box.conf[0])

        # Confidence threshold filter
        if conf < CONF_THRESHOLD:
            continue

        # Optional class whitelist filter
        if TARGET_CLASSES is not None and cls_name not in TARGET_CLASSES:
            continue

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        x_min = x1 / w
        y_min = y1 / h
        x_max = x2 / w
        y_max = y2 / h

        bbox_height_norm = (y_max - y_min)
        center_x_norm = (x_min + x_max) / 2.0

        distance = estimate_distance(bbox_height_norm)
        direction = estimate_direction(center_x_norm)

        det = Detection(
            cls=cls_name,
            confidence=round(conf, 3),
            bbox=BBox(
                x_min=round(x_min, 4),
                y_min=round(y_min, 4),
                x_max=round(x_max, 4),
                y_max=round(y_max, 4),
            ),
            distance_m=distance,
            direction=direction,
        )
        detections.append(det)

        # Update per-class statistics
        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

    # 4. Build summarized view
    high_priority_warning = False
    summary_msg = "No obstacles detected."
    closest_info: Optional[Dict[str, Any]] = None

    if detections:
        closest = min(detections, key=lambda d: d.distance_m or 999.0)
        if (closest.distance_m or 999.0) < 1.5:
            high_priority_warning = True

        summary_msg = (
            f"{closest.direction.capitalize()} {closest.distance_m}m: "
            f"{closest.cls} detected"
        )

        closest_info = {
            "cls": closest.cls,
            "distance_m": closest.distance_m,
            "direction": closest.direction,
            "confidence": closest.confidence,
        }

    processing_ms = (time.perf_counter() - t_start) * 1000.0

    summary = {
        # Fields your current Android Summary class expects:
        "high_priority_warning": high_priority_warning,
        "message": summary_msg,
        "device_id": device_id,  # echo device_id back to the client

        # Extra fields (safe to ignore on the client if you don't model them yet):
        "closest": closest_info,
        "class_counts": class_counts,
        "processing_ms": round(processing_ms, 1),

        # New TTS output
        "TTS_Output": {
            "messages": summary_msg
        },
    }

    logger.debug(
        f"Frame {frame_id}: {len(detections)} detections, "
        f"{processing_ms:.1f} ms processing time."
    )

    return DetectResponse(
        frame_id=frame_id,
        detections=detections,
        summary=summary,
    )


@router.get("/health")
async def health():
    """
    Lightweight health check endpoint.

    Returns:
        A simple JSON payload indicating that the service is alive.
    """
    return {"status": "ok"}
