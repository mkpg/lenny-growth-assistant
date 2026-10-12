from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

class ChatRequest(BaseModel):
    session_id: Optional[uuid.UUID] = Field(default=None, description="The ID of the session. If not provided, a new session is created.")
    question: str = Field(..., description="The user's question.")
    provider: str = Field(default="ollama", description="The LLM provider to use (e.g., 'ollama', 'google').")
    model: str = Field(default="qwen2.5:3b", description="The specific model to use.")

class Citation(BaseModel):
    source_id: str
    episode_title: Optional[str] = None
    source_url: Optional[str] = None
    distance: Optional[float] = 0.0

class ChatResponse(BaseModel):
    session_id: uuid.UUID
    response_type: str = Field(
        default="grounded_answer", 
        description="Type of response: conversational, grounded_answer, insufficient_evidence, artifact, error"
    )
    answer: str
    artifact: Optional[str] = None
    artifact_type: Optional[str] = None
    artifact_id: Optional[uuid.UUID] = None
    artifact_title: Optional[str] = None
    citations: List[Citation]

class ArtifactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    artifact_type: str
    title: str
    created_at: datetime

class ArtifactDetail(ArtifactSummary):
    content: str

