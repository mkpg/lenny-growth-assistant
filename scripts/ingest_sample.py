import os
import sys
import yaml
import httpx
from pathlib import Path
from sqlalchemy.orm import Session
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from app.database import SessionLocal
from app.models import TranscriptChunk

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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

from app.chunking import chunk_text

def parse_markdown_with_frontmatter(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) == 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                markdown_content = parts[2].strip()
                return frontmatter, markdown_content
            except yaml.YAMLError:
                return {}, content
    
    return {}, content

def main():
    repo_path = Path("scratch/lennys-podcast-transcripts/episodes")
    if not repo_path.exists():
        print(f"Directory not found: {repo_path}")
        return

    db: Session = SessionLocal()
    
    sample_episodes = ["ada-chen-rekhi", "adam-fishman", "adam-grenier"]
    
    try:
        chunk_count = 0
        file_count = 0
        
        for guest_dir_name in sample_episodes:
            guest_dir = repo_path / guest_dir_name
            if guest_dir.is_dir():
                transcript_file = guest_dir / "transcript.md"
                if transcript_file.exists():
                    # Check idempotency per file
                    existing = db.query(TranscriptChunk).filter(TranscriptChunk.source_id.startswith(guest_dir.name)).first()
                    if existing:
                        print(f"Skipping {guest_dir.name}, already ingested.")
                        continue
                        
                    frontmatter, markdown_content = parse_markdown_with_frontmatter(transcript_file)
                    
                    guest = frontmatter.get("guest") or frontmatter.get("title")
                    title = frontmatter.get("title")
                    source_url = frontmatter.get("youtube_url") or frontmatter.get("spotify_url")
                    
                    chunks = chunk_text(markdown_content)
                    print(f"Processing {guest_dir.name}: {len(chunks)} chunks.")
                    
                    for idx, chunk_text_content in enumerate(chunks):
                        embedding = get_embedding(chunk_text_content)
                        # Verify dimension
                        if len(embedding) != 768:
                            raise ValueError(f"Expected embedding dim 768, got {len(embedding)}")
                            
                        db_chunk = TranscriptChunk(
                            source_id=f"{guest_dir.name}_{idx}",
                            guest=guest,
                            episode_title=title,
                            source_url=source_url,
                            chunk_index=idx,
                            content=chunk_text_content,
                            embedding=embedding
                        )
                        db.add(db_chunk)
                        chunk_count += 1
                    
                    file_count += 1
                    
        db.commit()
        print(f"Successfully ingested {file_count} files into {chunk_count} chunks.")
    except Exception as e:
        db.rollback()
        print(f"Error during ingestion: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
