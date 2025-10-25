from deepface import DeepFace
from fastapi import FastAPI, UploadFile, File
import numpy as np, cv2, os, io, base64
from fastapi.middleware.cors import CORSMiddleware
from gtts import gTTS

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(HERE, "db")



@app.post("/verify")
async def verify_face(image: UploadFile = File(...)):
    buf = await image.read()
    img = cv2.imdecode(np.frombuffer(buf, np.uint8), cv2.IMREAD_COLOR)

    result = DeepFace.find(
        img_path=img,
        db_path=DB_DIR,
        model_name="ArcFace",
        detector_backend="opencv",
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



