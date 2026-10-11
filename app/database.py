from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from fastapi import HTTPException

Base = declarative_base()

engine = None
SessionLocal = None

if settings.database_url:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,      # Verify connection health before use
        pool_recycle=300,        # Recycle connections every 5 min to prevent pg8000 network errors
        pool_size=5,             # Keep 5 connections alive
        max_overflow=10,         # Allow up to 10 extra connections under load
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not configured. DATABASE_URL is missing.")
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Roll back any failed transaction so the session is clean for the next request
        db.rollback()
        raise
    finally:
        db.close()
