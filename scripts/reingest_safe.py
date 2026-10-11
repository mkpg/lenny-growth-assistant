import os
import sys
import yaml
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import TranscriptChunk
from app.chunking import chunk_text
from scripts.ingest_sample import get_embedding, parse_markdown_with_frontmatter

def main():
    repo_path = Path("scratch/lennys-podcast-transcripts/episodes")
    sample_episodes = ["ada-chen-rekhi", "adam-fishman", "adam-grenier"]
    
    print("--- PREPARATION PHASE ---")
    prepared_chunks = []
    
    # 1. Parse and generate new chunks + embeddings in memory first
    for guest_dir_name in sample_episodes:
        guest_dir = repo_path / guest_dir_name
        if not guest_dir.is_dir():
            print(f"Directory not found: {guest_dir}")
            return
            
        transcript_file = guest_dir / "transcript.md"
        frontmatter, markdown_content = parse_markdown_with_frontmatter(transcript_file)
        
        guest = frontmatter.get("guest") or frontmatter.get("title")
        title = frontmatter.get("title")
        source_url = frontmatter.get("youtube_url") or frontmatter.get("spotify_url")
        
        chunks = chunk_text(markdown_content)
        print(f"Parsed {guest_dir_name}: Generated {len(chunks)} chunks.")
        
        for idx, chunk_text_content in enumerate(chunks):
            embedding = get_embedding(chunk_text_content)
            if len(embedding) != 768:
                print(f"ERROR: Expected embedding dimension 768, got {len(embedding)}")
                return
                
            db_chunk = TranscriptChunk(
                source_id=f"{guest_dir_name}_{idx}",
                guest=guest,
                episode_title=title,
                source_url=source_url,
                chunk_index=idx,
                content=chunk_text_content,
                embedding=embedding
            )
            prepared_chunks.append(db_chunk)

    print("\n--- VALIDATION PHASE ---")
    print(f"Total new chunks prepared: {len(prepared_chunks)}")
    for chunk in prepared_chunks:
        if not chunk.source_id or not chunk.embedding or len(chunk.embedding) != 768:
            print("ERROR: A prepared chunk failed validation.")
            return
        if not chunk.guest or not chunk.episode_title or not chunk.source_url:
            print("ERROR: A prepared chunk is missing metadata.")
            return
            
    print("All prepared chunks passed validation (source_id, content, 768-dim embeddings, metadata).")

    # 2. Collect existing IDs and Unrelated IDs
    db = SessionLocal()
    try:
        all_ids_before = {i[0] for i in db.query(TranscriptChunk.source_id).all()}
        
        existing_ids = []
        counts_per_source = {}
        for s in sample_episodes:
            ids = db.query(TranscriptChunk.source_id).filter(TranscriptChunk.source_id.startswith(s)).all()
            ids_list = [i[0] for i in ids]
            existing_ids.extend(ids_list)
            counts_per_source[s] = len(ids_list)
            
        unrelated_ids = all_ids_before - set(existing_ids)
        
        print(f"Total rows in DB before transaction: {len(all_ids_before)}")
        print(f"Found {len(existing_ids)} existing target chunks in database to be replaced.")
        print(f"Found {len(unrelated_ids)} unrelated chunks to preserve.")
        
        # We stop here for the preflight report as requested by the user
        print("\n--- PREFLIGHT REPORT ---")
        print("Proposed replacement:")
        print(f"  Old row count to delete: {len(existing_ids)}")
        print(f"  Old rows per source: {counts_per_source}")
        print(f"  New row count to insert: {len(prepared_chunks)}")
        print(f"  Unrelated rows to preserve: {len(unrelated_ids)}")
        print("  Exact targeted guests:", sample_episodes)
        print("  Metadata explicitly confirmed for all new chunks (Guest, Title, URL).")
        print("  Rollback behavior: The deletion and insertion will be wrapped in a single database transaction.")
        print("  If insertion fails, the deletion will be automatically rolled back.")
        
        if "--execute" in sys.argv:
            print("\n--- EXECUTING TRANSACTION ---")
            try:
                # Issue the delete and insert inside the SAME transaction
                for s in sample_episodes:
                    # synchronize_session=False is standard for bulk deletes. The DB handles the deletion.
                    db.query(TranscriptChunk).filter(TranscriptChunk.source_id.startswith(s)).delete(synchronize_session=False)
                
                db.add_all(prepared_chunks)
                
                # Flush to database without committing, so we can run pre-commit validation queries within the transaction context
                db.flush()
                
                print("\n--- PRE-COMMIT VALIDATION ---")
                
                # 1. Verify unrelated records exactly
                current_unrelated_ids = {i[0] for i in db.query(TranscriptChunk.source_id).filter(~TranscriptChunk.source_id.in_(existing_ids)).filter(TranscriptChunk.source_id.notin_([c.source_id for c in prepared_chunks])).all()}
                
                # If there were no unrelated IDs before, this should be empty. But a better check is just fetching everything not in our new set
                prepared_ids_set = {c.source_id for c in prepared_chunks}
                all_current_ids = {i[0] for i in db.query(TranscriptChunk.source_id).all()}
                current_unrelated_ids_actual = all_current_ids - prepared_ids_set
                
                if current_unrelated_ids_actual != unrelated_ids:
                    raise Exception(f"Validation failed: Unrelated records modified. Expected {len(unrelated_ids)}, found {len(current_unrelated_ids_actual)}.")
                
                # 2. Validate every replacement row
                inserted_rows = db.query(TranscriptChunk).filter(TranscriptChunk.source_id.in_(prepared_ids_set)).all()
                if len(inserted_rows) != len(prepared_chunks):
                    raise Exception(f"Validation failed: Expected {len(prepared_chunks)} inserted rows, found {len(inserted_rows)}.")
                
                # Full check on every single inserted row
                for row in inserted_rows:
                    if not row.content or not row.guest or not row.episode_title or not row.source_url:
                        raise Exception(f"Validation failed: Row {row.source_id} is missing metadata or content.")
                    if len(row.embedding) != 768:
                        raise Exception(f"Validation failed: Row {row.source_id} has invalid embedding dim {len(row.embedding)}.")
                
                # 3. Check row counts for each source prefix
                new_counts_per_source = {}
                for s in sample_episodes:
                    new_counts_per_source[s] = len([r for r in inserted_rows if r.source_id.startswith(s)])
                
                expected_new_counts = {'ada-chen-rekhi': 67, 'adam-fishman': 54, 'adam-grenier': 56}
                if new_counts_per_source != expected_new_counts:
                    raise Exception(f"Validation failed: Expected rows per source {expected_new_counts}, got {new_counts_per_source}.")
                
                print("Pre-commit validation passed. All constraints verified inside transaction.")
                
                db.commit()
                print("TRANSACTION COMMITTED. Successfully replaced records.")
            except Exception as e:
                db.rollback()
                print(f"TRANSACTION FAILED. Rolled back successfully. Error: {e}")
                return

            # Post-commit verification
            print("\n--- POST-COMMIT VERIFICATION ---")
            post_db = SessionLocal()
            try:
                total_new = post_db.query(TranscriptChunk).filter(TranscriptChunk.source_id.in_([c.source_id for c in prepared_chunks])).count()
                print(f"Verified {total_new} records in database post-commit.")
                if total_new != len(prepared_chunks):
                    print(f"CRITICAL WARNING: Expected {len(prepared_chunks)} records, but found {total_new}.")
                    print("Because the commit succeeded, rollback is no longer possible. DB requires manual inspection.")
            finally:
                post_db.close()
                
        else:
            print("\nHALTING execution before database transaction. Run with '--execute' to commit.")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
