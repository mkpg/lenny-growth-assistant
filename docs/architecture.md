# Architecture — The Lenny Growth Assistant

**Status:** Proposed architecture. Update this document to match the implementation actually built.

## 1. Architecture goals
- Source-grounded answers with traceable provenance.
- Simple end-to-end system that fits the deadline.
- Local Ollama demo and one cloud model option.
- Independent persisted sessions.
- Constrained agent workflows.
- Safe artifact rendering and reproducible handoff.

## 2. Logical components

```text
Browser (vanilla HTML/CSS/JS)
  ├── Chat + session selector + provider selector
  ├── Source citation list
  └── Artifact viewer
         │ HTTP/JSON
         ▼
FastAPI
  ├── API validation / error mapping / health
  ├── Session and message service
  ├── Workflow router
  │    ├── Grounded Q&A
  │    ├── Ship 30 essay skill
  │    └── Artifact generation skill
  ├── Retrieval service
  │    ├── PostgreSQL full-text search
  │    └── pgvector similarity search (if validated)
  └── Model adapter
       ├── Ollama (mandatory local demo)
       └── Cloud provider (at least one)
         │
         ▼
Neon PostgreSQL + pgvector
  ├── sessions
  ├── messages
  ├── transcript_chunks + metadata + embedding
  └── artifacts
```

The required agent layer must use Pi Coding Agent or Anthropic Claude Agent SDK. The preferred candidate is Pi, conditional on a short smoke test. If its TypeScript runtime adds too much integration cost, use the assignment-permitted Claude Agent SDK for the cloud agent and an explicit Ollama adapter for local mode. Document the final choice and test it. Do not represent a hand-written router alone as satisfying the agent SDK requirement.

## 3. Ingestion and retrieval
1. Inspect transcript repository layout, metadata, attribution and any licensing terms.
2. Parse files without assuming every transcript has identical formatting.
3. Normalize metadata: guest, episode title, source URL, publication date, timestamps where available.
4. Split into meaningful passages, preferably preserving speaker-turn boundaries and enough adjacent context. Avoid tiny chunks that lose meaning.
5. Generate embeddings with Ollama `nomic-embed-text` only after confirming the model is available and works.
6. Store passage text, metadata, embedding and stable source identifier in PostgreSQL.
7. Search lexical and semantic indexes. Start with a simple, explainable combination; do not add reranking before measuring baseline quality.
8. Pass only selected evidence and source metadata to the model.
9. Return answer text plus structured citations that refer to retrieved chunk IDs.
10. If evidence is absent or weak, abstain or state the uncertainty.

Citation fields should be populated only when available. Never invent timestamps or source URLs.

## 4. Model and agent routing
- Provider is selected explicitly via configuration and UI.
- Local Ollama is mandatory for the demo.
- At least one cloud provider is supported.
- Keep retrieval and product workflows shared across providers.
- Show the selected provider and model.
- Do not silently fall back. Missing keys/unavailable services return clear, actionable errors.
- Agent tools/workflows should be bounded:
  - `search_transcripts`
  - `write_ship30_essay`
  - `create_artifact`
- Normal Q&A should use a predictable retrieval workflow. Additional retrieval attempts are allowed only when evidence is weak and within a bounded limit.

## 5. Minimal data model
- `sessions`: id, created_at, updated_at, optional non-sensitive metadata.
- `messages`: id, session_id, role, content, created_at, provider/model metadata where useful.
- `transcript_chunks`: id, source_id, guest, episode_title, source_url, published_at, start/end timestamps where available, chunk_index, content, embedding.
- `artifacts`: id, session_id, message_id if applicable, artifact_type (`markdown` or `html`), title, content, created_at.

Use stable IDs, foreign keys and indexes. Preserve session isolation in every read/write path. The embedding vector dimension must match the actual embedding model output; do not hardcode a dimension without checking it.

## 6. API contract proposal
- `GET /health` — app and database readiness status (avoid exposing secrets).
- `POST /sessions` — create session.
- `GET /sessions` — list sessions for this local single-user app.
- `GET /sessions/{session_id}/messages` — fetch session history.
- `POST /sessions/{session_id}/messages` — submit user message, run selected workflow, persist response and citations.
- `POST /sessions/{session_id}/artifacts` — optional dedicated endpoint if not handled through message routing.
- `GET /sessions/{session_id}/artifacts/{artifact_id}` — retrieve artifact, verifying session ownership.
- `POST /ingest` or a CLI ingestion command — ingest local transcript files; do not expose unrestricted filesystem ingestion in a public API.

Finalize request/response shapes after inspecting the repository and agent SDK. Validate IDs and payload sizes.

## 7. Artifact security
- Markdown: render with a safe renderer and DOMPurify if HTML-capable rendering is enabled.
- HTML: render in an iframe using a restrictive `sandbox` attribute without `allow-same-origin`; do not enable arbitrary script execution. Add restrictive CSP, ideally denying network connections and limiting resource sources.
- Never place model-generated content directly into the trusted application DOM.
- Do not expose tokens, backend APIs with privileged capabilities, or trusted UI objects to the iframe.
- Test malicious markup and document the actual tested controls.

## 8. Deployment
- Docker Compose: FastAPI and frontend only (do NOT provision a local PostgreSQL container).
- Database: Configure Neon PostgreSQL connection via environment variables.
- Ollama runs on the host unless testing proves containerization is easier; document the correct host address for the user's OS and container network.
- `.env.example` contains placeholders only.
- Health checks and dependency readiness must be explicit.
- Do not assume the host's `localhost` is reachable from a container using the same address.

## 9. Observability and failures
Structured logs should include request/session identifier, workflow, selected provider, retrieval count, latency and error category. Do not log secrets or unnecessary transcript/message contents.

Expected failures: missing cloud key, Ollama down, timeout, empty retrieval, malformed model output, database unavailable, invalid session, invalid artifact type. Return useful error messages and safe HTTP status codes.
