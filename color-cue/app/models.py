#This object represents and emergency contact record in the database
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    Float,
    Text,
    func
)
from sqlalchemy.orm import relationship
from app.db import Base
from pgvector.sqlalchemy import Vector



class EmergencyContact(Base):
    __tablename__ = "emergencycontact"

    contact_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String(100))
    phone = Column(String(20))
    relationship = Column(String(50))
    address = Column(String(255))
    image_url = Column(String(255))


class ClothingItem(Base):
    __tablename__ = "clothingitem"

    item_id = Column(Integer, primary_key = True, index = True, autoincrement = True)
    closet_id = Column(Integer, ForeignKey("closet.closet_id"), nullable=False)
    category = Column(String(20))
    color = Column(String(50))
    material = Column(String(100))
    style = Column(String(100))
    genre = Column(String(100))
    pattern = Column(String(100))
    washing_instructions = Column(String(100))
    notes = Column(String(255))
    printed_text = Column(String(255))   # NEW  — text/logo printed on clothing

    image_url = Column(String(255))   
    tag_front_url = Column(String(255))   # NEW
    tag_back_url = Column(String(255))   # S3 image link
    embedding_str = Column(String)       # Placeholder for vector embedding
    embedding = Column(Vector(512))
    primary_color = Column(String(50))
    secondary_colors = Column(String(255))       
    is_multicolor = Column(Boolean, default=False)
    pattern_probability = Column(Float)
    dominant_colors_json = Column(Text)
    tag_front_url = Column(String(255))   # NEW
    tag_back_url = Column(String(255))


    def __repr__(self):
        return f"<ClothingItem(id={self.item_id}, color={self.color}, category={self.category})>"
    

class Closet(Base):
    __tablename__ = "closet"

    closet_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship with clothing items
    clothing_items = relationship("ClothingItem", backref="closet", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Closet(id={self.closet_id}, name='{self.name}')>"