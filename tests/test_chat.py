"""
Automated tests for the Phase 5 chat workflow.
Uses mocks for Pi agent and retrieval to test the endpoint logic in isolation.
"""
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_CITATIONS = [
    {
        "source_id": "ep-001.md",
        "episode_title": "Growth Strategies with Alice",
        "source_url": "https://example.com/ep1",
        "distance": 0.15,
        "content": "Alice says growth is about retention.",
    }
]
MOCK_CONTEXT = "Source: Growth Strategies with Alice (URL: https://example.com/ep1)\nExcerpt: Alice says growth is about retention.\n"
MOCK_AGENT_REPLY = "According to the transcript, Alice emphasizes that growth is fundamentally about retention."


def _patch_retrieval_and_agent():
    """Returns context managers that mock retrieval and agent."""
    retrieval_patch = patch(
        "app.main.retrieve_context",
        return_value=(MOCK_CONTEXT, MOCK_CITATIONS),
    )
    agent_patch = patch(
        "app.main.call_pi_agent",
        return_value=(MOCK_AGENT_REPLY, None, {
            "evidence_state": "sufficient",
            "answer": MOCK_AGENT_REPLY,
            "citations": [{"source_id": "ep-001.md", "quote": "Alice says growth is about retention"}]
        }),
    )
    return retrieval_patch, agent_patch


def _patch_db():
    """Mock the database dependency."""
    mock_db = MagicMock()
    # Mock session creation
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    return mock_db, mock_session


# ---------------------------------------------------------------------------
# 1. Request Validation
# ---------------------------------------------------------------------------

class TestRequestValidation:
    def test_missing_question_returns_422(self):
        """question is required in the schema."""
        res = client.post("/api/v1/chat", json={"provider": "ollama"})
        assert res.status_code == 422

    def test_empty_question_accepted(self):
        """An empty string is technically valid for the field but the model should handle it."""
        # This just tests Pydantic doesn't reject ""
        with patch("app.main.retrieve_context", return_value=("", [])), \
             patch("app.main.call_pi_agent", return_value=("I have no question to answer.", None, {"evidence_state": "insufficient", "answer": "I have no question to answer.", "citations": []})), \
             patch("app.main.crud") as mock_crud:
            mock_session = MagicMock()
            mock_session.id = uuid.uuid4()
            mock_crud.create_session.return_value = mock_session
            mock_crud.get_session_messages.return_value = []
            res = client.post("/api/v1/chat", json={"question": ""})
            assert res.status_code == 200


# ---------------------------------------------------------------------------
# 2. Session Integrity
# ---------------------------------------------------------------------------

class TestSessionIntegrity:
    def test_invalid_session_id_returns_404(self):
        """An explicitly supplied session ID that doesn't exist must return 404."""
        fake_id = str(uuid.uuid4())
        with patch("app.main.crud") as mock_crud:
            mock_crud.get_session.return_value = None
            res = client.post("/api/v1/chat", json={
                "session_id": fake_id,
                "question": "test"
            })
            assert res.status_code == 404
            assert "Session not found" in res.json()["detail"]

    def test_new_session_created_when_no_id(self):
        """When session_id is omitted, a new session is created."""
        new_session = MagicMock()
        new_session.id = uuid.uuid4()
        with patch("app.main.crud") as mock_crud, \
             patch("app.main.retrieve_context", return_value=("", [])), \
             patch("app.main.call_pi_agent", return_value=("No context available.", None, {"evidence_state": "insufficient", "answer": "No context available.", "citations": []})):
            mock_crud.create_session.return_value = new_session
            mock_crud.get_session_messages.return_value = []
            res = client.post("/api/v1/chat", json={"question": "hello"})
            assert res.status_code == 200
            assert res.json()["session_id"] == str(new_session.id)
            mock_crud.create_session.assert_called_once()


# ---------------------------------------------------------------------------
# 3. Agent Error Handling
# ---------------------------------------------------------------------------

class TestAgentErrors:
    def test_agent_failure_returns_502(self):
        """If the Pi agent raises PiAgentError, the endpoint returns 502."""
        from app.agent import PiAgentError
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        with patch("app.main.crud") as mock_crud, \
             patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
             patch("app.main.call_pi_agent", side_effect=PiAgentError("Pi process crashed")):
            mock_crud.create_session.return_value = mock_session
            mock_crud.get_session_messages.return_value = []
            res = client.post("/api/v1/chat", json={"question": "test"})
            assert res.status_code == 502
            assert "Agent error" in res.json()["detail"]

    def test_agent_failure_does_not_persist_messages(self):
        """On agent failure, no messages should be written to the database."""
        from app.agent import PiAgentError
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        with patch("app.main.crud") as mock_crud, \
             patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
             patch("app.main.call_pi_agent", side_effect=PiAgentError("crash")):
            mock_crud.create_session.return_value = mock_session
            mock_crud.get_session_messages.return_value = []
            res = client.post("/api/v1/chat", json={"question": "test"})
            assert res.status_code == 502
            mock_crud.save_message_pair.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Retrieval Error Handling
