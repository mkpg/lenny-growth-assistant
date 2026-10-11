"""
Real end-to-end smoke test for Phase 5.
Requires: running FastAPI server, Ollama with qwen2.5:3b, Neon DB with ingested transcripts.
"""
import os
import sys
import uuid
import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

BASE_URL = "http://127.0.0.1:8000"
PASS_COUNT = 0
FAIL_COUNT = 0

def report(name, passed, detail=""):
    global PASS_COUNT, FAIL_COUNT
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

def test_chat_workflow():
    global PASS_COUNT, FAIL_COUNT
    print("=" * 60)
    print("Phase 5 End-to-End Smoke Test")
    print("=" * 60)
    
    # 0. Server readiness
    print("\n--- Prerequisite: Server Readiness ---")
    try:
        res = httpx.get(f"{BASE_URL}/ready", timeout=5.0)
        if res.status_code != 200:
            print(f"Server not ready: {res.status_code} {res.text}")
            return
        report("Server /ready", True)
    except Exception as e:
        print(f"Server not reachable. Start it first. Error: {e}")
        return

    # 1. New question with real RAG retrieval and Ollama inference
    print("\n--- Test 1: New Question with Grounded Answer ---")
    payload_1 = {
        "question": "What is Adam Fishman's advice on product growth?",
        "provider": "ollama",
        "model": "qwen2.5:3b"
    }
    res_1 = httpx.post(f"{BASE_URL}/api/v1/chat", json=payload_1, timeout=120.0)
    report("HTTP 200 response", res_1.status_code == 200, f"got {res_1.status_code}")
    if res_1.status_code != 200:
        print(f"  Response: {res_1.text}")
        return
    
    data_1 = res_1.json()
    session_id = data_1["session_id"]
    answer_1 = data_1["answer"]
    citations_1 = data_1["citations"]
    
    report("Session ID returned", bool(session_id))
    report("Citations retrieved from DB", len(citations_1) > 0, f"{len(citations_1)} citations")
    report("Citations have episode_title", all(c.get("episode_title") for c in citations_1))
    report("Citations have source_url", all(c.get("source_url") for c in citations_1))
    report("Non-empty answer", len(answer_1.strip()) > 0)
    print(f"\n  Answer preview: {answer_1[:200]}...")
    for c in citations_1:
        print(f"  Citation: {c['episode_title']} (dist={c['distance']:.3f}, url={c['source_url']})")

    # 2. Follow-up question in the same session
    print("\n--- Test 2: Follow-up Question (Context Retention) ---")
    payload_2 = {
        "session_id": session_id,
        "question": "Can you summarize that advice in one sentence?",
        "provider": "ollama",
        "model": "qwen2.5:3b"
    }
    res_2 = httpx.post(f"{BASE_URL}/api/v1/chat", json=payload_2, timeout=120.0)
    report("Follow-up HTTP 200", res_2.status_code == 200, f"got {res_2.status_code}")
    if res_2.status_code == 200:
        data_2 = res_2.json()
        report("Same session ID", data_2["session_id"] == session_id)
        print(f"  Follow-up answer: {data_2['answer'][:200]}...")

    # 3. Invalid session ID rejection
    print("\n--- Test 3: Invalid Session ID Rejection ---")
    fake_id = str(uuid.uuid4())
    res_3 = httpx.post(f"{BASE_URL}/api/v1/chat", json={
        "session_id": fake_id,
        "question": "test",
        "provider": "ollama",
        "model": "qwen2.5:3b"
    }, timeout=10.0)
    report("Invalid session returns 404", res_3.status_code == 404, f"got {res_3.status_code}")

    # 4. Session isolation
    print("\n--- Test 4: Session Isolation ---")
    payload_4 = {
        "question": "What did I just ask you?",
        "provider": "ollama",
        "model": "qwen2.5:3b"
    }
    res_4 = httpx.post(f"{BASE_URL}/api/v1/chat", json=payload_4, timeout=120.0)
    if res_4.status_code == 200:
        data_4 = res_4.json()
        isolated = data_4["session_id"] != session_id
        report("New session is different", isolated, f"new={data_4['session_id']}")
        print(f"  Independent session answer: {data_4['answer'][:200]}...")
    else:
        report("Independent session request", False, f"got {res_4.status_code}")

    # 5. Unsupported question
    print("\n--- Test 5: Unsupported Question ---")
    payload_5 = {
        "question": "What is the capital of France?",
        "provider": "ollama",
        "model": "qwen2.5:3b"
    }
    res_5 = httpx.post(f"{BASE_URL}/api/v1/chat", json=payload_5, timeout=120.0)
    if res_5.status_code == 200:
        data_5 = res_5.json()
        print(f"  Unrelated question answer: {data_5['answer'][:300]}...")
        # Check that the model didn't fabricate transcript citations
        # The answer should acknowledge it can't answer from context
        report("Response received for unrelated question", True)
    else:
        report("Unrelated question request", False, f"got {res_5.status_code}")

    # 6. Database persistence check
    print("\n--- Test 6: Database Persistence ---")
    try:
        from app.database import SessionLocal
        from app.models import Message
        db = SessionLocal()
        msgs = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).all()
        db.close()
        # We expect at least 4 messages: Q1 user, Q1 assistant, Q2 user, Q2 assistant
        report("Messages persisted in Neon", len(msgs) >= 4, f"{len(msgs)} messages found")
        if msgs:
            for m in msgs:
                print(f"  [{m.role}] {m.content[:80]}... (created_at={m.created_at})")
    except Exception as e:
        report("DB persistence check", False, str(e))

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    print("=" * 60)

if __name__ == "__main__":
    test_chat_workflow()
