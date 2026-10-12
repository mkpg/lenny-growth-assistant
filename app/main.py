from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import logging
import os
import re
import uuid
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

from app.schemas import ChatRequest, ChatResponse, ArtifactSummary, ArtifactDetail
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
    history_meta_patterns = [
        r"based on (your|the) (previous|earlier|last) answer",
        r"what (did you|target did you|did we) (recommend|say|mention)",
        r"in (your|the) (previous|earlier|last) (answer|message|response)",
        r"what was (your|the) (previous|earlier|last) (answer|response)",
        r"referring to (your|the) (previous|earlier) answer"
    ]
    
    is_greeting = lower_q in greeting_words or (0 < len(lower_q) < 15 and lower_q.split()[0] in greeting_words)
    is_capability = any(re.search(p, lower_q) for p in capability_patterns)
    is_history_query = any(re.search(p, lower_q) for p in history_meta_patterns)
    
    if is_greeting or is_capability:
        is_conversational = True
        formatted_context = "The user is greeting you or asking about your capabilities. Briefly explain that you are The Lenny Growth Assistant, a tool that answers questions about growth, product, and leadership using insights from Lenny's Podcast transcripts. No podcast context is needed for this response."
        citations = []
    elif is_history_query:
        if not history:
            assistant_reply = "There is no previous conversation history in this session to refer to."
            crud.save_message_pair(db, db_session.id, request.question, assistant_reply)
            return ChatResponse(
                session_id=db_session.id,
                response_type="conversational",
                answer=assistant_reply,
                artifact=None,
                citations=[]
            )
        
        # Check if the query asks purely about what was previously said/recommended
        pure_history_patterns = [
            r"what (target|metric|goal|number) did you recommend",
            r"what did you (recommend|say|mention|suggest)",
            r"what was (your|the) (previous|earlier|last) (answer|recommendation)",
            r"did you recommend",
        ]
        is_pure_history = any(re.search(p, lower_q) for p in pure_history_patterns)
        
        if is_pure_history:
            is_conversational = True
            formatted_context = "The user is asking about what you previously stated or recommended in the conversation history. Answer strictly based on the CONVERSATION HISTORY provided below. If you did NOT recommend a specific target, metric, or item in the previous turns, state clearly that you did not recommend one."
            citations = []
        else:
            try:
                formatted_context, citations = retrieve_context(request.question, db)
            except RetrievalError as e:
                logger.error(f"Retrieval failed: {e}")
                raise HTTPException(status_code=503, detail=f"Retrieval service unavailable: {e}")
    else:
        try:
            formatted_context, citations = retrieve_context(request.question, db)
        except RetrievalError as e:
            logger.error(f"Retrieval failed: {e}")
            raise HTTPException(status_code=503, detail=f"Retrieval service unavailable: {e}")
            
    artifact_keywords = {"html", "landing page", "document", "artifact", "website", "web page", "checklist", "markdown"}
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

    from app.skills.ship30 import is_ship30_request, build_ship30_instruction
    is_essay_request = is_ship30_request(request.question)
    skill_instruction = build_ship30_instruction() if is_essay_request else None

    try:
        assistant_reply, artifact_content, parsed_response = call_pi_agent(
            prompt=request.question,
            context=formatted_context,
            history=history,
            provider=request.provider,
            model=request.model,
            is_artifact_request=is_artifact_request,
            skill_instruction=skill_instruction
        )
    except PiAgentError as e:
        logger.error(f"Agent inference failed: {e}")
        error_str = str(e).lower()
        if "api key" in error_str or "unauthorized" in error_str or "401" in error_str:
            sanitized_detail = "Provider authentication failed. The server's API credentials may be missing or invalid."
            status_code = 500
        elif "connection refused" in error_str or "failed to connect" in error_str or ("ollama" in error_str and ("down" in error_str or "connect" in error_str)):
            sanitized_detail = "Local Ollama service is unavailable. Please ensure Ollama is running and accessible."
            status_code = 503
        elif "pi executable could not be resolved" in error_str:
            sanitized_detail = "Pi executable could not be resolved. Please ensure Pi CLI is installed or set PI_CMD_PATH."
            status_code = 500
        elif ("not found" in error_str or "404" in error_str or "no longer available" in error_str) and "using custom model id" not in error_str:
            sanitized_detail = f"The selected model '{request.model}' is currently unavailable from the provider."
            status_code = 502
        elif "timeout" in error_str or "timed out" in error_str:
            sanitized_detail = "The AI provider took too long to respond. Please try again."
            status_code = 504
        else:
            sanitized_detail = "Agent error: An error occurred while communicating with the AI provider."
            status_code = 502
            
        raise HTTPException(status_code=status_code, detail=sanitized_detail)
    except Exception as e:
        logger.error(f"Unexpected error during agent inference: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during agent inference")

    # 5. Determine intent and filter citations (Application-level Evidence Gate)
    response_type = "grounded_answer"
    from app.validator import validate_evidence, validate_markdown_text, strip_unverified_quotes, secure_artifact_html
    
    if is_conversational:
        response_type = "conversational"
        citations = []
    elif is_artifact_request:
        if artifact_content:
            response_type = "artifact"
            if "<html" in artifact_content.lower() or "<body" in artifact_content.lower() or "<!doctype" in artifact_content.lower() or "<div" in artifact_content.lower():
                artifact_content = secure_artifact_html(artifact_content)
        else:
            response_type = "error"
    else:
        # Check structured JSON response
        if parsed_response and isinstance(parsed_response, dict):
            evidence_state = parsed_response.get("evidence_state")
            model_answer = parsed_response.get("answer")
            model_citations = parsed_response.get("citations", [])
            
            if evidence_state not in ("sufficient", "partial", "insufficient") or not model_answer or not isinstance(model_answer, str):
                # Malformed structure -> drop into markdown fallback
                parsed_response = None
            elif evidence_state == "insufficient":
                response_type = "insufficient_evidence"
                citations = []
                if model_answer and model_answer.strip():
                    assistant_reply = model_answer.strip()
                else:
                    assistant_reply = (
                        "The retrieved transcripts do not contain sufficient evidence to support this claim."
                    )
            else:
                # evidence_state in ("sufficient", "partial")
                if not isinstance(model_citations, list) or not model_citations:
                    # Model gave an answer but no citations -> validate markdown
                    val = validate_markdown_text(model_answer, citations)
                    if val.has_any_verified:
                        response_type = "partially_verified"
                        citations = val.verified_citations
                        assistant_reply = model_answer
                    else:
                        response_type = "insufficient_evidence"
                        citations = []
                        assistant_reply = (
                            "The retrieved transcripts do not support the requested claim because no supporting citations were provided."
                        )
                else:
                    validation = validate_evidence(
                        model_citations=model_citations,
                        retrieved_citations=citations,
                        model_answer=model_answer,
                    )
                    citations = validation.verified_citations
                    assistant_reply = model_answer
                    
                    if not validation.has_any_verified:
                        # 0 citations verified
                        response_type = "insufficient_evidence"
                        citations = []
                        assistant_reply = (
                            "The retrieved transcripts do not support the requested claim because the evidence could not be verified."
                        )
                    elif validation.unverified_citations:
                        # Some verified, some unverified (e.g. fabricated metric/quote).
                        # Strip the unverified verbatim quotations from the answer text
                        # so fabricated quotes are never silently presented as facts.
                        assistant_reply = strip_unverified_quotes(
                            assistant_reply, validation.unverified_citations
                        )
                        response_type = "partially_verified"
                    else:
                        # 100% of citations verified!
                        response_type = "grounded_answer"

        # Safe Markdown Fallback if parsed_response was None or malformed
        if not parsed_response or not isinstance(parsed_response, dict):
            has_json_artifacts = (
                '"evidence_state"' in assistant_reply
                or '"answer"' in assistant_reply
                or '"citations"' in assistant_reply
                or '"header"' in assistant_reply
                or '"summary"' in assistant_reply
                or '```json' in assistant_reply.lower()
                or assistant_reply.strip().startswith("{")
            )

            if has_json_artifacts:
                # Try to cleanly extract the answer text
                ans_m = re.search(r'"answer"\s*:\s*"(.*?)"(?:\s*,?\s*"(?:citations|evidence_state)"|\s*\}\s*$)', assistant_reply, re.DOTALL)
                if ans_m:
                    salvaged = ans_m.group(1).replace(r'\"', '"').replace(r'\n', '\n').replace(r'\t', '\t').replace(r'\\', '\\').strip()
                    if len(salvaged) >= 15 and not (salvaged.startswith("{") and salvaged.endswith("}")):
                        assistant_reply = salvaged
                    else:
                        assistant_reply = ""
                else:
                    assistant_reply = ""

                # If JSON was malformed and cannot be safely salvaged, return safe fallback without leaking raw JSON
                if not assistant_reply:
                    response_type = "insufficient_evidence"
                    citations = []
                    assistant_reply = (
                        "I was unable to produce a properly formatted response from the retrieved transcripts. "
                        "Please try asking your question again or rephrasing it."
                    )

            if response_type != "insufficient_evidence" or (parsed_response is None and not has_json_artifacts):
                # Check for explicit refusal or insufficient context signals
                refusal_signals = [
                    "cannot answer", "do not contain", "does not contain",
                    "no relevant", "not mentioned", "not enough information",
                    "cannot confidently answer", "no direct evidence",
                    "do not provide explicit", "not supported by the transcripts"
                ]
                lower_reply = assistant_reply.lower()
                if any(sig in lower_reply for sig in refusal_signals):
                    response_type = "insufficient_evidence"
                    citations = []
                else:
                    # Substantive markdown answer: validate quotes against retrieved citations
                    val = validate_markdown_text(assistant_reply, citations)
                    if val.has_any_verified:
                        # Strip any unverified quoted phrases from the answer before returning
                        assistant_reply = strip_unverified_quotes(
                            assistant_reply, val.unverified_citations
                        )
                        response_type = "partially_verified"
                        citations = val.verified_citations
                    else:
                        response_type = "unverified"
                        citations = []

    # 6. Persist to Database — atomic: both messages in one transaction
    # Also persist generated artifact if present
    artifact_id = None
    artifact_title = None
    artifact_type = None
    if artifact_content:
        # Determine whether artifact is HTML or Markdown
        is_html = (
            "<html" in artifact_content.lower()
            or "<body" in artifact_content.lower()
            or "<div" in artifact_content.lower()
            or "<!doctype" in artifact_content.lower()
        )
        artifact_type = "html" if is_html else "markdown"

        if artifact_type == "html":
            title_match = re.search(r'<title>(.*?)</title>', artifact_content, re.IGNORECASE)
            if not title_match:
                title_match = re.search(r'<h1>(.*?)</h1>', artifact_content, re.IGNORECASE)
            if title_match:
                raw_title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                artifact_title = raw_title if raw_title else request.question[:50]
            else:
                artifact_title = request.question[:50]
        else:
            # Markdown title extraction from # Title
            md_title_match = re.search(r'^#\s+(.+)$', artifact_content, re.MULTILINE)
            if md_title_match:
                artifact_title = md_title_match.group(1).strip()
            else:
                artifact_title = request.question[:50]

        try:
            db_art = crud.create_artifact(
                db=db,
                session_id=db_session.id,
                title=artifact_title,
                content=artifact_content,
                artifact_type=artifact_type
            )
            artifact_id = db_art.id
            artifact_title = db_art.title
        except Exception as ae:
            logger.error(f"Failed to persist artifact: {ae}")

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
            artifact=artifact_content,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            artifact_title=artifact_title,
            citations=citations
        )

    # 7. Return response
    return ChatResponse(
        session_id=db_session.id,
        response_type=response_type,
        answer=assistant_reply,
        artifact=artifact_content,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        artifact_title=artifact_title,
        citations=citations
    )


