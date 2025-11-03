# Familiar Face Detection Router and Services
from deepface import DeepFace
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import numpy as np
import cv2
import os
import io
import base64
import boto3
import tempfile
import json
import time
import asyncio
from dotenv import load_dotenv

# Load .env file from project root (parent of app directory)
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=env_path, override=True)

router = APIRouter(tags=["familiar_face"])  # No prefix to maintain original paths

S3_BUCKET = os.getenv("AWS_S3_BUCKET_NAME", "newsight-storage")
S3_PREFIX = os.getenv("S3_PREFIX", "familiar_img/")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

DISTANCE_THRESHOLDS = {
    "VGG-Face": 0.67,
    "Facenet": 10,
    "Facenet512": 10,
    "ArcFace": 4.15,
    "Dlib": 0.6,
    "SFace": 0.593
}

MODEL_NAME = "VGG-Face"
DETECTOR_BACKEND = "retinaface"
DISTANCE_THRESHOLD = DISTANCE_THRESHOLDS.get(MODEL_NAME, 0.4)

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

CACHE_DIR = os.path.join(tempfile.gettempdir(), "familiar_faces_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

WS_MIN_INTERVAL_MS = 250


def sync_s3_faces_to_local():
    objs = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
    if "Contents" not in objs:
        return []

    local_files = []
    for obj in objs["Contents"]:
        key = obj["Key"]
        if not key.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        local_path = os.path.join(CACHE_DIR, os.path.basename(key))
        s3.download_file(S3_BUCKET, key, local_path)
        local_files.append(local_path)

    print(f"[S3] Synced {len(local_files)} faces to cache")
    return local_files


# WebSocket endpoints - registered directly in app/main.py to maintain original paths
async def ws_verify(websocket: WebSocket):
    await websocket.accept()
    print("[WS] connected to", websocket.url.path)
    last_ts = 0.0
    current_feature = None

    try:
        if not os.listdir(CACHE_DIR):
            try:
                sync_s3_faces_to_local()
                print("[WS] S3 sync complete")
            except Exception as e:
                print(f"[WS] S3 sync failed: {e}")

        while True:
            message = await websocket.receive()

            if "text" in message and message["text"] is not None:
                txt = message["text"]
                if txt == "ping":
                    await websocket.send_text("pong")
                    continue

                try:
                    data = json.loads(txt)
                    msg_type = data.get("type")

                    if msg_type == "hello":
                        current_feature = data.get("feature")
                        await websocket.send_text(
                            json.dumps({"ok": True, "note": "hello_ack", "feature": current_feature}))
                        continue

                    if msg_type == "frame" and "image_b64" in data:
                        jpeg_bytes = base64.b64decode(data.get("image_b64") or "")
                        await websocket.send_text(json.dumps({"ok": True, "note": "received", "len": len(jpeg_bytes)}))

                        await process_face_recognition(jpeg_bytes, websocket)
                        continue

                except Exception as e:
                    print(f"[WS] Error parsing text message: {e}")
                    pass
                continue

            if "bytes" not in message or message["bytes"] is None:
                continue

            now = time.time() * 1000.0
            if now - last_ts < WS_MIN_INTERVAL_MS:
                continue
            last_ts = now

            jpeg_bytes = message["bytes"]

            await process_face_recognition(jpeg_bytes, websocket)

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "ok": False, "error": f"server_exception: {e}"
            }))
        except Exception:
            pass


async def process_face_recognition(jpeg_bytes: bytes, websocket: WebSocket):

    try:

        npbuf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        img = cv2.imdecode(npbuf, cv2.IMREAD_COLOR)
        if img is None:
            await websocket.send_text(json.dumps({
                "ok": False,
                "error": "decode_failed"
            }))
            return

        if not os.listdir(CACHE_DIR):
            await websocket.send_text(json.dumps({
                "ok": True,
                "match": False,
                "note": "no_gallery_in_cache"
            }))
            return

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: DeepFace.find(
                img_path=img,
                db_path=CACHE_DIR,
                model_name=MODEL_NAME,
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=False,
                silent=True
            )
        )

        if not result or len(result[0]) == 0:
            await websocket.send_text(json.dumps({
                "ok": True,
                "match": False,
                "contactName": "Unknown",
                "confidence": 0.0,
                "note": "no_face_detected"
            }))
            return

        top = result[0].iloc[0]

        distance_col = next(
            (c for c in result[0].columns
             if "distance" in c.lower() or "cosine" in c.lower()
             or "euclidean" in c.lower()),
            None
        )

        if distance_col is None:
            await websocket.send_text(json.dumps({
                "ok": False,
                "error": "no_distance_column"
            }))
            return

        distance = float(top[distance_col])
        identity = os.path.basename(str(top.get("identity", "")))
        name_stem, _ext = os.path.splitext(identity)

        if distance > DISTANCE_THRESHOLD:
            print(f"[FACE] Rejected: {name_stem} (distance={distance:.4f}, threshold={DISTANCE_THRESHOLD})")
            await websocket.send_text(json.dumps({
                "ok": True,
                "match": False,
                "contactName": "Unknown",
                "confidence": 0.0,
                "distance": round(distance, 4),
                "note": "below_threshold"
            }))
            return

        confidence = max(0.0, min(1.0, 1.0 - distance))
        print(f"[FACE] Match: {name_stem} (distance={distance:.4f}, confidence={confidence:.4f})")

        await websocket.send_text(json.dumps({
            "ok": True,
            "match": True,
            "contactName": name_stem,
            "confidence": round(confidence, 4),
            "distance": round(distance, 4)
        }))

    except Exception as e:
        print(f"[FACE] Error processing frame: {e}")
        await websocket.send_text(json.dumps({
            "ok": False,
            "error": str(e)
        }))

