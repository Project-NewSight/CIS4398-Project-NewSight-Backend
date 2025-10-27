from deepface import DeepFace
from fastapi import FastAPI, UploadFile, File
import numpy as np, cv2, os, io, base64, boto3, tempfile
from fastapi.middleware.cors import CORSMiddleware
from gtts import gTTS
from dotenv import load_dotenv


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





@app.post("/verify")
async def verify_face(image: UploadFile = File(...)):
    upload_bytes = await image.read()
    img = cv2.imdecode(np.frombuffer(upload_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid image: could not decode")

    gallery = sync_s3_faces_to_local()

    if not gallery:
        message = "No reference faces found in S3."
        tts = gTTS(message)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_b64 = base64.b64encode(buf.read()).decode("utf-8")
        return {"match": False, "message": message, "audio": f"data:audio/mpeg;base64,{audio_b64}"}

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
    person = os.path.basename(top["identity"])

    message = f"Match found. This looks like {person}."
    tts = gTTS(message)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    audio_b64 = base64.b64encode(buf.read()).decode("utf-8")


    return {
        "match": True,
        "person": person,
        "distance": distance,
        "message": message,
        "audio": f"data:audio/mpeg;base64,{audio_b64}"
    }



