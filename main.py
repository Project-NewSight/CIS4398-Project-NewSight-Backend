from deepface import DeepFace
from fastapi import FastAPI, UploadFile, File, HTTPException
import numpy as np, cv2, os, io, base64, boto3, tempfile, json, time
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from gtts import gTTS
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect

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




WS_MIN_INTERVAL_MS = 250

@app.websocket("/ws")
@app.websocket("/ws/verify")
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
                        await websocket.send_text(json.dumps({"ok": True, "note": "hello_ack", "feature": current_feature}))
                        continue


                    if msg_type == "frame" and "image_b64" in data:
                        jpeg_bytes = base64.b64decode(data.get("image_b64") or "")
                        await websocket.send_text(json.dumps({"ok": True, "note": "received", "len": len(jpeg_bytes)}))


                        loop = asyncio.get_running_loop()
                        if not os.listdir(CACHE_DIR):
                            try:
                                sync_s3_faces_to_local()
                                print(f"[WS] cache synced; files: {len(os.listdir(CACHE_DIR))}")
                            except Exception as e:
                                print(f"[WS] S3 sync failed: {e}")
                                await websocket.send_text(
                                    json.dumps({"ok": True, "match": False, "note": "no_gallery_in_cache"}))
                                continue
                        result = await loop.run_in_executor(
                            None,
                            lambda: DeepFace.find(
                                img_path=cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR),
                                db_path=CACHE_DIR,
                                model_name="ArcFace",
                                detector_backend="retinaface",
                                enforce_detection=False
                            )
                        )

                        if not result or len(result[0]) == 0:
                            await websocket.send_text(json.dumps({"ok": True, "match": False, "contactName": None, "confidence": 0.0}))
                        else:
                            top = result[0].iloc[0]
                            distance_col = next((c for c in result[0].columns if "distance" in c.lower() or "cosine" in c.lower() or "euclidean" in c.lower()), None)
                            distance = float(top[distance_col]) if distance_col else None
                            identity = os.path.basename(str(top.get("identity", "")))
                            name_stem, _ext = os.path.splitext(identity)
                            confidence = max(0.0, min(1.0, 1.0 - distance)) if distance is not None else 0.0
                            await websocket.send_text(json.dumps({"ok": True, "match": True, "contactName": name_stem, "confidence": confidence}))
                        continue

                except Exception:
                    pass
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
                await websocket.send_text(json.dumps({"ok": False, "error": "decode_failed"}))
                continue


            await websocket.send_text(json.dumps({"ok": True, "note": "received", "len": len(jpeg_bytes)}))


            loop = asyncio.get_running_loop()
            if not os.listdir(CACHE_DIR):
                try:
                    sync_s3_faces_to_local()
                    print(f"[WS] cache synced; files: {len(os.listdir(CACHE_DIR))}")
                except Exception as e:
                    print(f"[WS] S3 sync failed: {e}")
                    await websocket.send_text(json.dumps({"ok": True, "match": False, "note": "no_gallery_in_cache"}))
                    continue
            result = await loop.run_in_executor(
                None,
                lambda: DeepFace.find(
                    img_path=img,
                    db_path=CACHE_DIR,
                    model_name="ArcFace",
                    detector_backend="retinaface",
                    enforce_detection=False
                )
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
