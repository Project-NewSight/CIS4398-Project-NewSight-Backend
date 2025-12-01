from pydantic import BaseModel
from typing import Optional, List

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

class ClothingItemBase(BaseModel):
    closet_id: int
    category: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    style: Optional[str] = None
    genre: Optional[str] = None
    pattern: Optional[str] = None
    washing_instructions: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None        
    embedding_str: Optional[str] = None     


class ClothingItemCreate(ClothingItemBase):
    pass

class ClothingItemOut(ClothingItemBase):
    item_id: int

    class Config:
        orm_mode = True

class ClosetBase(BaseModel):
    user_id: int
    name: str
    description: Optional[str] = None

class ClosetCreate(ClosetBase):
    pass

class ClosetOut(ClosetBase):
    closet_id: int
    created_at: Optional[str] = None
    clothing_items: List[ClothingItemOut] = []  

    class Config:
        orm_mode = True