import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Session as DbSession, Message, Artifact

def get_session(db: Session, session_id: uuid.UUID) -> Optional[DbSession]:
    return db.query(DbSession).filter(DbSession.id == session_id).first()

def create_session(db: Session) -> DbSession:
    db_session = DbSession()
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_session_messages(db: Session, session_id: uuid.UUID) -> List[Message]:
    return db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).all()

def save_message_pair(db: Session, session_id: uuid.UUID, user_content: str, assistant_content: str):
    """
    Persist both the user and assistant messages atomically in one transaction.
    If either insert fails, neither is committed.
    """
    user_msg = Message(session_id=session_id, role="user", content=user_content)
    assistant_msg = Message(session_id=session_id, role="assistant", content=assistant_content)
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return user_msg, assistant_msg

def create_artifact(
    db: Session,
    session_id: uuid.UUID,
    title: str,
    content: str,
    artifact_type: str = "html",
    message_id: Optional[uuid.UUID] = None
) -> Artifact:
    """
    Persist a generated artifact associated with a session.
    Avoids duplicate entries if the exact same content already exists for this session.
    """
    existing = (
        db.query(Artifact)
        .filter(Artifact.session_id == session_id, Artifact.content == content)
        .first()
    )
    if existing:
        return existing

    clean_title = (title or "Generated Artifact")[:255]
    artifact = Artifact(
        session_id=session_id,
        message_id=message_id,
        artifact_type=artifact_type,
        title=clean_title,
        content=content
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact

def get_session_artifacts(db: Session, session_id: uuid.UUID) -> List[Artifact]:
    """Retrieve all artifacts belonging to a given session, ordered by newest first."""
    return (
        db.query(Artifact)
        .filter(Artifact.session_id == session_id)
        .order_by(Artifact.created_at.desc())
        .all()
    )

def get_artifact(
    db: Session,
    artifact_id: uuid.UUID,
    session_id: Optional[uuid.UUID] = None
) -> Optional[Artifact]:
    """
    Retrieve an artifact by ID, optionally validating session ownership.
    """
    query = db.query(Artifact).filter(Artifact.id == artifact_id)
    if session_id:
        query = query.filter(Artifact.session_id == session_id)
    return query.first()
