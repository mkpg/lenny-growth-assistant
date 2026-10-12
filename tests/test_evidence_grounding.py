"""
Regression tests for the evidence-grounding fix.

Scenarios (from the marketplace failure and requirements):
1. Valid quote + unsupported customer-acquisition-cost quotation
   – verified quote kept, fabricated quote replaced inline, partially_verified.
2. Multiple claims where only one has a matching quote
   – fabricated quote replaced, supported prose preserved.
3. Fully supported answer (all citations verified)
   – grounded_answer, no stripping, no warning banners.
4. Answer with no verifiable evidence
   – insufficient_evidence returned.
5. Malformed JSON falling back to Markdown with a verified quote
   – partially_verified, fabricated inline quote replaced, prose preserved.
6. strip_unverified_quotes unit tests (direct, no HTTP).
"""
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.validator import strip_unverified_quotes

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

VERIFIED_CONTENT = (
    "One of the biggest pieces of advice I'm giving to people is: "
    "start by assuming you no longer have product market fit, because "
    "you had product market fit in a different market."
)
VERIFIED_CHUNK = {
    "source_id": "adam-grenier_39",
    "episode_title": "Adam Grenier on marketplace growth",
    "guest": "Adam Grenier",
    "source_url": "https://www.youtube.com/watch?v=marketplace123",
    "distance": 0.37,
    "content": VERIFIED_CONTENT,
}
MOCK_CITATIONS = [VERIFIED_CHUNK]
MOCK_CONTEXT = f"Source ID: adam-grenier_39\nExcerpt: {VERIFIED_CONTENT}\n"

VERIFIED_QUOTE = (
    "start by assuming you no longer have product market fit, "
    "because you had product market fit in a different market"
)
FABRICATED_QUOTE = (
    "marketplace companies that cut customer acquisition costs by 40% "
    "see a threefold improvement in payback period"
)


def _mock_session():
    s = MagicMock()
    s.id = uuid.uuid4()
    return s


# ---------------------------------------------------------------------------
# 1. Valid verified quote + unsupported fabricated CAC quotation
# ---------------------------------------------------------------------------

def test_verified_quote_with_fabricated_cac_quotation():
    """
    Answer contains one real transcript quote and one fabricated CAC metric quote.
    - response_type must be partially_verified (never grounded_answer).
    - Fabricated quotation text is silently removed (no [UNVERIFIED QUOTE:] tag).
    - The verified quote citation is preserved.
    - Fabricated quote is NOT in any citation content.
    """
    session = _mock_session()
    answer_text = (
        f"Adam Grenier advised founders to '{VERIFIED_QUOTE}'. "
        f"Furthermore, research shows that '{FABRICATED_QUOTE}'."
    )
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": answer_text,
             "citations": [
                 {"source_id": "adam-grenier_39", "quote": VERIFIED_QUOTE},
                 {"source_id": "adam-grenier_39", "quote": FABRICATED_QUOTE},
             ]
         })):
        mock_crud.create_session.return_value = session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={
            "question": "What does Grenier say about marketplace growth and CAC?"
        })

    assert res.status_code == 200
    data = res.json()
    assert data["response_type"] == "partially_verified", data["response_type"]
    # Verified citation is preserved
    assert any(c["source_id"] == "adam-grenier_39" for c in data["citations"])
    # Fabricated quote is not in citation content
    for c in data["citations"]:
        assert FABRICATED_QUOTE not in c.get("content", "")
    # Fabricated quotation silently removed — no tag, no quote text
    assert FABRICATED_QUOTE not in data["answer"]
    assert "[UNVERIFIED QUOTE:" not in data["answer"]
    # No banners or disclaimers
    assert "[WARNING: PARTIALLY VERIFIED]" not in data["answer"]
    assert "Note:" not in data["answer"]
    # Verified quote text still present
    assert "product market fit" in data["answer"]


# ---------------------------------------------------------------------------
# 2. Multiple claims, only one has a matching quote
# ---------------------------------------------------------------------------

def test_multiple_claims_only_one_verified():
    """
    Answer has two direct quotations; only the first matches a retrieved chunk.
    - The second fabricated quote is replaced inline.
    - Surrounding descriptive prose is preserved.
    - response_type is partially_verified.
    """
    session = _mock_session()
    fabricated_second = "the best marketplaces achieve 90% seller retention in year one"
    answer_text = (
        f"Grenier says '{VERIFIED_QUOTE}'. "
        f"He also noted that '{fabricated_second}'. "
        "Overall, marketplace companies must rethink their growth assumptions."
    )
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": answer_text,
             "citations": [
                 {"source_id": "adam-grenier_39", "quote": VERIFIED_QUOTE},
                 {"source_id": "adam-grenier_39", "quote": fabricated_second},
             ]
         })):
        mock_crud.create_session.return_value = session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={
            "question": "What did Grenier say about seller retention?"
        })

    assert res.status_code == 200
    data = res.json()
    assert data["response_type"] == "partially_verified"
    assert fabricated_second not in data["answer"]
    assert "[UNVERIFIED QUOTE:" not in data["answer"]
    # Surrounding prose is preserved
    assert "marketplace companies must rethink" in data["answer"]


# ---------------------------------------------------------------------------
# 3. Fully supported answer — grounded_answer, no stripping
# ---------------------------------------------------------------------------

