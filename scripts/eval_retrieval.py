import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.database import SessionLocal
from app.retrieval import retrieve_context

def main():
    queries = [
        "How do I find product-market fit?",
        "What are the best strategies for user activation?",
        "How can I improve user retention?",
        "How to make pasta?",
        "Is advertising scalable?",
        "What is the best way to handle performance reviews?",
        "What are the pros and cons of building a marketplace?",
        "Tell me about organic vs paid marketing."
    ]
    
    db = SessionLocal()
    
    thresholds_to_test = [0.35, 0.45, 0.55]
    
    for q in queries:
        print(f"\n{'='*50}\nQUERY: {q}\n{'='*50}")
        for t in thresholds_to_test:
            print(f"\n--- Threshold: {t} ---")
            context, citations = retrieve_context(q, db, top_k=5, threshold=t)
            
            if not citations:
                print("  No chunks retrieved.")
            else:
                for cit in citations:
                    print(f"  [{cit['distance']:.4f}] {cit['source_id']} - {cit['episode_title']}")

if __name__ == "__main__":
    main()
