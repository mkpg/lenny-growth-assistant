import os
import sys
import yaml
import glob
from pathlib import Path
from sqlalchemy.orm import Session
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from app.database import SessionLocal
from app.models import TranscriptChunk

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
    
    try:
        # Check if already ingested
        existing_count = db.query(TranscriptChunk).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} chunks. Skipping ingestion to prevent duplicates.")
            return

        chunk_count = 0
        file_count = 0
        
        # Iterate over all guest directories
        for guest_dir in repo_path.iterdir():
            if guest_dir.is_dir():
                transcript_file = guest_dir / "transcript.md"
                if transcript_file.exists():
                    frontmatter, markdown_content = parse_markdown_with_frontmatter(transcript_file)
                    
                    guest = frontmatter.get("guest") or frontmatter.get("title")
                    title = frontmatter.get("title")
                    source_url = frontmatter.get("youtube_url") or frontmatter.get("spotify_url")
                    
                    chunks = chunk_text(markdown_content)
                    
                    for idx, chunk_text_content in enumerate(chunks):
                        # Note: We aren't generating embeddings here yet.
                        # This should be updated when the model is selected.
                        db_chunk = TranscriptChunk(
                            source_id=f"{guest_dir.name}_{idx}",
                            guest=guest,
                            episode_title=title,
                            source_url=source_url,
                            chunk_index=idx,
                            content=chunk_text_content,
                            embedding=None # Will populate in a separate pass or when Nomic is available
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
