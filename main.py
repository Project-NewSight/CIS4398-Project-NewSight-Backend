from deepface import DeepFace
from fastapi import FastAPI, UploadFile, File, HTTPException
import numpy as np, cv2, os, io, base64, boto3, tempfile
from fastapi.middleware.cors import CORSMiddleware
from gtts import gTTS
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect
import json, time


env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path, override=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

S3_BUCKET = os.getenv("S3_BUCKET", "newsight-storage")
S3_PREFIX = os.getenv("S3_PREFIX", "familiar_img/")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-2")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

CACHE_DIR = os.path.join(tempfile.gettempdir(), "familiar_faces_cache")
os.makedirs(CACHE_DIR, exist_ok=True)



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

    return local_files





"""@app.post("/verify")
async def verify_face(image: UploadFile = File(...)):
    upload_bytes = await image.read()
    img = cv2.imdecode(np.frombuffer(upload_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image: could not decode")

    gallery = sync_s3_faces_to_local()

    if not gallery:
        message = "No reference faces found in S3."
        tts = gTTS(message)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_b64 = base64.b64encode(buf.read()).decode("utf-8")
        return {
            "match": False,
            "contactName": None,
            "confidence": 0.0,
            "message": message,
            "audio": f"data:audio/mpeg;base64,{audio_b64}"
        }

    result = DeepFace.find(
        img_path=img,
        db_path=CACHE_DIR,
        model_name="ArcFace",
        detector_backend="retinaface",
        enforce_detection=False
    )

    if len(result[0]) == 0:
        message = "No match found"
        tts = gTTS(message)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_b64 = base64.b64encode(buf.read()).decode("utf-8")
        return {
            "match": False,
            "contactName": None,
            "confidence": 0.0,
            "message": message,
            "audio": f"data:audio/mpeg;base64,{audio_b64}"
        }

    top = result[0].iloc[0]

    distance_col = next(
        (c for c in result[0].columns
         if "distance" in c.lower() or "cosine" in c.lower() or "euclidean" in c.lower()),
        None
    )
    distance = float(top[distance_col]) if distance_col else None
    identity = os.path.basename(str(top.get("identity", "")))
    name_stem, _ext = os.path.splitext(identity)

    if distance is not None:

        confidence = max(0.0, min(1.0, 1.0 - distance))
    else:
        confidence = 0.0

    message = f"Match found. This looks like {name_stem}."
    tts = gTTS(message)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    audio_b64 = base64.b64encode(buf.read()).decode("utf-8")


    return {
        "match": True,
        "contactName": name_stem,
        "confidence": confidence,
        "message": message,
        "audio": f"data:audio/mpeg;base64,{audio_b64}"
    }
"""

WS_MIN_INTERVAL_MS = 250

@app.websocket("/ws")
@app.websocket("/ws/verify")
async def ws_verify(websocket: WebSocket):
    await websocket.accept()
    last_ts = 0.0


    if not os.listdir(CACHE_DIR):
        sync_s3_faces_to_local()

    try:
        while True:
            message = await websocket.receive()


            if "text" in message and message["text"] is not None:
                if message["text"] == "ping":
                    await websocket.send_text("pong")
                # silently ignore other text to keep behavior minimal
                continue


            if "bytes" not in message or message["bytes"] is None:
                continue

            now = time.time() * 1000.0
            if now - last_ts < WS_MIN_INTERVAL_MS:
                continue
            last_ts = now

            jpeg_bytes = message["bytes"]


            npbuf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            img = cv2.imdecode(npbuf, cv2.IMREAD_COLOR)
            if img is None:
                await websocket.send_text(json.dumps({
                    "ok": False, "error": "decode_failed"
                }))
                continue


            result = DeepFace.find(
                img_path=img,
                db_path=CACHE_DIR,
                model_name="ArcFace",
                detector_backend="retinaface",
                enforce_detection=False
            )

            if not result or len(result[0]) == 0:
                await websocket.send_text(json.dumps({
                    "ok": True, "match": False,
                    "contactName": None, "confidence": 0.0
                }))
                continue

            top = result[0].iloc[0]
            distance_col = next(
                (c for c in result[0].columns
                 if "distance" in c.lower() or "cosine" in c.lower()
                 or "euclidean" in c.lower()),
                None
            )
            distance = float(top[distance_col]) if distance_col else None

            identity = os.path.basename(str(top.get("identity", "")))
            name_stem, _ext = os.path.splitext(identity)

            confidence = max(0.0, min(1.0, 1.0 - distance)) if distance is not None else 0.0

            await websocket.send_text(json.dumps({
                "ok": True,
                "match": True,
                "contactName": name_stem,
                "confidence": confidence
            }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "ok": False, "error": f"server_exception: {e}"
            }))
        except Exception:
            pass



