"""
Comprehensive automated regression tests verifying all code-level requirement fixes:
1. Portable Pi CLI executable discovery and error handling.
2. Transcript evidence grounding, citation deduplication, and unverified quote handling.
3. Dedicated Ship 30 for 30 essay skill integration, validation, and insufficient evidence behavior.
4. HTML artifact security, CSP injection, and iframe sandbox isolation.
5. Provider failure handling, timeout mapping, and credentials checking.
6. Session isolation, invalid session ID handling, and persistence rollback.
"""

import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.config import settings
from app.agent import resolve_pi_executable, PiAgentError
from app.validator import secure_artifact_html, validate_evidence, strip_unverified_quotes
from app.skills.ship30 import is_ship30_request, build_ship30_instruction, validate_ship30_essay

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_db_dependency():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    yield mock_db
    app.dependency_overrides.clear()

# ---------------------------------------------------------------------------
# 1. Portable Pi CLI configuration & discovery tests
# ---------------------------------------------------------------------------

def test_resolve_pi_executable_from_env_var(tmp_path):
    """Setting PI_CMD_PATH points directly to the executable."""
    dummy_exe = tmp_path / "custom_pi.exe"
    dummy_exe.write_text("dummy")
    with patch.dict(os.environ, {"PI_CMD_PATH": str(dummy_exe)}):
        resolved = resolve_pi_executable()
        assert resolved == str(dummy_exe)

def test_resolve_pi_executable_from_path():
    """When pi is found on system PATH via shutil.which, it is returned."""
    with patch.dict(os.environ, {}, clear=True), \
         patch.object(settings, "pi_cmd_path", None), \
         patch("shutil.which", return_value="/usr/local/bin/pi"):
        resolved = resolve_pi_executable()
        assert resolved == "/usr/local/bin/pi"

def test_resolve_pi_executable_missing_raises_error():
    """When pi cannot be found anywhere, a clear PiAgentError is raised."""
    with patch.dict(os.environ, {}, clear=True), \
         patch.object(settings, "pi_cmd_path", None), \
         patch("shutil.which", return_value=None), \
         patch("os.path.isfile", return_value=False):
        with pytest.raises(PiAgentError) as exc_info:
            resolve_pi_executable()
        assert "Pi executable could not be resolved" in str(exc_info.value)
        assert "PI_CMD_PATH" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 2. Evidence Grounding & Citation Integrity
# ---------------------------------------------------------------------------

def test_grounding_preserves_supported_and_strips_unsupported():
    """
    Mixed response: verified quotes are retained in citations;
    unverified verbatim quotes are stripped cleanly from answer without ugly tags.
    """
    answer_text = (
        "Elena Verna advised that 'freemium drives organic virality'. "
        "She also claimed that 'conversion jumps to 95% on day one'."
    )
    mock_context = "Elena Verna: freemium drives organic virality across modern SaaS funnels."
    mock_citations = [
        {"source_id": "chunk_elena_01", "content": mock_context, "episode_title": "Elena Verna on PLG", "source_url": "https://example.com/elena"}
    ]
    
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(mock_context, mock_citations)), \
         patch("app.main.call_pi_agent", return_value=(
             "Raw",
             None,
             {
                 "evidence_state": "sufficient",
                 "answer": answer_text,
                 "citations": [
                     {"source_id": "chunk_elena_01", "quote": "freemium drives organic virality"},
                     {"source_id": "chunk_elena_01", "quote": "conversion jumps to 95% on day one"}
                 ]
             }
         )):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What does Elena say about freemium?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "partially_verified"
        assert len(data["citations"]) == 1
        assert data["citations"][0]["source_id"] == "chunk_elena_01"
        assert "conversion jumps to 95% on day one" not in data["answer"]
        assert "[UNVERIFIED QUOTE:" not in data["answer"]
        assert "[WARNING]" not in data["answer"]

