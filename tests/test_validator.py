import pytest
from app.validator import validate_evidence, ValidationResult

@pytest.fixture
def sample_retrieved():
    return [
        {
            "source_id": "s1",
            "content": "The quick brown fox jumps over the lazy dog.",
            "guest": "Alice",
        },
        {
            "source_id": "s2",
            "content": "She said, \"Hello, world!\"",
            "guest": "Bob",
        },
    ]

def test_exact_match(sample_retrieved):
    model_citations = [
        {"source_id": "s1", "quote": "quick brown fox jumps over", "speaker": "Alice"}
    ]
    result = validate_evidence(model_citations, sample_retrieved, "")
    assert result.has_any_verified
    assert len(result.verified_citations) == 1
    assert result.unverified_citations == []
    assert result.attribution_warnings == []

def test_smart_quote_normalization(sample_retrieved):
    model_citations = [
        {"source_id": "s2", "quote": "\u201cHello, world!\u201d", "speaker": "Bob"}
    ]
    result = validate_evidence(model_citations, sample_retrieved, "")
    assert result.has_any_verified
    assert len(result.verified_citations) == 1
    assert result.unverified_citations == []
    assert result.attribution_warnings == []

def test_recovered_quote_from_other_chunk(sample_retrieved):
    model_citations = [
        {"source_id": "s3", "quote": "quick brown fox", "speaker": "Alice"}
    ]
    result = validate_evidence(model_citations, sample_retrieved, "")
    # The quote exists in s1, so it should be recovered.
    assert result.has_any_verified
    assert len(result.verified_citations) == 1
    assert result.verified_citations[0]["source_id"] == "s1"
    assert result.unverified_citations == []

def test_speaker_mismatch_warning(sample_retrieved):
    model_citations = [
        {"source_id": "s1", "quote": "quick brown fox", "speaker": "Bob"}
    ]
    result = validate_evidence(model_citations, sample_retrieved, "")
    assert result.has_any_verified
    assert len(result.attribution_warnings) == 1
    assert "Speaker mismatch" in result.attribution_warnings[0]

def test_no_verified_citations(sample_retrieved):
    model_citations = [
        {"source_id": "s1", "quote": "nonexistent", "speaker": "Alice"}
    ]
    result = validate_evidence(model_citations, sample_retrieved, "")
    assert not result.has_any_verified
    assert result.verified_citations == []
    assert len(result.unverified_citations) == 1
