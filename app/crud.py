import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Session as DbSession, Message

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
