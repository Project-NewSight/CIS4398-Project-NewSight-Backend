from deepface import DeepFace
from fastapi import FastAPI, UploadFile, File
import numpy as np, cv2

#result = DeepFace.verify(img1_path="BillGates.jpg", img2_path="BillGates2.jpg")

#print(result)

app = FastAPI()

@app.post("/verify")
async def verify_face(image: UploadFile = File(...)):
    buf = await image.read()
    img = cv2.imdecode(np.frombuffer(buf, np.uint8), cv2.IMREAD_COLOR)

    result = DeepFace.find(
        img_path=img,
        db_path="./db",
        model_name="ArcFace",
        detector_backend="opencv",
        enforce_detection=False
    )

    if len(result[0]) == 0:
        return {"match": False, "message": "No match found"}

    top = result[0].iloc[0]

    distance_col = next(
        (c for c in result[0].columns
         if "distance" in c.lower() or "cosine" in c.lower() or "euclidean" in c.lower()),
        None
    )
    distance = float(top[distance_col]) if distance_col else None

    return {
        "match": True,
        "person": top["identity"],
        "distance": distance
    }