# ---------------------------------------------------------------------------

class TestRetrievalErrors:
    def test_retrieval_failure_returns_503(self):
        """If the retrieval infrastructure fails, the endpoint returns 503."""
        from app.retrieval import RetrievalError
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        with patch("app.main.crud") as mock_crud, \
             patch("app.main.retrieve_context", side_effect=RetrievalError("Ollama down")):
            mock_crud.create_session.return_value = mock_session
            mock_crud.get_session_messages.return_value = []
            res = client.post("/api/v1/chat", json={"question": "test"})
            assert res.status_code == 503
            assert "Retrieval service unavailable" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 5. Happy Path and Evidence Gate
# ---------------------------------------------------------------------------

class TestEvidenceGate:
    def test_successful_chat_returns_200_with_citations(self):
        """Full successful flow returns answer, citations, and session_id."""
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        with patch("app.main.crud") as mock_crud, \
             patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
             patch("app.main.call_pi_agent", return_value=(MOCK_AGENT_REPLY, None, {
                 "evidence_state": "sufficient",
                 "answer": MOCK_AGENT_REPLY,
                 "citations": [{"source_id": "ep-001.md", "quote": "Alice says growth is about retention"}]
             })):
            mock_crud.create_session.return_value = mock_session
            mock_crud.get_session_messages.return_value = []
            res = client.post("/api/v1/chat", json={"question": "What is growth?"})
            assert res.status_code == 200
            data = res.json()
            assert data["session_id"] == str(mock_session.id)
            assert data["answer"] == MOCK_AGENT_REPLY
            assert len(data["citations"]) == 1
            assert data["citations"][0]["episode_title"] == "Growth Strategies with Alice"
            assert data["response_type"] == "grounded_answer"
            mock_crud.save_message_pair.assert_called_once()
            
    def test_insufficient_evidence_state(self):
        """When agent returns insufficient evidence_state, citations are stripped and response_type is set."""
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        with patch("app.main.crud") as mock_crud, \
             patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
             patch("app.main.call_pi_agent", return_value=("No info.", None, {
                 "evidence_state": "insufficient",
                 "answer": "No info.",
                 "citations": [{"source_id": "ep-001.md", "quote": "fake"}] # model misbehaves and returns citation anyway
             })):
            mock_crud.create_session.return_value = mock_session
            mock_crud.get_session_messages.return_value = []
            res = client.post("/api/v1/chat", json={"question": "What is growth?"})
            assert res.status_code == 200
            data = res.json()
            assert data["response_type"] == "insufficient_evidence"
            assert len(data["citations"]) == 0

    def test_fabricated_quote_filtered(self):
        """When agent provides a quote not in the text, it is filtered out and triggers insufficient_evidence."""
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        with patch("app.main.crud") as mock_crud, \
             patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
             patch("app.main.call_pi_agent", return_value=("Alice said hello.", None, {
                 "evidence_state": "sufficient",
                 "answer": "Alice said hello.",
                 "citations": [{"source_id": "ep-001.md", "quote": "Alice said hello"}] # quote not in MOCK_CONTEXT
             })):
            mock_crud.create_session.return_value = mock_session
            mock_crud.get_session_messages.return_value = []
            res = client.post("/api/v1/chat", json={"question": "What did Alice say?"})
            assert res.status_code == 200
            data = res.json()
            assert data["response_type"] == "insufficient_evidence"
            assert "evidence could not be verified" in data["answer"]
            assert len(data["citations"]) == 0

    def test_partial_evidence_state(self):
        """When agent returns partial evidence_state with valid quotes, it's accepted."""
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        with patch("app.main.crud") as mock_crud, \
             patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
             patch("app.main.call_pi_agent", return_value=("Alice says growth is about retention, but I don't know about sales.", None, {
                 "evidence_state": "partial",
                 "answer": "Alice says growth is about retention, but I don't know about sales.",
                 "citations": [{"source_id": "ep-001.md", "quote": "Alice says growth is about retention"}]
             })):
            mock_crud.create_session.return_value = mock_session
            mock_crud.get_session_messages.return_value = []
            res = client.post("/api/v1/chat", json={"question": "What about growth and sales?"})
            assert res.status_code == 200
            data = res.json()
            assert data["response_type"] == "grounded_answer" # falls back to grounded_answer
            assert len(data["citations"]) == 1
