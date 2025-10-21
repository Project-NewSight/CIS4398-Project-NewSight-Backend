from fastapi import FastAPI,Form,UploadFile, File
from fastapi.responses import JSONResponse

app = FastAPI(title="Emergency Contact API", version="1.0")

@app.get("/")
def root():
    return {"message": "Emergency Contact backend Running Sucessfully!"}

@app.post("/emergency/alert")
async def emergency_alert(
user_id: str = Form(...),
latitude: float = Form(...),
longitude: float = Form(...),
image: UploadFile = File(None)
):
    
    google_maps_url = f"https://maps.google.com/?q={latitude},{longitude}"

    response = {
    "status":"recieved",
    "user_id": user_id,
    "location": google_maps_url,
    "image_filename": image.filename if image else "No Image Uploaded"
        }

    return JSONResponse(content=response)