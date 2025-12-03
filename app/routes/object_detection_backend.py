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

# ---------- Distance / Obstacle configuration ----------

# Distance estimation parameters (no longer used for messaging, kept just in case)
DIST_K = float(os.getenv("DIST_K", "3.0"))        # Scale factor
DIST_MIN = float(os.getenv("DIST_MIN", "0.3"))    # Minimum distance in meters
DIST_MAX = float(os.getenv("DIST_MAX", "10.0"))   # Maximum distance in meters

# Obstacle logic
# Classes considered as "obstacles" for a walking user, based on YOLOv8 default COCO names
OBSTACLE_CLASSES = {
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "truck",
    "train",
    "bench",
    "chair",
    "sofa",
    "bed",
    "dining table",
    "potted plant",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "suitcase",
    "stroller",
}

# How big on screen (normalized area) to treat something as "very big"
OBSTACLE_AREA_THRESHOLD = float(os.getenv("OBSTACLE_AREA_THRESHOLD", "0.08"))
# How central (normalized center x) to treat something as "in front"
OBSTACLE_CENTER_MIN = float(os.getenv("OBSTACLE_CENTER_MIN", "0.33"))
OBSTACLE_CENTER_MAX = float(os.getenv("OBSTACLE_CENTER_MAX", "0.66"))


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
    """
    if normalized_height <= 0:
        return 999.0

    d = DIST_K / normalized_height
    d = max(DIST_MIN, min(d, DIST_MAX))
    return round(d, 2)


def estimate_direction(normalized_center_x: float) -> str:
    """
    Map a normalized horizontal center position to a coarse direction label.

    Returns:
        "left", "right" or "front"
    """
    if normalized_center_x < 0.33:
        return "left"
    elif normalized_center_x > 0.66:
        return "right"
    else:
        return "front"


def region_phrase(direction: str) -> str:
    """
    Helper to turn 'front'/'left'/'right' into a TTS-friendly phrase.
    """
    if direction == "front":
        return "in front of you"
    elif direction == "left":
        return "on your left"
    elif direction == "right":
        return "on your right"
    return "around you"


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

    Now also:
    - Analyzes regions (left, front, right)
    - Treats obstacles (person, car, bike, etc.) differently from generic objects
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

    # Track "best" obstacle and object per region
    regions: Dict[str, Dict[str, Optional[Detection]]] = {
        "front": {"obstacle": None, "object": None},
        "left": {"obstacle": None, "object": None},
        "right": {"obstacle": None, "object": None},
    }

    # 3. Parse detections, apply confidence and class filters
    for box in results.boxes:
        cls_id = int(box.cls[0])
        cls_name = results.names.get(cls_id, str(cls_id))
        conf = float(box.conf[0])

        # Confidence threshold filter
        if conf < CONF_THRESHOLD:
            continue

        # Optional class whitelist filter from TARGET_CLASSES
        if TARGET_CLASSES is not None and cls_name not in TARGET_CLASSES:
            continue

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        x_min = x1 / w
        y_min = y1 / h
        x_max = x2 / w
        y_max = y2 / h

        bbox_height_norm = (y_max - y_min)
        bbox_width_norm = (x_max - x_min)
        bbox_area_norm = bbox_height_norm * bbox_width_norm
        center_x_norm = (x_min + x_max) / 2.0

        # We no longer use numeric distance in messages; keep field for schema
        distance = None
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

        # ---- Decide if it's an "obstacle" vs generic object ----
        is_obstacle_class = cls_name in OBSTACLE_CLASSES

        # Extra condition: for front obstacles, we can also require "very big"
        # so we're not shouting for tiny detections far away.
        is_front = direction == "front"
        very_big = (bbox_area_norm >= OBSTACLE_AREA_THRESHOLD)

        # For front region, treat "big obstacles in front" as real obstacles.
        if is_obstacle_class and (not is_front or very_big):
            kind = "obstacle"
        else:
            kind = "object"

        # Store best detection per region & type (higher confidence wins)
        if direction in regions:
            existing = regions[direction][kind]
            if existing is None or det.confidence > existing.confidence:
                regions[direction][kind] = det

    # 4. Choose which region to talk about
    # Priority:
    #   1) Obstacle in front
    #   2) Obstacle left/right
    #   3) Object in front
    #   4) Object left/right
    chosen_region: Optional[str] = None
    chosen_det: Optional[Detection] = None
    chosen_is_obstacle: bool = False

    # 1) obstacle in front
    if regions["front"]["obstacle"] is not None:
        chosen_region = "front"
        chosen_det = regions["front"]["obstacle"]
        chosen_is_obstacle = True
    else:
        # 2) obstacle left/right
        for side in ["left", "right"]:
            if regions[side]["obstacle"] is not None:
                chosen_region = side
                chosen_det = regions[side]["obstacle"]
                chosen_is_obstacle = True
                break

    # 3) object in front
    if chosen_det is None and regions["front"]["object"] is not None:
        chosen_region = "front"
        chosen_det = regions["front"]["object"]
        chosen_is_obstacle = False

    # 4) object left/right
    if chosen_det is None:
        for side in ["left", "right"]:
            if regions[side]["object"] is not None:
                chosen_region = side
                chosen_det = regions[side]["object"]
                chosen_is_obstacle = False
                break

    # 5) Build summary message
    high_priority_warning = False
    summary_msg = "No obstacles detected around you."
    closest_info: Optional[Dict[str, Any]] = None
    tts_message = ""  # <-- only filled for obstacles

    if chosen_det is not None and chosen_region is not None:
        phrase = region_phrase(chosen_region)   # "in front of you", "on your left", "on your right"
        cls_name = chosen_det.cls

        if chosen_is_obstacle:
            # 🚨 Obstacle detected — include class name
            high_priority_warning = True
            summary_msg = f"Obstacle of {cls_name} {phrase}."
            tts_message = summary_msg  # speak it
        else:
            # ⚪ Objects do NOT produce TTS
            summary_msg = f"Object of {cls_name} {phrase}."
            tts_message = ""

        closest_info = {
            "cls": cls_name,
            "direction": chosen_det.direction,
            "confidence": chosen_det.confidence,
        }

    processing_ms = (time.perf_counter() - t_start) * 1000.0

    summary = {
        # Fields your current Android Summary class expects:
        "high_priority_warning": high_priority_warning,
        "message": summary_msg,
        "device_id": device_id,  # echo device_id back to the client

        # Extra fields
        "closest": closest_info,
        "class_counts": class_counts,
        "processing_ms": round(processing_ms, 1),

        # TTS output — empty string if no obstacle
        "TTS_Output": {
            "messages": tts_message
        },
    }



    logger.debug(
        f"Frame {frame_id}: {len(detections)} detections, "
        f"{processing_ms:.1f} ms processing time. "
        f"Chosen region: {chosen_region}, obstacle: {chosen_is_obstacle}"
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
