"""
Unit tests for app/retrieval.py.

Covers:
  1. Default top_k is now 8 (not 3).
  2. The SQL LIMIT is driven by the top_k argument.
  3. Citation deduplication is keyed on source_id (chunk-level), not source_url
     (episode-level) – two distinct chunks from the same episode both appear as
     separate citation entries.
  4. Chunks sharing the exact same source_id are not duplicated in citations.
  5. Chunks above the distance threshold are filtered out.
  6. Every chunk below the threshold (regardless of citation deduplication)
     contributes its text to the formatted context string.
  7. An explicit top_k argument overrides the default.

No database or Ollama server is required; all external calls are mocked.
"""
import inspect
import pytest
from unittest.mock import patch, MagicMock

from app.retrieval import retrieve_context, RetrievalError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(source_id: str, source_url: str, episode_title: str = "Ep",
                content: str = "some text", guest: str = "Guest"):
    """Return a MagicMock that behaves like a TranscriptChunk ORM object."""
    chunk = MagicMock()
    chunk.source_id = source_id
    chunk.source_url = source_url
    chunk.episode_title = episode_title
    chunk.content = content
    chunk.guest = guest
    return chunk


def _db_returning(rows):
    """Return a mock SQLAlchemy Session whose execute().all() yields *rows*."""
    db = MagicMock()
    db.execute.return_value.all.return_value = rows
    return db


FAKE_EMBEDDING = [0.1] * 768


# ---------------------------------------------------------------------------
# 1. Default top_k is 8
# ---------------------------------------------------------------------------

class TestDefaultTopK:
    def test_signature_default_top_k_is_8(self):
        sig = inspect.signature(retrieve_context)
        assert sig.parameters["top_k"].default == 8, (
            "retrieve_context top_k default must be 8"
        )

    def test_db_limit_uses_default_top_k(self):
        """When called without explicit top_k the SQL statement must LIMIT 8.

        SQLAlchemy renders the limit as a bound parameter (:param_1) in the
        string representation of the Select object, so we read the value
        directly from the internal _limit_clause rather than from str().
        """
        db = _db_returning([])
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            retrieve_context("some query", db)

        stmt = db.execute.call_args[0][0]
        # _limit_clause is a BindParameter whose .value holds the integer.
        limit_value = stmt._limit_clause.value
        assert limit_value == 8, (
            f"Expected LIMIT 8 with default top_k, got {limit_value}"
        )

    def test_explicit_top_k_overrides_default(self):
        """Passing top_k=3 explicitly must result in LIMIT 3."""
        db = _db_returning([])
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            retrieve_context("some query", db, top_k=3)

        stmt = db.execute.call_args[0][0]
        limit_value = stmt._limit_clause.value
        assert limit_value == 3, (
            f"Expected LIMIT 3 with explicit top_k=3, got {limit_value}"
        )


# ---------------------------------------------------------------------------
# 2. Citation deduplication: chunk-level (source_id), not episode-level (source_url)
# ---------------------------------------------------------------------------

class TestCitationDeduplication:
    def test_two_chunks_same_url_different_source_id_both_cited(self):
        """Two chunks from the same episode (same URL, different source_ids)
        must each produce a separate citation entry."""
        chunk_a = _make_chunk("ep-001_chunk_01", "https://example.com/ep1",
                              content="Chunk A text")
        chunk_b = _make_chunk("ep-001_chunk_02", "https://example.com/ep1",
                              content="Chunk B text")
        rows = [(chunk_a, 0.20), (chunk_b, 0.30)]

        db = _db_returning(rows)
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            _, citations = retrieve_context("query", db)

        source_ids = [c["source_id"] for c in citations]
        assert "ep-001_chunk_01" in source_ids
        assert "ep-001_chunk_02" in source_ids
        assert len(citations) == 2

    def test_same_source_id_not_duplicated_in_citations(self):
        """If the DB somehow returns the same source_id twice, citations must
        contain it only once."""
        chunk = _make_chunk("ep-001_chunk_01", "https://example.com/ep1")
        rows = [(chunk, 0.20), (chunk, 0.21)]  # same chunk, two distances

        db = _db_returning(rows)
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            _, citations = retrieve_context("query", db)

        assert len(citations) == 1
        assert citations[0]["source_id"] == "ep-001_chunk_01"

    def test_different_url_different_source_id_both_cited(self):
        """Two chunks from different episodes are both cited (baseline sanity)."""
        chunk_a = _make_chunk("ep-001_chunk_01", "https://example.com/ep1")
        chunk_b = _make_chunk("ep-002_chunk_01", "https://example.com/ep2")
        rows = [(chunk_a, 0.15), (chunk_b, 0.25)]

        db = _db_returning(rows)
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            _, citations = retrieve_context("query", db)

        assert len(citations) == 2


