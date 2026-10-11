from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone
from app.database import Base
from pgvector.sqlalchemy import Vector

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    role = Column(String(50), nullable=False) # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("Session", back_populates="messages")

class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(255), nullable=False, index=True) # E.g., the markdown filename or episode ID
    guest = Column(String(255), nullable=True)
    episode_title = Column(String(255), nullable=True)
    source_url = Column(String(1024), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps (if available in the transcript, though we might not have them)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    # We will use Nomic embed text default dimension of 768. 
    # If a different model is used, we must update this or handle it dynamically.
    embedding = Column(Vector(768))

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    artifact_type = Column(String(50), nullable=False) # 'markdown' or 'html'
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("Session", back_populates="artifacts")
