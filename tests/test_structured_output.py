"""
Tests for robust structured JSON extraction, evidence validation,
and insufficient-evidence fallbacks.
"""
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.agent import extract_json_payload

client = TestClient(app)

MOCK_CITATIONS = [
    {
        "source_id": "chunk_01",
        "episode_title": "Growth Tactics with Elena",
        "guest": "Elena",
        "source_url": "https://example.com/elena",
        "distance": 0.12,
        "content": "Focus on the activation funnel before scaling acquisition channels.",
    }
]
MOCK_CONTEXT = "Source: Growth Tactics with Elena\nExcerpt: Focus on the activation funnel before scaling acquisition channels.\n"


# ---------------------------------------------------------------------------
# Unit tests for extract_json_payload
# ---------------------------------------------------------------------------

def test_extract_json_fenced_markdown():
    text = """Here is the response:
```json
{
  "evidence_state": "sufficient",
  "answer": "Focus on activation first.",
  "citations": [{"source_id": "chunk_01", "quote": "Focus on the activation funnel"}]
}
```
"""
    result = extract_json_payload(text)
    assert result is not None
    assert result["evidence_state"] == "sufficient"
    assert len(result["citations"]) == 1


def test_extract_json_raw():
    text = '{"evidence_state": "sufficient", "answer": "Focus on activation first.", "citations": []}'
    result = extract_json_payload(text)
    assert result is not None
    assert result["evidence_state"] == "sufficient"
    assert result["answer"] == "Focus on activation first."


def test_extract_json_embedded():
    text = 'Some intro text\n{"evidence_state": "insufficient", "answer": "No evidence.", "citations": []}\nSome closing remarks'
    result = extract_json_payload(text)
    assert result is not None
    assert result["evidence_state"] == "insufficient"


def test_extract_json_malformed():
    text = '```json\n{"evidence_state": "sufficient", "answer": ... broken json\n```'
    result = extract_json_payload(text)
    assert result is None


def test_extract_json_missing_or_empty():
    assert extract_json_payload("") is None
    assert extract_json_payload("Just plain text with no json at all.") is None


# ---------------------------------------------------------------------------
# Integration tests for endpoint evidence validation gate
# ---------------------------------------------------------------------------

def test_endpoint_missing_structured_output_fallback():
    """When agent returns plain text without valid JSON and no quotes match, endpoint returns unverified."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Unstructured fabricated reply.", None, None)):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What should I do?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "unverified"
        assert len(data["citations"]) == 0
        assert data["answer"] == "Unstructured fabricated reply."


def test_endpoint_malformed_evidence_state_fallback():
    """When evidence_state is missing or invalid, safe unverified fallback is returned."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {"evidence_state": "bogus_state", "answer": "Some answer"})):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What should I do?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "unverified"
        assert len(data["citations"]) == 0
        assert data["answer"] == "Reply"


def test_endpoint_missing_citations_when_claimed_sufficient():
    """When agent claims sufficient evidence but provides no citations, fallback safely."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": "Claims without citations.",
             "citations": []
         })):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What should I do?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "insufficient_evidence"
        assert len(data["citations"]) == 0
        assert "no supporting citations were provided" in data["answer"].lower()


def test_endpoint_fabricated_unmatched_quote():
    """When agent quotes text not present in retrieved context, quote is rejected."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": "Fabricated statement.",
             "citations": [{"source_id": "chunk_01", "quote": "This sentence was never spoken in the podcast"}]
         })):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What should I do?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "insufficient_evidence"
        assert len(data["citations"]) == 0
        assert "evidence could not be verified" in data["answer"].lower()


def test_endpoint_verified_quote_success():
    """When quote matches retrieved context, grounded_answer is returned with verified citations."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": "Focus on the activation funnel first.",
             "citations": [{"source_id": "chunk_01", "quote": "Focus on the activation funnel before scaling", "speaker": "Elena"}]
         })):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What should I do?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "grounded_answer"
        assert len(data["citations"]) == 1
        assert data["citations"][0]["source_id"] == "chunk_01"


def test_endpoint_speaker_mismatch_warning():
    """When quote matches but speaker is wrong, grounded_answer is returned without trailing disclaimers in answer."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": "Focus on the activation funnel first.",
             "citations": [{"source_id": "chunk_01", "quote": "Focus on the activation funnel before scaling", "speaker": "Bob"}]
         })):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What should I do?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "grounded_answer"
        assert "[WARNING]" not in data["answer"]
        assert data["answer"] == "Focus on the activation funnel first."


def test_extract_json_missing_comma_repaired():
    """Missing comma between answer and citations is safely repaired."""
    malformed_raw = (
        '{\n'
        '  "evidence_state": "sufficient",\n'
        '  "answer": "Focus on the activation funnel first."\n'
        '  "citations": [{"source_id": "chunk_01", "quote": "Focus on the activation funnel"}]\n'
        '}'
    )
    parsed = extract_json_payload(malformed_raw)
    assert parsed is not None
    assert parsed["evidence_state"] == "sufficient"
    assert "Focus on the activation funnel first." in parsed["answer"]
    assert len(parsed["citations"]) == 1
    assert parsed["citations"][0]["source_id"] == "chunk_01"