# ---------------------------------------------------------------------------
# 3. Threshold filtering
# ---------------------------------------------------------------------------

class TestThresholdFiltering:
    def test_chunk_above_threshold_excluded(self):
        """A chunk with distance > 0.45 must not appear in citations or context."""
        chunk_far = _make_chunk("ep-far", "https://example.com/far", content="Far text")
        chunk_near = _make_chunk("ep-near", "https://example.com/near", content="Near text")
        rows = [(chunk_near, 0.30), (chunk_far, 0.50)]

        db = _db_returning(rows)
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            context, citations = retrieve_context("query", db)

        assert "Far text" not in context
        assert all(c["source_id"] != "ep-far" for c in citations)

    def test_chunk_at_threshold_included(self):
        """Distance exactly equal to threshold (0.45) is INCLUDED.

        The filter is ``dist > threshold`` (strict greater-than), so a chunk
        whose distance equals the threshold passes the filter and is returned.
        """
        chunk = _make_chunk("ep-boundary", "https://example.com/boundary",
                            content="Boundary text")
        rows = [(chunk, 0.45)]

        db = _db_returning(rows)
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            context, citations = retrieve_context("query", db)

        assert len(citations) == 1
        assert "Boundary text" in context

    def test_chunk_just_above_threshold_excluded(self):
        """Distance 0.451 (just above threshold) must be excluded."""
        chunk = _make_chunk("ep-over", "https://example.com/over",
                            content="Over text")
        rows = [(chunk, 0.451)]

        db = _db_returning(rows)
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            context, citations = retrieve_context("query", db)

        assert citations == []
        assert context == ""

    def test_all_chunks_below_threshold_included(self):
        """All chunks below the threshold contribute to context."""
        chunks = [
            _make_chunk(f"ep-00{i}", f"https://example.com/ep{i}",
                        content=f"Text {i}")
            for i in range(4)
        ]
        rows = [(c, 0.10 * (i + 1)) for i, c in enumerate(chunks)]  # 0.1, 0.2, 0.3, 0.4

        db = _db_returning(rows)
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            context, citations = retrieve_context("query", db)

        assert len(citations) == 4
        for i in range(4):
            assert f"Text {i}" in context


# ---------------------------------------------------------------------------
# 4. Context string: every passing chunk contributes text even if its
#    citation entry was deduplicated.
# ---------------------------------------------------------------------------

class TestContextStringCompleteness:
    def test_both_chunks_appear_in_context_even_when_same_url(self):
        """Even when two chunks share a URL (producing one citation), both
        chunks' text must appear in the formatted context string."""
        chunk_a = _make_chunk("ep-001_chunk_01", "https://example.com/ep1",
                              content="First passage about activation.")
        chunk_b = _make_chunk("ep-001_chunk_02", "https://example.com/ep1",
                              content="Second passage about retention.")
        rows = [(chunk_a, 0.20), (chunk_b, 0.30)]

        db = _db_returning(rows)
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            context, _ = retrieve_context("query", db)

        assert "First passage about activation." in context
        assert "Second passage about retention." in context


# ---------------------------------------------------------------------------
# 5. RetrievalError propagation
# ---------------------------------------------------------------------------

class TestRetrievalError:
    def test_embedding_failure_raises_retrieval_error(self):
        import httpx
        db = MagicMock()
        with patch("app.retrieval.get_embedding",
                   side_effect=httpx.ConnectError("refused")):
            with pytest.raises(RetrievalError, match="not reachable"):
                retrieve_context("query", db)

    def test_db_failure_raises_retrieval_error(self):
        db = MagicMock()
        db.execute.side_effect = RuntimeError("DB is down")
        with patch("app.retrieval.get_embedding", return_value=FAKE_EMBEDDING):
            with pytest.raises(RetrievalError, match="Database query failed"):
                retrieve_context("query", db)
