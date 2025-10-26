from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Request
import os 
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import EmergencyContact
from app.services.sms_service import send_sms
from datetime import datetime
import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")

s3_client = boto3.client(
     "s3",
     region_name = AWS_REGION,
     aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID"),
     aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

)

router = APIRouter(prefix="/emergency_alert", tags=["emergency_alert"])

@router.post("/{user_id}")
async def send_emergency_alert(user_id: int, request: Request, db: Session = Depends(get_db), latitude: str = Form(...), longitude: str = Form(...), photo: UploadFile = File(None)):
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()

    if not contacts:
        raise HTTPException(status_code=404, detail="No emergency contacts found for this user")
    
    image_url = None

    if photo:
         try:
              filename = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{photo.filename}"
              s3_client.upload_fileobj(
                   photo.file,
                   BUCKET_NAME,
                   filename,
                   ExtraArgs={"ContentType": photo.content_type,"ACL":"public-read"}
              )
              image_url = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{filename}"

         except Exception as e:
              raise HTTPException(status_code=500, detail=f"Error uploading photo: {str(e)}")
              
    
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

    return{"message": "Alert sent to your emergency contact", "results":results, "photo_included": bool(photo), "image_url":image_url}