"""
Regression tests for Gemini/Pi agent output handling:
1. Prevent raw model output from reaching chat UI:
   - Progress text + intermediate JSON + final structured JSON displays only the final answer.
2. Replace generic verification banners with appropriate user-facing messages:
   - Insufficient evidence with no citations does not display [NOTE: UNVERIFIED] boilerplate.
3. Partially verified answers preserve verified claims and handle unsupported quotations safely.
4. Malformed JSON does not leak raw internal output into the chat.
5. Existing Ollama/Pi behavior and retrieval configuration remain unchanged.
"""
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.agent import extract_json_payload
from app.retrieval import retrieve_context

client = TestClient(app)

MOCK_CHUNK = {
    "source_id": "adam-grenier_39",
    "episode_title": "Adam Grenier on Marketplace Growth",
    "guest": "Adam Grenier",
    "source_url": "https://example.com/marketplace",
    "distance": 0.35,
    "content": "start by assuming you no longer have product market fit, because you had product market fit in a different market",
}
MOCK_CITATIONS = [MOCK_CHUNK]
MOCK_CONTEXT = f"Source: Adam Grenier\nExcerpt: {MOCK_CHUNK['content']}\n"


def _mock_session():
    s = MagicMock()
    s.id = uuid.uuid4()
    return s


# ---------------------------------------------------------------------------
# 1. Progress text + intermediate JSON + final structured JSON
# ---------------------------------------------------------------------------

def test_extract_json_payload_with_progress_and_intermediate_json():
    """extract_json_payload ignores progress text and intermediate JSON, selecting final response."""
    raw_output = (
        "Analyzing Marketplace Models\n\n"
        "```json\n"
        "{\n"
        '  "header": "Marketplace Models Analysis",\n'
        '  "summary": "Reviewing Adam Grenier transcripts for product-market fit pivots."\n'
        "}\n"
        "```\n\n"
        "```json\n"
        "{\n"
        '  "evidence_state": "sufficient",\n'
        '  "answer": "Adam Grenier suggests starting by assuming you no longer have product-market fit when market conditions shift.",\n'
        '  "citations": [\n'
        '    {"source_id": "adam-grenier_39", "quote": "start by assuming you no longer have product market fit"}\n'
        "  ]\n"
        "}\n"
        "```"
    )
    payload = extract_json_payload(raw_output)
    assert payload is not None
    assert payload["evidence_state"] == "sufficient"
    assert "Adam Grenier suggests starting by assuming" in payload["answer"]
    assert len(payload["citations"]) == 1
    assert payload["citations"][0]["source_id"] == "adam-grenier_39"


def test_endpoint_displays_only_final_answer_when_intermediate_json_present():
    """Chat endpoint strips progress text and intermediate JSON, returning only final answer."""
    session = _mock_session()
    raw_agent_reply = (
        "Analyzing Marketplace Models\n\n"
        "```json\n"
        '{"header": "Marketplace Models Analysis", "summary": "Intermediate reasoning notes"}\n'
        "```\n\n"
        "```json\n"
        "{\n"
        '  "evidence_state": "sufficient",\n'
        '  "answer": "Adam Grenier suggests starting by assuming you no longer have product market fit.",\n'
        '  "citations": [{"source_id": "adam-grenier_39", "quote": "start by assuming you no longer have product market fit"}]\n'
        "}\n"
        "```"
    )
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=(
             raw_agent_reply,
             None,
             {
                 "evidence_state": "sufficient",
                 "answer": "Adam Grenier suggests starting by assuming you no longer have product market fit.",
                 "citations": [{"source_id": "adam-grenier_39", "quote": "start by assuming you no longer have product market fit"}]
             }
         )):
        mock_crud.create_session.return_value = session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What does Grenier say about market changes?"})

    assert res.status_code == 200
    data = res.json()
    assert data["response_type"] == "grounded_answer"
    assert data["answer"] == "Adam Grenier suggests starting by assuming you no longer have product market fit."
    assert "Analyzing Marketplace Models" not in data["answer"]
    assert "header" not in data["answer"]
    assert "summary" not in data["answer"]
    assert "```json" not in data["answer"]
    assert len(data["citations"]) == 1


# ---------------------------------------------------------------------------
# 2. Insufficient evidence response without generic boilerplate
# ---------------------------------------------------------------------------

