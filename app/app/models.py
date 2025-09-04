# =====================================
# app/models.py
# =====================================
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True)
    name = Column(String)
    business_type = Column(String)  # freelance, tpe, pme
    created_at = Column(DateTime, default=func.now())
    last_active = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_phone = Column(String, index=True)
    invoice_number = Column(String)
    client_name = Column(String)
    amount = Column(Float)
    invoice_date = Column(DateTime)
    due_date = Column(DateTime)
    status = Column(String, default="sent")  # sent, paid, overdue, cancelled
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_phone = Column(String, index=True)
    message = Column(Text)
    response = Column(Text)
    message_type = Column(String)  # text, image, document
    created_at = Column(DateTime, default=func.now())

class PendingMessage(Base):
    __tablename__ = "pending_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_phone = Column(String, index=True)
    message = Column(Text)
    media_url = Column(String)
    received_at = Column(DateTime, default=func.now())
    processed = Column(Boolean, default=False)
