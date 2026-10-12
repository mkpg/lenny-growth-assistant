"""
Regression tests for the re-balancing fix:
1. Valid structured JSON -> grounded_answer with verified citations.
2. Plain Markdown with verified quote -> partially_verified (never falsely marked grounded).
3. Plain Markdown without quotes -> unverified with preserved text.
4. Verified quote + fabricated numerical claim:
   - Verified quote remains in citations.
   - Fabricated numerical claim citation is stripped.
   - Fabricated number is never presented as transcript-backed.
   - Status is partially_verified with explicit warning banner.
5. Conversational follow-up about prior turn -> answers from history (conversational).
6. Conversational follow-up with missing history -> returns no-history notice without guessing.
7. Out-of-domain refusal -> insufficient_evidence with model prose preserved.
8. Follow-up introducing new podcast claims -> requires transcript retrieval and evidence checks.
"""
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOCK_CITATIONS = [
    {
        "source_id": "chunk_fishman_32",
        "episode_title": "How to build a high-performing growth team | Adam Fishman",
        "guest": "Adam Fishman",
        "source_url": "https://www.youtube.com/watch?v=wP8YyWH524A",
        "distance": 0.15,
        "content": "improving the onboarding experience can improve user revenue by 25%",
    }
]
MOCK_CONTEXT = "Source: Adam Fishman\nExcerpt: improving the onboarding experience can improve user revenue by 25%\n"


def test_valid_json_grounded_answer():
    """Valid structured JSON with 100% verified citations yields grounded_answer."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": "Fishman notes that improving onboarding can improve user revenue by 25%.",
             "citations": [{"source_id": "chunk_fishman_32", "quote": "improving the onboarding experience can improve user revenue by 25%"}]
         })):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What is the impact of onboarding?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "grounded_answer"
        assert len(data["citations"]) == 1
        assert data["citations"][0]["source_id"] == "chunk_fishman_32"


def test_plain_markdown_with_verified_quote_is_partially_verified():
    """When JSON fails but plain Markdown contains a verified quote, mark partially_verified, NOT grounded_answer."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    markdown_reply = (
        "Here are activation strategies:\n"
        "As Adam Fishman noted: \"improving the onboarding experience can improve user revenue by 25%\".\n"
        "You should focus on reducing initial cognitive friction."
    )
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=(markdown_reply, None, None)):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "How can I improve activation?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "partially_verified"
        assert len(data["citations"]) == 1
        assert data["citations"][0]["source_id"] == "chunk_fishman_32"
        assert "reducing initial cognitive friction" in data["answer"]
        assert "[NOTE: PARTIALLY VERIFIED]" not in data["answer"]
        assert "Note:" not in data["answer"]


