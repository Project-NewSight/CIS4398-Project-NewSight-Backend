from pydantic import BaseModel

class EmergencyContactOut(BaseModel):
    contact_id: int
    user_id: int
    name: str
    phone: str
    relationship: str
    address: str
    image_url: str | None=None

    class Config:
        orm_mode = True