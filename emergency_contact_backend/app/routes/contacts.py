from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import EmergencyContact
from app.schemas import EmergencyContactOut

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.get("/{user_id}", response_model=list[EmergencyContactOut])
def get_contacts(user_id:int, db: Session = Depends(get_db)):
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()
    if not contacts:
        raise HTTPException(status_code=404,detail="No contacts found for this user.")
    return contacts