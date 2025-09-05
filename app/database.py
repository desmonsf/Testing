# =====================================
# app/database.py
# =====================================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Si pas de DATABASE_URL, utiliser SQLite local
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./facturation_coach.db"
    print("Utilisation de SQLite local")
else:
    print(f"DATABASE_URL détectée: {DATABASE_URL[:50]}...")
    
    # Fix pour Railway/Render PostgreSQL URL
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        print("URL PostgreSQL corrigée")
    
    # Vérification que l'URL est valide
    if not (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("sqlite://")):
        print(f"ERREUR: URL invalide détectée: {DATABASE_URL}")
        print("Fallback vers SQLite")
        DATABASE_URL = "sqlite:///./facturation_coach.db"

# Create engine
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )
    print("Engine SQLAlchemy créé avec succès")
except Exception as e:
    print(f"Erreur création engine: {e}")
    # Fallback SQLite
    DATABASE_URL = "sqlite:///./facturation_coach.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    print("Fallback SQLite activé")

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialise la base de données"""
    try:
        Base.metadata.create_all(bind=engine)
        print("Base de données initialisée avec succès")
    except Exception as e:
        print(f"Erreur initialisation DB: {e}")
        raise

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