def test_fully_supported_answer_is_grounded():
    """
    When all citations are verified, response_type is grounded_answer and the
    answer is returned unchanged (no fabricated quote stripping, no warning banner).
    """
    session = _mock_session()
    answer_text = (
        f"Adam Grenier recommends that founders '{VERIFIED_QUOTE}' "
        "before launching new acquisition channels."
    )
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": answer_text,
             "citations": [
                 {"source_id": "adam-grenier_39", "quote": VERIFIED_QUOTE},
             ]
         })):
        mock_crud.create_session.return_value = session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={
            "question": "What does Grenier say about product-market fit in new markets?"
        })

    assert res.status_code == 200
    data = res.json()
    assert data["response_type"] == "grounded_answer", data["response_type"]
    assert len(data["citations"]) == 1
    assert "[UNVERIFIED QUOTE:" not in data["answer"]
    assert "[WARNING: PARTIALLY VERIFIED]" not in data["answer"]


# ---------------------------------------------------------------------------
# 4. Answer with no verifiable evidence
# ---------------------------------------------------------------------------

def test_no_verifiable_evidence_returns_insufficient():
    """
    When no citation matches, insufficient_evidence is returned and the model's
    generic refusal prose is preserved (not swapped for a fabricated answer).
    """
    session = _mock_session()
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=("Reply", None, {
             "evidence_state": "sufficient",
             "answer": "Grenier mentioned that 'sellers who invest in photography see 300% uplift'.",
             "citations": [
                 {"source_id": "adam-grenier_39",
                  "quote": "sellers who invest in photography see 300% uplift"}
             ]
         })):
        mock_crud.create_session.return_value = session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={
            "question": "What does Grenier say about photography and seller uplift?"
        })

    assert res.status_code == 200
    data = res.json()
    assert data["response_type"] == "insufficient_evidence"
    assert data["citations"] == []


# ---------------------------------------------------------------------------
# 5. Malformed JSON → Markdown fallback with mixed verified/fabricated quotes
# ---------------------------------------------------------------------------

def test_malformed_json_fallback_strips_fabricated_inline_quote():
    """
    When the model returns Markdown (parsed_response=None) that contains both
    a verified inline quote and a fabricated inline quote:
    - partially_verified is returned.
    - The fabricated inline quote is replaced.
    - Verified quote prose is preserved.
    """
    session = _mock_session()
    fabricated_md_quote = "the top 10% of marketplace founders all learned to code"
    markdown_reply = (
        f"Adam Grenier advises: \"{VERIFIED_QUOTE}\". "
        f"He also believes that \"{fabricated_md_quote}\". "
        "These insights come from his time building growth teams."
    )
    with patch("app.main.crud") as mock_crud, \
         patch("app.main.retrieve_context", return_value=(MOCK_CONTEXT, MOCK_CITATIONS)), \
         patch("app.main.call_pi_agent", return_value=(markdown_reply, None, None)):
        mock_crud.create_session.return_value = session
        mock_crud.get_session_messages.return_value = []
        res = client.post("/api/v1/chat", json={
            "question": "What does Grenier say about growth founders?"
        })

    assert res.status_code == 200
    data = res.json()
    assert data["response_type"] == "partially_verified"
    # Fabricated quote silently removed — no tag
    assert fabricated_md_quote not in data["answer"]
    assert "[UNVERIFIED QUOTE:" not in data["answer"]
    # Surrounding prose preserved
    assert "insights come from his time building growth teams" in data["answer"]
    # No banners or disclaimers
    assert "[NOTE: PARTIALLY VERIFIED]" not in data["answer"]
    assert "Note:" not in data["answer"]


# ---------------------------------------------------------------------------
# 6. Unit tests for strip_unverified_quotes (direct, no HTTP)
# ---------------------------------------------------------------------------

class TestStripUnverifiedQuotes:
    def test_removes_fabricated_quote_silently(self):
        answer = "Grenier said 'sellers achieve 300% uplift' in all cases."
        unverified = [{"quote": "sellers achieve 300% uplift"}]
        result = strip_unverified_quotes(answer, unverified)
        assert "sellers achieve 300% uplift" not in result
        assert "[UNVERIFIED QUOTE:" not in result
        # Surrounding prose preserved
        assert "Grenier said" in result
        assert "in all cases." in result

    def test_leaves_answer_unchanged_when_no_unverified(self):
        answer = "This is a perfectly verified answer."
        result = strip_unverified_quotes(answer, [])
        assert result == answer

    def test_skips_very_short_fragments(self):
        """Fragments shorter than 15 normalised chars must not trigger replacement."""
        answer = "Sales grew 5x fast."
        unverified = [{"quote": "5x fast"}]  # 7 chars normalised
        result = strip_unverified_quotes(answer, unverified)
        assert result == answer

    def test_does_not_touch_paraphrases(self):
        """
        Paraphrases that differ from the unverified quote string are left alone.
        strip_unverified_quotes only operates on exact string matches.
        """
        answer = (
            "Grenier suggested that founders should reconsider product-market fit "
            "when market conditions change significantly."
        )
        unverified = [{"quote": "product-market fit requires constant re-evaluation in shifting markets"}]
        result = strip_unverified_quotes(answer, unverified)
        # The paraphrase is different; nothing should be touched.
        assert "[UNVERIFIED QUOTE:" not in result
        assert result == answer

    def test_handles_missing_quote_key_gracefully(self):
        answer = "Some answer text."
        unverified = [{"source_id": "ep-001"}]  # no 'quote' key
        result = strip_unverified_quotes(answer, unverified)
        assert result == answer

    def test_multiple_unverified_quotes_all_removed(self):
        q1 = "sellers who invest in photography see 300% uplift"
        q2 = "the top 10% of marketplace founders all learned to code"
        answer = f"He said '{q1}' and also '{q2}'. These are big claims."
        unverified = [{"quote": q1}, {"quote": q2}]
        result = strip_unverified_quotes(answer, unverified)
        assert q1 not in result
        assert q2 not in result
        assert "[UNVERIFIED QUOTE:" not in result
        assert "These are big claims." in result