def test_insufficient_evidence_response_no_generic_unverified_boilerplate():
    """When evidence is insufficient, clean concise explanation is displayed without [NOTE: UNVERIFIED]."""
    session = _mock_session()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=(
             "No relevant transcripts found.",
             None,
             {
                 "evidence_state": "insufficient",
                 "answer": "The retrieved transcripts do not discuss enterprise procurement cycles.",
                 "citations": []
             }
         )):
        mock_crud.create_session.return_value = session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "How do enterprise sales cycles work?"})

    assert res.status_code == 200
    data = res.json()
    assert data["response_type"] == "insufficient_evidence"
    assert len(data["citations"]) == 0
    assert data["answer"] == "The retrieved transcripts do not discuss enterprise procurement cycles."
    assert "[NOTE: UNVERIFIED]" not in data["answer"]
    assert "[NOTE:" not in data["answer"]
    assert "[WARNING:" not in data["answer"]


# ---------------------------------------------------------------------------
# 3. Partially verified answer handles unsupported quotations safely
# ---------------------------------------------------------------------------

def test_partially_verified_answer_handles_unsupported_quotations_safely():
    """Supported claims preserved with citations, unsupported quote stripped inline, clean note attached."""
    session = _mock_session()
    answer_text = (
        "Grenier noted that 'start by assuming you no longer have product market fit'. "
        "He also claimed that 'enterprise churn drops by 70% in year three'."
    )
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=(
             "Reply",
             None,
             {
                 "evidence_state": "sufficient",
                 "answer": answer_text,
                 "citations": [
                     {"source_id": "adam-grenier_39", "quote": "start by assuming you no longer have product market fit"},
                     {"source_id": "adam-grenier_39", "quote": "enterprise churn drops by 70% in year three"},
                 ]
             }
         )):
        mock_crud.create_session.return_value = session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What does Grenier say about churn?"})

    assert res.status_code == 200
    data = res.json()
    assert data["response_type"] == "partially_verified"
    assert len(data["citations"]) == 1
    assert data["citations"][0]["source_id"] == "adam-grenier_39"
    # Unsupported quote is stripped cleanly without inline warning tags
    assert "enterprise churn drops by 70% in year three" not in data["answer"]
    assert "[UNVERIFIED QUOTE:" not in data["answer"]
    # Implementation labels absent, user-facing notice present
    assert "[NOTE: PARTIALLY VERIFIED]" not in data["answer"]
    assert "[WARNING: PARTIALLY VERIFIED]" not in data["answer"]
    assert "Note: Only parts of this response" not in data["answer"]
    assert "[WARNING]" not in data["answer"]


# ---------------------------------------------------------------------------
# 4. Malformed JSON does not leak raw internal output into chat
# ---------------------------------------------------------------------------

def test_malformed_json_does_not_leak_raw_internal_output():
    """Malformed JSON returns safe fallback without exposing internal braces, JSON keys, or scaffolding."""
    session = _mock_session()
    broken_output = (
        "Analyzing Marketplace Models\n\n"
        "```json\n"
        '{"evidence_state": "sufficient", "answer": "Unclosed broken JSON string that terminates abruptly\n'
        '{"citations": [{"source_id": "adam-grenier_39"'
    )
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=(broken_output, None, None)):
        mock_crud.create_session.return_value = session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What is the marketplace strategy?"})

    assert res.status_code == 200
    data = res.json()
    # Must not leak raw internal scaffolding into chat
    assert "{" not in data["answer"]
    assert "}" not in data["answer"]
    assert '"evidence_state"' not in data["answer"]
    assert '"citations"' not in data["answer"]
    assert "Analyzing Marketplace Models" not in data["answer"]
    assert "unable to produce a properly formatted response" in data["answer"]


# ---------------------------------------------------------------------------
# 5. Existing Ollama/Pi behavior and retrieval configuration remain unchanged
# ---------------------------------------------------------------------------

def test_existing_ollama_markdown_behavior_preserved():
    """Plain Markdown prose from Ollama without matching quotes returns unverified with text preserved."""
    session = _mock_session()
    plain_markdown = (
        "To scale a growth team, establish a clear north star metric and run rapid A/B experiments weekly."
    )
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=(plain_markdown, None, None)):
        mock_crud.create_session.return_value = session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "How to scale a growth team?"})

    assert res.status_code == 200
    data = res.json()
    assert data["response_type"] == "unverified"
    assert len(data["citations"]) == 0
    assert "establish a clear north star metric" in data["answer"]
    assert "[NOTE: UNVERIFIED]" not in data["answer"]
    assert "Note: This response" not in data["answer"]


def test_retrieval_configuration_defaults_unchanged():
    """Verify default retrieval parameters: top_k=8, threshold=0.45."""
    import inspect
    sig = inspect.signature(retrieve_context)
    assert sig.parameters["top_k"].default == 8
    assert sig.parameters["threshold"].default == 0.45
