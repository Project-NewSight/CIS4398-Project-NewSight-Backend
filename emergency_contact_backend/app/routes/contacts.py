from fastapi import APIRouter,Depends,HTTPException,Form
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import EmergencyContact


router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.post("/")
def add_contact(
        user_id: int = Form(...),
        name: str = Form(...),
        phone: str = Form(...),
        relationship: str = Form(None),
        address: str = Form(None),
        image_url: str = Form(None),
        db: Session = Depends(get_db)
):
    try:
        contact = EmergencyContact(user_id=user_id, name=name, phone=phone,relationship=relationship,address=address,image_url=image_url)
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return {"message": "Contact added", "contact": {"id": contact.contact_id, "name":name, "phone": phone}}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500,detail=f"Error adding Contact: {str(e)}")

@router.get("/{user_id}")
def get_contacts(user_id:int, db: Session = Depends(get_db)):
    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id== user_id).all()
    return contacts

@router.delete("/{contact_id}")
def delete_contact(contact_id:int, db: Session = Depends(get_db)):
    contact = db.query(EmergencyContact).filter(EmergencyContact.contact_id== contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
    return{"message": "Contact deleted"}
  