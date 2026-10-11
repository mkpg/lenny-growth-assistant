import os
import sys
import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from app.database import SessionLocal
from app.models import TranscriptChunk

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

def retrieve(query: str, top_k: int = 3, threshold: float = 0.35):
    db: Session = SessionLocal()
    try:
        embedding = get_embedding(query)
        
        # We also want to compute the distance to filter out completely irrelevant chunks.
        # pgvector cosine_distance returns a distance (0 for identical, 1 for orthogonal, 2 for opposite).
        distance_col = TranscriptChunk.embedding.cosine_distance(embedding).label('distance')
        
        stmt = select(TranscriptChunk, distance_col).order_by(distance_col).limit(top_k)
        results = db.execute(stmt).all()
        
        print(f"\n--- Results for: '{query}' ---")
        found_relevant = False
        for chunk, dist in results:
            if dist > threshold:
                continue
            found_relevant = True
            print(f"[{chunk.episode_title}] (URL: {chunk.source_url}) - Distance: {dist:.4f}")
            print(f"Chunk {chunk.chunk_index} preview: {chunk.content[:150].replace(chr(10), ' ')}...\n")
            
        if not found_relevant:
            print("No relevant results found (all results exceeded distance threshold).")
            # print top closest anyway to debug
            if results:
                print(f"Closest match distance was: {results[0].distance:.4f}")
            
    except Exception as e:
        print(f"Error during retrieval: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    retrieve("What is Adam Fishman's advice on product growth?")
    retrieve("What does the podcast say about building a time machine out of cheese?")
