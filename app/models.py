#This object represents and emergency contact record in the database
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Sequence
from app.db import Base

class EmergencyContact(Base):
    __tablename__ = "emergencycontact"

    contact_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String(100))
    phone = Column(String(20))
    relationship = Column(String(50))
    address = Column(String(255))
    image_url = Column(String(255))

class User(Base):
    __tablename__ = "users"
    user_id = Column(
        Integer,
        Sequence("users_user_id_seq"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    hashed_password = Column(String(255), nullable=False)
