#When this endpoint is hit the send sms function is called
from fastapi import APIRouter, HTTPException
from app.services.sms_service import send_sms

router = APIRouter(prefix="/sms", tags=["SMS"])
@router.post("/send")
def send_sms_endpoint(to_number: str, message: str):
    try:
        send_sms(to_number,message) #sending the text message
        return {"status": "sucess","to":to_number, "message":message}
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
