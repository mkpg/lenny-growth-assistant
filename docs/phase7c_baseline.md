# Phase 7C Baseline Report

## Existing Behavior and Tests
Before starting Phase 7C modifications, all existing tests in the repository were executed to establish a reproducible baseline. 

- **Test Suite Command**: `venv\Scripts\python.exe -m pytest tests\ scratch\test_phase7a.py scratch\test_phase7a1.py scratch\test_phase7b.py`
- **Result**: 28 passed, 0 failed.

## Known Deficiencies
Despite passing all pre-7C tests (which verified API contracts, database persistence, RAG execution, and simple citation removal), manual testing previously identified critical logical and security regressions:

1. **False Claim Rationalization**: The model fails to safely reject unsupported assertions (e.g., doubling advertising budgets) and instead fabricates reasoning.
2. **Citation Laundering / Orphaned Sources**: The existing implementation may cite unrelated transcripts (e.g., Ada Chen) for answers regarding other individuals (e.g., Adam Fishman) if the similarity search surfaces them.
3. **Artifact Pipeline Instability**: Generating HTML artifacts currently yields descriptive text ("Here is your landing page...") rather than the raw document string rendering correctly into the artifact viewer.
4. **Prompt Injection Susceptibility**: The agent is vulnerable to instructions asking to bypass verification or fabricate citations (e.g., "Invent three quotes...").
5. **Format Rigidity without Grounding**: Enforcing formatting rules (e.g., 3 bullet points) causes the model to invent unsupported claims if the retrieved evidence is insufficient.

## Data Flow
`User input → frontend request → FastAPI endpoint (main.py) → intent classification → transcript retrieval (retrieval.py) → conversation history → Pi Agent (agent.py) → response parsing (main.py) → schema validation (schemas.py) → API response → frontend state (script.js) → chat/citation rendering → artifact viewer`

## Objectives for Phase 7C
- Make `ChatResponse` handle structured response types natively rather than relying exclusively on lightweight substring checks (e.g. `refusal_phrases`).
- Secure the system prompt against injections, hidden-instruction extractions, and multi-turn manipulation.
- Guarantee that citations presented to the user are ONLY those corresponding to claims the agent explicitly verifies against retrieved text. 
- Implement a rigid HTML extraction and verification step for artifact requests, preventing descriptions from leaking into the UI.
