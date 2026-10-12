import httpx
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import TranscriptChunk

logger = logging.getLogger(__name__)

class RetrievalError(Exception):
    """Raised when the retrieval infrastructure itself fails (embedding service down, DB error)."""
    pass

def get_embedding(text: str) -> list[float]:
    url = "http://localhost:11434/api/embeddings"
    payload = {
        "model": "nomic-embed-text",
        "prompt": text
    }
    response = httpx.post(url, json=payload, timeout=60.0)
    response.raise_for_status()
    data = response.json()
    return data["embedding"]

def retrieve_context(query: str, db: Session, top_k: int = 8, threshold: float = 0.45) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Retrieves chunks from the database matching the query via pgvector distance.

    ``top_k`` controls how many candidate chunks are fetched from the DB before
    threshold filtering (default raised to 8 so relevant chunks that rank beyond
    3rd are not silently excluded).

    Citation deduplication is keyed on ``source_id`` (chunk-level), not on
    ``source_url`` (episode-level), so distinct chunks from the same episode each
    appear as separate citation entries.  Chunks with the identical ``source_id``
    are never duplicated.

    Returns:
        A tuple of (formatted_context_string, list_of_citation_dicts)
    Raises:
        RetrievalError: If the embedding service or database query fails.
    """
    try:
        embedding = get_embedding(query)
    except httpx.ConnectError:
        raise RetrievalError("Embedding service (Ollama) is not reachable at localhost:11434")
    except httpx.HTTPStatusError as e:
        raise RetrievalError(f"Embedding service returned an error: {e.response.status_code}")
    except Exception as e:
        raise RetrievalError(f"Embedding failed: {e}")

    distance_col = TranscriptChunk.embedding.cosine_distance(embedding).label('distance')
    stmt = select(TranscriptChunk, distance_col).order_by(distance_col).limit(top_k)

    try:
        results = db.execute(stmt).all()
    except Exception as e:
        raise RetrievalError(f"Database query failed during retrieval: {e}")

    unique_citations: List[Dict[str, Any]] = []
    seen_source_ids: set = set()
    context_parts: List[str] = []

    for chunk, dist in results:
        if dist > threshold:
            continue

        # Deduplicate citations at the chunk level (source_id), not the episode
        # level (source_url), so two distinct chunks from the same episode are
        # both surfaced as citations.
        if chunk.source_id not in seen_source_ids:
            seen_source_ids.add(chunk.source_id)
            citation = {
                "source_id": chunk.source_id,
                "episode_title": chunk.episode_title,
                "source_url": chunk.source_url,
                "distance": float(dist),
                "content": chunk.content,
                "guest": chunk.guest,
            }
            unique_citations.append(citation)

        # Every surviving chunk contributes its text to the LLM context.
        context_part = f"Source ID: {chunk.source_id}\n"
        context_part += f"Title: {chunk.episode_title} (URL: {chunk.source_url})\n"
        context_part += f"Excerpt: {chunk.content}\n"
        context_parts.append(context_part)

    formatted_context = "\n---\n\n".join(context_parts)
    return formatted_context, unique_citations