# ---------------------------------------------------------------------------
# Artifact Library Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/sessions/{session_id}/artifacts", response_model=List[ArtifactSummary])
def list_session_artifacts(session_id: uuid.UUID, db: Session = Depends(get_db)):
    """List all artifacts generated in the given session."""
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    artifacts = crud.get_session_artifacts(db, session_id)
    return artifacts


@app.get("/api/v1/artifacts/{artifact_id}", response_model=ArtifactDetail)
def get_artifact_endpoint(
    artifact_id: uuid.UUID,
    session_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db)
):
    """Retrieve an artifact by ID, optionally validating session ownership."""
    artifact = crud.get_artifact(db, artifact_id, session_id=session_id)
    if not artifact:
        if session_id:
            other = crud.get_artifact(db, artifact_id)
            if other:
                raise HTTPException(status_code=403, detail="Access denied: Artifact does not belong to this session")
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@app.get("/api/v1/artifacts/{artifact_id}/download")
def download_artifact(
    artifact_id: uuid.UUID,
    session_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db)
):
    """Download the raw saved artifact content with appropriate headers and filename."""
    artifact = crud.get_artifact(db, artifact_id, session_id=session_id)
    if not artifact:
        if session_id:
            other = crud.get_artifact(db, artifact_id)
            if other:
                raise HTTPException(status_code=403, detail="Access denied: Artifact does not belong to this session")
        raise HTTPException(status_code=404, detail="Artifact not found")

    safe_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', artifact.title).strip().replace(' ', '_').lower()
    if not safe_title:
        safe_title = "artifact"
    safe_title = safe_title[:50]

    if artifact.artifact_type == "markdown":
        ext = ".md"
        media_type = "text/markdown; charset=utf-8"
    else:
        ext = ".html"
        media_type = "text/html; charset=utf-8"

    filename = f"{safe_title}{ext}"
    return Response(
        content=artifact.content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

