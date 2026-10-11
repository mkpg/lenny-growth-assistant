from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid

class ChatRequest(BaseModel):
    session_id: Optional[uuid.UUID] = Field(default=None, description="The ID of the session. If not provided, a new session is created.")
    question: str = Field(..., description="The user's question.")
    provider: str = Field(default="ollama", description="The LLM provider to use (e.g., 'ollama', 'google').")
    model: str = Field(default="qwen2.5:3b", description="The specific model to use.")

class Citation(BaseModel):
    source_id: str
    episode_title: Optional[str]
    source_url: Optional[str]
    distance: float

class ChatResponse(BaseModel):
    session_id: uuid.UUID
    response_type: str = Field(
        default="grounded_answer", 
        description="Type of response: conversational, grounded_answer, insufficient_evidence, artifact, error"
    )
    answer: str
    artifact: Optional[str] = None
    citations: List[Citation]
