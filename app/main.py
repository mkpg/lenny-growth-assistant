from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import logging
import os
import re
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.config import settings
from dotenv import load_dotenv

# Load environment variables into os.environ for Pi agent subprocess
load_dotenv()

# Attempt to import DB components
try:
    from app.database import get_db, engine
    db_configured = True if engine else False
except Exception:
    db_configured = False
    
# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title="Lenny Growth Assistant")

# Mount static files for the frontend
import os
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
def health_check():
    """Liveness endpoint."""
    return {"status": "ok", "env": settings.app_env}

@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness endpoint verifying database dependency."""
    try:
        # Check DB connection
        db.execute(text("SELECT 1"))
        
        # Check pgvector extension
        vector_res = db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
        pgvector_status = "installed" if vector_res else "not_installed"
        
        return {
            "status": "ready",
            "database": "connected",
            "pgvector": pgvector_status
        }
    except RuntimeError as re:
        logger.error(f"Readiness check failed: {re}")
        raise HTTPException(status_code=503, detail="Database credentials missing or invalid")
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Database dependency check failed")

from app.schemas import ChatRequest, ChatResponse
from app import crud
from app.retrieval import retrieve_context, RetrievalError
from app.agent import call_pi_agent, PiAgentError

@app.post("/api/v1/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Session Management
    if request.session_id:
        db_session = crud.get_session(db, request.session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        db_session = crud.create_session(db)

    # 2. Retrieve history
    db_messages = crud.get_session_messages(db, db_session.id)
    history = [{"role": msg.role, "content": msg.content} for msg in db_messages]

    # 3. Retrieve Context via RAG
    is_conversational = False
    lower_q = request.question.strip().lower()
    
    # Improved greeting and capability detection
    greeting_words = {"hi", "hello", "hey", "greetings", "howdy", "sup", "yo"}
    capability_patterns = [
        r"what can you (do|help)",
        r"who are you",
        r"explain what you can (do|help)",
        r"how can you (help|assist)",
        r"what are your capabilities",
        r"how can you help me"
    ]
    
    is_greeting = lower_q in greeting_words or (0 < len(lower_q) < 15 and lower_q.split()[0] in greeting_words)
    is_capability = any(re.search(p, lower_q) for p in capability_patterns)
    
    if is_greeting or is_capability:
        is_conversational = True
        formatted_context = "The user is greeting you or asking about your capabilities. Briefly explain that you are The Lenny Growth Assistant, a tool that answers questions about growth, product, and leadership using insights from Lenny's Podcast transcripts. No podcast context is needed for this response."
        citations = []
    else:
        try:
            formatted_context, citations = retrieve_context(request.question, db)
        except RetrievalError as e:
            logger.error(f"Retrieval failed: {e}")
            raise HTTPException(status_code=503, detail=f"Retrieval service unavailable: {e}")
            
    artifact_keywords = {"html", "landing page", "document", "artifact", "website", "web page"}
    is_artifact_request = any(k in lower_q for k in artifact_keywords)

    # 4. Validate Provider/Model and Check Credentials
    supported_models = {
        "ollama": ["qwen2.5:3b", "qwen3:4b"],
        "google": [
            "gemini-3.8-flash"
        ]
    }
    
    if request.provider not in supported_models:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")
        
    if request.model not in supported_models[request.provider]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported model '{request.model}' for provider '{request.provider}'"
        )

    # Explicit credential check for Gemini
    if request.provider == "google":
        if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
            raise HTTPException(
                status_code=503, 
                detail="Gemini API key is missing. Please set GEMINI_API_KEY or GOOGLE_API_KEY in your .env file or environment."
            )

    try:
        assistant_reply, artifact_html, parsed_response = call_pi_agent(
            prompt=request.question,
            context=formatted_context,
            history=history,
            provider=request.provider,
            model=request.model,
            is_artifact_request=is_artifact_request
        )
    except PiAgentError as e:
        logger.error(f"Agent inference failed: {e}")
        error_str = str(e).lower()
        if "api key" in error_str or "unauthorized" in error_str or "401" in error_str:
            sanitized_detail = "Provider authentication failed. The server's API credentials may be missing or invalid."
            status_code = 500
        elif ("not found" in error_str or "404" in error_str or "no longer available" in error_str) and "using custom model id" not in error_str:
            sanitized_detail = f"The selected model '{request.model}' is currently unavailable from the provider."
            status_code = 502
        elif "timeout" in error_str:
            sanitized_detail = "The AI provider took too long to respond. Please try again."
            status_code = 504
        else:
            sanitized_detail = "An error occurred while communicating with the AI provider."
            status_code = 502
            
        raise HTTPException(status_code=status_code, detail=sanitized_detail)
    except Exception as e:
        logger.error(f"Unexpected error during agent inference: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during agent inference")
        
    # 5. Determine intent and filter citations (Application-level Evidence Gate)
    response_type = "grounded_answer"
    
    if is_conversational:
        response_type = "conversational"
        citations = []
    elif is_artifact_request:
        if artifact_html:
            response_type = "artifact"
        else:
            response_type = "error"
    else:
        # Check structured JSON response
        evidence_state = parsed_response.get("evidence_state", "insufficient")
        model_answer = parsed_response.get("answer", assistant_reply)
        model_citations = parsed_response.get("citations", [])
        
        # Override the raw assistant reply with the cleanly parsed answer, if available
        if model_answer:
            assistant_reply = model_answer
            
        if evidence_state == "insufficient":
            response_type = "insufficient_evidence"
            citations = []
        else:
            # Evidence gate: Validate quotes against retrieved context
            valid_citations = []
            
            # Map retrieved citations by source_id for fast lookup
            retrieved_map = {cit["source_id"]: cit for cit in citations}
            
            for m_cit in model_citations:
                source_id = m_cit.get("source_id")
                quote = m_cit.get("quote", "")
                
                if source_id in retrieved_map:
                    # Very basic exact substring validation
                    # Note: We can normalize whitespace/case for robustness if needed, but strict is safer.
                    retrieved_content = retrieved_map[source_id]["content"]
                    
                    if quote and quote in retrieved_content:
                        # Only add each unique source ID once
                        if not any(v["source_id"] == source_id for v in valid_citations):
                            valid_citations.append(retrieved_map[source_id])
                            
            citations = valid_citations
            
            if not citations:
                # Agent claimed 'sufficient' or 'partial', but provided zero verifiable quotes/source_ids
                response_type = "insufficient_evidence"
                assistant_reply = "I cannot confidently answer this question using the retrieved transcripts because the evidence could not be verified."
            elif evidence_state == "partial":
                response_type = "partial_answer"
                # If frontend doesn't understand "partial_answer", we can fallback to "grounded_answer", 
                # but "grounded_answer" is technically true for the parts that are answered.
                response_type = "grounded_answer"

    # 6. Persist to Database — atomic: both messages in one transaction
    try:
        crud.save_message_pair(db, db_session.id, request.question, assistant_reply)
    except Exception as e:
        logger.error(f"Failed to persist messages: {e}")
        # Rollback the broken transaction so this session doesn't stay poisoned
        try:
            db.rollback()
        except Exception:
            pass
        # Still return the answer to the user — persistence failure is non-fatal
        return ChatResponse(
            session_id=db_session.id,
            response_type=response_type,
            answer=assistant_reply,
            artifact=artifact_html,
            citations=citations
        )

    # 7. Return response
    return ChatResponse(
        session_id=db_session.id,
        response_type=response_type,
        answer=assistant_reply,
        artifact=artifact_html,
        citations=citations
    )
