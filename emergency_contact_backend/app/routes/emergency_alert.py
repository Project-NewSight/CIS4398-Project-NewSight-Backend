from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Request
import os 
import threading
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import EmergencyContact
from app.services.sms_service import send_sms
from datetime import datetime


def delete_photo_delay(path,delay=300):
     def _delete():
          if os.path.exists(path):
               os.remove(path)
               print(f"Deleted photo {path}")
     threading.Timer(delay,_delete).start()

router = APIRouter(prefix="/emergency_alert", tags=["emergency_alert"])

@router.post("/{user_id}")
async def send_emergency_alert(user_id: int, request: Request, db: Session = Depends(get_db), latitude: str = Form(...), longitude: str = Form(...), photo: UploadFile = File(None)):
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()

    if not contacts:
        raise HTTPException(status_code=404, detail="No emergency contacts found for this user")
    
    image_url = None
    if photo:
        temp_dir = "temp_photos"
        os.makedirs(temp_dir,exist_ok=True)
        filename = f"temp_{datetime.now().strftime('%H%M%S')}_{photo.filename}"
        temp_path = os.path.join(temp_dir,filename)

        with open(temp_path,"wb") as f:
            f.write(await photo.read())

        
        base_url = str(request.base_url).rstrip("/")
        #if "127.0.0.1" in base_url or "localhost" in base_url:
         #   base_url = "https://ourapidomain.com"  # replace with your backend URL

        image_url = f"{base_url}/temp_photos/{filename}"

    
    alert_message = (
        "This is an automated message from Project NewSight.\n" \
        "User may need assistance.\n" \
        f"Last known location: https://maps.google.com/?q={latitude},{longitude}\n"
    )
    if image_url:
        alert_message += f"Here is an image of the user's location: {image_url}\n"

    results = []
    for c in contacts:
        sms_result = send_sms(c.phone, alert_message)
        results.append({
        "contact_name": c.name,
        "phone": c.phone,
        "status": sms_result.get("status"),
        "error": sms_result.get("error")
        })

    if photo and os.path.exists(temp_path):
            delete_photo_delay(temp_path,delay=300)

    return{"message": "Alert sent to your emergency contact", "results":results, "photo_included": bool(photo), "image_url":image_url}