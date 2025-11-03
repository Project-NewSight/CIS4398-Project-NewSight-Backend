#Main API for the emergency contact feature
import os
from fastapi import FastAPI,Form,UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from app.routes import sms_routes
from app.routes import contacts
from app.routes import emergency_alert
from app.routes import contacts

app = FastAPI(title="Emergency Contact API", version="1.0")

app.mount("/temp_photos", StaticFiles(directory="temp_photos"), name="temp_photos")


app.include_router(sms_routes.router)
app.include_router(contacts.router)
app.include_router(emergency_alert.router)
app.include_router(contacts.router)

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
    saved_filename = None

    if image:
        os.makedirs("uploads",exist_ok=True)
        saved_filename = os.path.join("uploads", image.filename)
        with open(saved_filename, "wb") as buffer:
            buffer.write(await image.read())

    response = {
    "status":"recieved",
    "user_id": user_id,
    "location": google_maps_url,
    "image_saved": bool(image),
    "image_filename": image.filename if image else "No Image Uploaded"
        }

    return JSONResponse(content=response)