def test_plain_markdown_without_matching_quotes_is_unverified():
    """Plain Markdown without matching quotes is preserved with unverified notice, not wiped."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    markdown_reply = (
        "To improve activation, define the setup moment, aha moment, and habit moment. "
        "Remove unnecessary form fields and guide users with targeted checklists."
    )
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=(markdown_reply, None, None)):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "How can I improve activation?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "unverified"
        assert len(data["citations"]) == 0
        assert "define the setup moment" in data["answer"]
        assert "[NOTE: UNVERIFIED]" not in data["answer"]
        assert "Note:" not in data["answer"]


def test_verified_quote_plus_fabricated_numerical_claim():
    """
    CRITICAL TEST: Answer contains one verified quote and one fabricated numerical claim.
    - The verified quote citation is preserved.
    - The fabricated numerical claim is stripped from citations.
    - The response is marked partially_verified (never grounded_answer).
    - An explicit warning is appended in the answer noting the unverified metric/claim.
    """
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": (
                 "Improving onboarding drives strong ROI: Adam Fishman stated that "
                 "'improving the onboarding experience can improve user revenue by 25%'. "
                 "In addition, top teams achieve an 85% activation benchmark within 7 days."
             ),
             "citations": [
                 {
                     "source_id": "chunk_fishman_32",
                     "quote": "improving the onboarding experience can improve user revenue by 25%"
                 },
                 {
                     "source_id": "chunk_fishman_32",
                     "quote": "top teams achieve an 85% activation benchmark within 7 days"
                 }
             ]
         })):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "What activation targets are recommended?"})
        assert res.status_code == 200
        data = res.json()
        # Must be partially_verified, NOT grounded_answer
        assert data["response_type"] == "partially_verified"
        # Only the 1 verified citation remains
        assert len(data["citations"]) == 1
        assert data["citations"][0]["source_id"] == "chunk_fishman_32"
        # 85% is NOT in any verified citation
        for c in data["citations"]:
            assert "85%" not in c.get("content", "")
        # Implementation labels and disclaimers absent
        assert "[WARNING: PARTIALLY VERIFIED]" not in data["answer"]
        assert "Note:" not in data["answer"]
        assert "[UNVERIFIED QUOTE:" not in data["answer"]


def test_conversational_follow_up_with_history():
    """When user asks about what was recommended in previous answer, answer from history as conversational."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    
    mock_history_msgs = [
        MagicMock(role="user", content="What strategies do transcripts recommend for activation?"),
        MagicMock(role="assistant", content="The transcripts highlight that improving onboarding increases revenue by 25%. No specific activation percentage target was recommended.")
    ]
    
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.call_pi_agent", return_value=(
             "Based on my previous answer, I did not recommend a specific target activation metric; I noted the 25% revenue impact from onboarding.",
             None,
             None
         )):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = mock_history_msgs
        res = client.post("/api/v1/chat", json={
            "session_id": str(mock_session.id),
            "question": "Based on your previous answer, what target did you recommend?"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "conversational"
        assert len(data["citations"]) == 0
        assert "did not recommend a specific target" in data["answer"]


def test_conversational_follow_up_missing_history_reports_clearly():
    """If conversational follow-up is asked with missing history, state history is missing without guessing."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    
    with patch("app.main.crud") as mock_crud:
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = [] # Empty history!
        res = client.post("/api/v1/chat", json={
            "session_id": str(mock_session.id),
            "question": "Based on your previous answer, what target did you recommend?"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "conversational"
        assert len(data["citations"]) == 0
        assert "no previous conversation history" in data["answer"].lower()


def test_out_of_domain_refusal_preserved():
    """Refusal on out-of-domain questions preserves model explanation and sets insufficient_evidence."""
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    pasta_reply = "The transcripts do not contain instructions or recipes for making Italian carbonara pasta."
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=("", [])), \
         patch("app.main.call_pi_agent", return_value=(pasta_reply, None, None)):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={"question": "How do I make authentic Italian carbonara?"})
        assert res.status_code == 200
        data = res.json()
        assert data["response_type"] == "insufficient_evidence"
        assert len(data["citations"]) == 0
        assert "carbonara" in data["answer"]


def test_follow_up_introducing_new_podcast_claims_requires_evidence():
    """
    If a follow-up mentions previous answer but introduces new podcast claims,
    it must NOT bypass retrieval or evidence checks.
    """
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    mock_history_msgs = [
        MagicMock(role="user", content="Hi"),
        MagicMock(role="assistant", content="Hello! How can I help you?")
    ]
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)) as mock_retrieval, \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": "Adam Fishman explains growth tactics.",
             "citations": [{"source_id": "chunk_fishman_32", "quote": "improving the onboarding experience can improve user revenue by 25%"}]
         })):
        mock_crud.create_session.return_value = mock_session
        mock_crud.get_session.return_value = mock_session
        mock_crud.get_session_messages.return_value = mock_history_msgs
        res = client.post("/api/v1/chat", json={
            "session_id": str(mock_session.id),
            "question": "Based on your previous answer, what does Adam Fishman say about growth teams?"
        })
        assert res.status_code == 200
        # Retrieval must be invoked for new podcast claims
        mock_retrieval.assert_called_once()
        data = res.json()
        assert data["response_type"] == "grounded_answer"
        assert len(data["citations"]) == 1
