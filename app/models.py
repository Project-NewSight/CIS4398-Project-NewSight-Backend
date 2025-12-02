#This object represents and emergency contact record in the database
from sqlalchemy import Column, Integer, String, ForeignKey
from app.db import Base

class EmergencyContact(Base):
    __tablename__ = "emergencycontact"

    contact_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer,ForeignKey("users.id"), nullable=False)
    name = Column(String(100))
    phone = Column(String(20))
    relationship = Column(String(50))
    address = Column(String(255))
    image_url = Column(String(255))

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
