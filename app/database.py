from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from fastapi import HTTPException

Base = declarative_base()

engine = None
SessionLocal = None

if settings.database_url:
    # Use the connection string
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not configured. DATABASE_URL is missing.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
