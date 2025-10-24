from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import EmergencyContact
from app.services.sms_service import send_sms

router = APIRouter(prefix="/emergency_alert", tags=["emergency_alert"])

@router.post("/{user_id}")
def send_emergency_alert(user_id: int, db: Session = Depends(get_db)):
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()

    if not contacts:
        raise HTTPException(status_code=404, detail="No emergency contacts found for this user")
    
    alert_message = (
        "This is an automated message from Project NewSight.\n" \
        "The user in need of assistance. Please try to contact them immediatly."
    )
    results = []
    for c in contacts:
        sms_result = send_sms(c.phone, alert_message)
        results.append({
        "contact_name": c.name,
        "phone": c.phone,
        "status": sms_result["status"],
        "error": sms_result["error"]
        })

    return{"message": "Alert sent to your emergency contact", "results":results}