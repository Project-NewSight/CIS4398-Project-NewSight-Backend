from fastapi import APIRouter, HTTPException
from app.services.sms_service import send_sms

router = APIRouter(prefix="/sms", tags=["SMS"])
@router.post("/send")
def send_sms_endpoint(to_number: str, message: str):
    try:
        send_sms(to_number,message)
        return {"status": "sucess","to":to_number, "message":message}
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