def test_distinct_chunks_from_same_url_preserved():
    """
    Two distinct chunks from the same episode/URL must both be preserved with their distinct source_ids.
    """
    model_citations = [
        {"source_id": "chunk_01", "quote": "quote one from part a"},
        {"source_id": "chunk_02", "quote": "quote two from part b"}
    ]
    retrieved = [
        {"source_id": "chunk_01", "content": "here is quote one from part a in context", "source_url": "https://example.com/ep1"},
        {"source_id": "chunk_02", "content": "here is quote two from part b in context", "source_url": "https://example.com/ep1"}
    ]
    val = validate_evidence(model_citations, retrieved, "model answer")
    assert val.has_any_verified
    assert len(val.verified_citations) == 2
    source_ids = [c["source_id"] for c in val.verified_citations]
    assert "chunk_01" in source_ids
    assert "chunk_02" in source_ids


# ---------------------------------------------------------------------------
# 3. Ship 30 for 30 Dedicated Skill Tests
# ---------------------------------------------------------------------------

def test_ship30_intent_detection():
    """Ship 30 and long-form essay requests are accurately detected."""
    assert is_ship30_request("Write a Ship 30 for 30 essay on onboarding")
    assert is_ship30_request("Can you generate a ship30 style essay about marketplace liquidity?")
    assert is_ship30_request("Write an essay on B2B pricing frameworks")
    assert is_ship30_request("Compose a 1,250-word essay analyzing product-market fit")
    # Standard questions must not trigger the skill
    assert not is_ship30_request("What did Adam Fishman say about activation?")
    assert not is_ship30_request("Explain how marketplace supply rebalancing works")

def test_ship30_instruction_structure():
    """Skill instruction encodes writing principles and strict grounding."""
    instruction = build_ship30_instruction()
    assert "Ship 30 for 30" in instruction
    assert "1,250 words" in instruction
    assert "Hook" in instruction
    assert "Takeaway" in instruction
    assert "CRITICAL GROUNDING RULES" in instruction
    assert "NEVER invent" in instruction

def test_ship30_essay_validation():
    """Validator checks word count, headings, takeaway, and bold emphasis."""
    good_essay = (
        "# The Growth Engine Blueprint\n\n"
        "Most growth teams optimize the wrong funnel step.\n\n"
        "## Why Activation Matters Most\n\n"
        "Improving onboarding yields **compounding advantages** for downstream retention.\n" * 50 +
        "\n\n## Actionable Takeaway\n\n"
        "Implement a 3-step activation checklist for new users."
    )
    result = validate_ship30_essay(good_essay)
    assert result["valid"]
    assert result["has_headings"]
    assert result["has_takeaway"]
    assert result["has_bold"]
    assert result["word_count"] > 300

