# Test Plan: Lenny Growth Assistant

This document outlines the test strategy, encompassing both the automated backend suite and manual UI verification steps.

## 1. Automated Test Suite

The automated test suite verifies the core backend behavior: database migrations, API endpoints, agent inference handling, and RAG retrieval.

### Running the Suite
```bash
# Core unit tests (FastAPI, Chat Logic, Session Integrity)
python -m pytest tests/

# End-to-end Pi Agent tests (Subprocess bounds, timeouts, malformed JSON)
python -m pytest scratch/test_phase7a.py scratch/test_phase7a1.py

# Live workflow smoke test (Must be run with Uvicorn active)
python scripts/test_workflow.py
```

### Key Automated Scenarios
- **Liveness & Readiness**: `/health` returns 200; `/ready` returns 503 if DB missing, 200 if connected to Neon.
- **Session Rejection**: Supplying an invalid UUID or fake session ID returns 404, preventing silent overwrites.
- **Agent Timeout / Process Hangs**: The `call_pi_agent` function enforces a strict 60s timeout, gracefully terminating the subprocess if the Pi CLI hangs.
- **RAG Integrity**: The `retrieve_context` function correctly filters out semantic search results with distance > 0.55.

## 2. Manual UI Test Plan

After verifying automated tests, perform these manual tests in the browser (`http://127.0.0.1:8000`).

### Test Case 2.1: Basic Chat & Citation
1. Open the UI.
2. Send: *"What does Adam Fishman say about onboarding?"*
3. **Expected**: The assistant answers based on the transcript. A clear citation chip appears at the bottom linking to the YouTube episode.

### Test Case 2.2: Greeting Exemption
1. Send: *"Hello"* or *"Hi there"*
2. **Expected**: The assistant responds naturally to the greeting. No citations are displayed (RAG is bypassed for short greetings).

### Test Case 2.3: Session Memory
1. Following Test 2.1, send: *"Summarize that in 3 bullet points."*
2. **Expected**: The assistant correctly summarizes the *previous* answer about onboarding. (Verifies session context).

### Test Case 2.4: Out-of-Scope Rejection
1. Send: *"What is the capital of France?"*
2. **Expected**: The assistant explicitly states: *"I cannot find information about this in the retrieved transcripts"* (or similar refusal). It does not hallucinate facts.

### Test Case 2.5: Artifact Viewer (Future/Extended)
1. If an answer includes markdown tables or formatted lists, click on it if an artifact button appears (or verify the markdown renders correctly in the chat window).
2. **Expected**: The markdown parses and renders clearly with CSS styling (glassmorphism/dark mode).
