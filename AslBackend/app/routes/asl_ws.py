import base64
import json
import asyncio
import logging
from collections import deque

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.asl_service import ASLModel, predict_letter_from_image
from ..config import CONFIDENCE_THRESHOLD

logger = logging.getLogger("asl_ws")
logger.setLevel(logging.DEBUG)

router = APIRouter()

# Simple smoothing window configuration

SMOOTH_WINDOW = 5
VALID_LETTERS = [chr(i) for i in range(ord("A"), ord("Z") + 1)]

@router.websocket("/ws/asl-stream")
async def asl_ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("ASL WebSocket connected")

    buffer = deque(maxlen=SMOOTH_WINDOW)

    # Instantiate model per-connection; handle failures gracefully
    try:
        model = ASLModel()
    except Exception as e:
        logger.exception("Failed to initialize ASL model: %s", e)
        try:
            await websocket.send_json({"error": f"model_load_failed: {e}"})
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
        return

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            if payload.get("feature") != "asl_detection":
                continue

            frame_b64 = payload.get("frame")
            if not frame_b64:
                logger.debug("[ASL] Frame missing in payload")
                continue

            frame_bytes = base64.b64decode(frame_b64)
            logger.debug("[ASL] Received frame, bytes=%d", len(frame_bytes))
            np_frame = np.frombuffer(frame_bytes, np.uint8)
            
            # Try JPEG decode first
            img = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)
            
            # If decode failed, try to interpret bytes as camera preview formats
            if img is None:
                byte_count = len(frame_bytes)
                logger.debug("[ASL] decode failed; attempting raw/YUV fallback, bytes=%d", byte_count)

                # Common resolutions to try (height, width)
                common_res = [(480, 640), (720, 1280), (1080, 1920)]

                # If this is full YUV420sp (NV21/NV12), total bytes == w*h*1.5
                handled = False
                for h, w in common_res:
                    expected_nv21 = int(w * h * 1.5)
                    expected_y = w * h
                    if byte_count == expected_nv21:
                        # extract Y plane (first w*h bytes) and reshape
                        y = np_frame[:expected_y]
                        img = y.reshape((h, w))
                        logger.debug("[ASL] Interpreted NV21/YUV420sp and extracted Y plane as (%d, %d)", h, w)
                        handled = True
                        break

                if not handled:
                    # If it's exactly a single-channel Y plane, reshape directly
                    for h, w in common_res:
                        if byte_count == w * h:
                            img = np_frame.reshape((h, w))
                            logger.debug("[ASL] Reshaped raw single-channel to (%d, %d)", h, w)
                            handled = True
                            break

                if not handled:
                    logger.debug("[ASL] Failed decoding frame (unknown byte count: %d)", byte_count)
                    continue

            # Run inference in threadpool
            loop = asyncio.get_running_loop()
            letter, conf = await loop.run_in_executor(None, model.predict_letter_from_image, img)

            logger.info("[ASL] Frame letter: %s, conf=%.2f", letter, conf)

            if letter is None or conf < CONFIDENCE_THRESHOLD:
                buffer.clear()
                await websocket.send_json({"letter": None})
                logger.debug("[ASL] Prediction below threshold, cleared buffer")
                continue

            buffer.append(letter)
            logger.debug("[ASL] Buffer content: %s", list(buffer))

            if len(buffer) == SMOOTH_WINDOW and len(set(buffer)) == 1:
                stable = buffer[0]
                logger.info("[ASL] Stable letter: %s", stable)
                await websocket.send_json({"letter": stable})
            else:
                await websocket.send_json({"letter": None})

    except WebSocketDisconnect:
        logger.info("ASL WebSocket client disconnected")
    except Exception as e:
        logger.exception("ASL WebSocket error: %s", e)
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
    finally:
        try:
            model.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("ASL WebSocket disconnected")