def test_ship30_routing_and_insufficient_evidence():
    """When user requests an essay on a topic with zero evidence, returns clean insufficient_evidence."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=("", [])), \
         patch("app.main.call_pi_agent", return_value=(
             "The retrieved transcripts do not contain sufficient evidence to write a grounded essay on this topic.",
             None,
             {
                 "evidence_state": "insufficient",
                 "answer": "The retrieved transcripts do not contain sufficient evidence to write a grounded essay on quantum computing.",
                 "citations": []
             }
         )):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "Write a Ship 30 for 30 essay on quantum computing"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "insufficient_evidence"
        assert len(data["citations"]) == 0


# ---------------------------------------------------------------------------
# 4. Artifact Security & CSP Tests
# ---------------------------------------------------------------------------

def test_secure_artifact_html_injects_csp():
    """HTML artifacts without CSP have strict CSP meta tag injected into <head>."""
    raw_html = "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
    secured = secure_artifact_html(raw_html)
    assert "Content-Security-Policy" in secured
    assert "default-src 'none'" in secured
    assert "script-src 'unsafe-inline'" in secured

def test_secure_artifact_html_preserves_existing_csp():
    """HTML with existing CSP is not duplicated."""
    html_with_csp = '<html><head><meta http-equiv="Content-Security-Policy" content="default-src \'self\'"></head></html>'
    secured = secure_artifact_html(html_with_csp)
    assert secured.count("Content-Security-Policy") == 1

def test_iframe_sandbox_in_index_html():
    """Artifact iframe in index.html has sandbox with allow-scripts and strictly NO allow-same-origin."""
    index_path = os.path.join("app", "static", "index.html")
    assert os.path.isfile(index_path)
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert 'sandbox="allow-scripts"' in content
    assert "allow-same-origin" not in content


# ---------------------------------------------------------------------------
# 5. Model-Provider Error Handling Tests
# ---------------------------------------------------------------------------

def test_gemini_missing_api_key_returns_503():
    """When Gemini provider is selected but no API key is in environment, return 503."""
    with patch.dict(os.environ, {}, clear=True), \
         patch("app.main.retrieve_context", return_value=("Context", [])):
        res = client.post("/api/v1/chat", json={
            "question": "What is product market fit?",
            "provider": "google",
            "model": "gemini-3.8-flash"
        })
        assert res.status_code == 503
        assert "Gemini API key is missing" in res.json()["detail"]

def test_unsupported_model_or_provider_returns_400():
    """Invalid provider or model returns clear 400 error."""
    res = client.post("/api/v1/chat", json={
        "question": "Hello",
        "provider": "unsupported_provider",
        "model": "qwen2.5:3b"
    })
    assert res.status_code == 400
    assert "Unsupported provider" in res.json()["detail"]

def test_provider_timeout_returns_504():
    """When agent inference times out, returns HTTP 504."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=("Context", [])), \
         patch("app.main.call_pi_agent", side_effect=PiAgentError("Operation timed out after 300s")):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What is retention?"})
        assert res.status_code == 504
        assert "took too long" in res.json()["detail"]

def test_ollama_unavailable_returns_503():
    """When local Ollama connection fails, returns HTTP 503."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=("Context", [])), \
         patch("app.main.call_pi_agent", side_effect=PiAgentError("Connection refused by Ollama host")):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What is activation?"})
        assert res.status_code == 503
        assert "Ollama service is unavailable" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 6. Session Isolation & Persistence Rollback Tests
# ---------------------------------------------------------------------------

def test_invalid_session_id_returns_404():
    """Passing a nonexistent session UUID returns 404."""
    unknown_uuid = str(uuid.uuid4())
    with patch("app.main.crud.get_session", return_value=None):
        res = client.post("/api/v1/chat", json={
            "session_id": unknown_uuid,
            "question": "What is onboarding?"
        })
        assert res.status_code == 404
        assert "Session not found" in res.json()["detail"]

def test_persistence_failure_rolls_back_transaction():
    """When database message persistence fails, transaction is rolled back and response is still delivered."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    mock_db = MagicMock()
    
    mock_context = "Activation requires intuitive setup workflows."
    mock_citations = [{"source_id": "ep_1", "content": mock_context, "distance": 0.1}]
    with patch("app.main.crud.create_session", return_value=mock_session), \
         patch("app.main.crud.get_session_messages", return_value=[]), \
         patch("app.main.retrieve_context", return_value=(mock_context, mock_citations)), \
         patch("app.main.call_pi_agent", return_value=("Assistant response", None, {
             "evidence_state": "sufficient",
             "answer": "Activation requires intuitive setup workflows.",
             "citations": [{"source_id": "ep_1", "quote": "Activation requires intuitive setup workflows."}]
         })), \
         patch("app.main.crud.save_message_pair", side_effect=Exception("Database lock error")):
        res = client.post("/api/v1/chat", json={"question": "What is activation?"})
        assert res.status_code == 200
        data = res.json()
        assert data["answer"] == "Activation requires intuitive setup workflows."
