# =====================================
# app/database.py
# =====================================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./facturation_coach.db")

# Fix pour Railway PostgreSQL URL
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialise la base de données"""
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Dependency pour obtenir une session DB"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_sync() -> Session:
    """Obtenir une session DB synchrone"""
    return SessionLocal()
