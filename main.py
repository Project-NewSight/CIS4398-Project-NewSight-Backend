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
        img_path="BillGates.jpg",
        db_path="./db",
        model_name="ArcFace",
        detector_backend="retinaface",
        enforce_detection=False
    )

    if len(result[0]) == 0:
        return {"match": False, "message": "No match found"}

    top = result[0].iloc[0]
    return {
        "match": True,
        "person": top["identity"],
        "distance": top["ArcFace_cosine"]
    }



