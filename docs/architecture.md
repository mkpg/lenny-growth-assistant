# System Architecture Document (architecture.md)
## The Lenny Growth Assistant

**Project:** Forward Deployed Engineer Take-Home Assignment | Oogway Labs  
**Repository:** [https://github.com/mkpg/lenny-growth-assistant](https://github.com/mkpg/lenny-growth-assistant)  
**Status:** Verified Against Repository Implementation  

---

## 1. System Overview & Component Boundaries

The **Lenny Growth Assistant** is architected as a modular RAG and agent orchestration platform. The architecture separates concerns between a FastAPI REST backend, a PostgreSQL persistence layer with pgvector for semantic search, a stateless Pi Coding Agent subprocess integration, and a single-page client interface.

```
+-----------------------------------------------------------------------------------------+
|                                    CLIENT APPLICATION                                   |
|  - HTML5, Vanilla CSS, Modern JavaScript (Fetch API, DOM Events, marked.js)             |
|  - In-App Artifact Viewer (Sandboxed Iframe with CSP & Markdown Formatted Viewport)     |
|  - Real-Time Model/Provider Selectors & Header Artifacts Counter Button                 |
+--------------------------------------------+--------------------------------------------+
                                             | HTTP REST (JSON)
                                             v
+-----------------------------------------------------------------------------------------+
|                                    FASTAPI BACKEND API                                  |
|                                                                                         |
|  +---------------------+   +---------------------+   +-------------------------------+  |
|  | /health & /ready    |   | /api/v1/chat        |   | /api/v1/artifacts/*           |  |
|  | Diagnostic Probes   |   | Chat & Sessions     |   | Library, Detail, Download     |  |
|  +---------------------+   +----------+----------+   +---------------+---------------+  |
|                                       |                              |                  |
|                                       v                              v                  |
|  +-----------------------------------------------------------------------------------+  |
|  |                                  EVIDENCE GATE                                    |  |
|  |  - JSON Schema Parsing (evidence_state, source_id, quote)                         |  |
|  |  - Substring Verification: Check quote presence in retrieved chunk text          |  |
|  +------------------------------------+----------------------------------------------+  |
|                                       |                                                 |
|                    +------------------+------------------+                              |
|                    v                                     v                              |
|  +------------------------------------+   +------------------------------------------+  |
|  |       RETRIEVAL ENGINE (RAG)       |   |       PI AGENT SUBPROCESS RPC            |  |
|  |  - app/retrieval.py                |   |  - app/agent.py                          |  |
|  |  - Vector query embedding via      |   |  - Portable Discovery (PI_CMD_PATH)      |  |
|  |    Ollama nomic-embed-text         |   |  - Exec: pi --mode rpc --exclude-tools * |  |
|  |  - Cosine distance ranking (<->)   |   |  - Providers: Ollama Local, Gemini Cloud |  |
|  +-----------------+------------------+   +-------------------+----------------------+  |
+--------------------|------------------------------------------|-------------------------+
                     |                                          |
                     v                                          v
+---------------------------------------+  +----------------------------------------------+
|     POSTGRESQL + PGVECTOR (Neon)      |  |             LLM INFERENCE ENGINES            |
|  - sessions & messages tables         |  |                                              |
|  - transcript_chunks table            |  |  [Local Ollama]         [Cloud Providers]    |
|    (vector(768) + HNSW index)         |  |  - qwen2.5:3b           - gemini-2.5-flash   |
|  - artifacts table                    |  |  - qwen3:4b             - gemini-pro         |
|    (id, session_id, type, content)    |  |  - nomic-embed-text                          |
+---------------------------------------+  +----------------------------------------------+
```

---

## 2. Database Schema & Data Models

Database persistence is managed via SQLAlchemy ORM connecting to PostgreSQL with the `vector` extension enabled.

```
+-------------------+           +-------------------+           +-----------------------+
|     sessions      | 1       * |     messages      |           |   transcript_chunks   |
+-------------------+-----------+-------------------+           +-----------------------+
| id (UUID, PK)     |           | id (UUID, PK)     |           | id (Int, PK)          |
| created_at (Date) |           | session_id (FK)   |           | episode_title (String)|
+---------+---------+           | role (String)     |           | url (String)          |
          |                     | content (Text)    |           | speaker (String)      |
          | 1                   | created_at (Date) |           | chunk_index (Int)     |
          |                     +-------------------+           | content (Text)        |
          | *                                                   | embedding (vector(768)|
+---------+---------+                                           +-----------------------+
|     artifacts     |
+-------------------+
| id (UUID, PK)     |
| session_id (FK)   |
| message_id (FK)   |
| title (String)    |
| artifact_type(Str)|  <-- "html" or "markdown"
| content (Text)    |
| created_at (Date) |
+-------------------+
```

### Table Specifications:
1. **`sessions`:**
   - `id`: `UUID` (Primary Key, default `uuid4`).
   - `created_at`: `DateTime` with timezone.
2. **`messages`:**
   - `id`: `UUID` (Primary Key).
   - `session_id`: `UUID` (Foreign Key referencing `sessions.id`, indexed).
   - `role`: `VARCHAR(20)` (`"user"` or `"assistant"`).
   - `content`: `TEXT` (Message body).
   - `created_at`: `DateTime`.
3. **`transcript_chunks`:**
   - `id`: `INTEGER` (Primary Key, auto-increment).
   - `episode_title`: `VARCHAR(255)`.
   - `url`: `VARCHAR(512)` (Source podcast URL).
   - `speaker`: `VARCHAR(100)` (Guest / host name).
   - `chunk_index`: `INTEGER`.
   - `content`: `TEXT` (Transcript chunk text).
   - `embedding`: `Vector(768)` (pgvector 768-dimensional float array).
4. **`artifacts`:**
   - `id`: `UUID` (Primary Key).
   - `session_id`: `UUID` (Foreign Key referencing `sessions.id`, indexed).
   - `message_id`: `UUID` (Foreign Key referencing `messages.id`, nullable).
   - `title`: `VARCHAR(255)` (Artifact title).
   - `artifact_type`: `VARCHAR(50)` (`"html"` or `"markdown"`).
   - `content`: `TEXT` (Raw HTML or Markdown content).
   - `created_at`: `DateTime`.

---

## 3. REST API Contract & Route Catalog

Routes are versioned and validated via Pydantic schemas in `app/schemas.py`:

### 3.1 `GET /health`
- **Purpose:** Liveness probe.
- **Response:** `200 OK` $\rightarrow$ `{"status": "ok", "env": "development"}`

### 3.2 `GET /ready`
- **Purpose:** Readiness probe verifying database connectivity and `vector` extension.
- **Response:** `200 OK` $\rightarrow$ `{"status": "ready", "database": "connected", "pgvector": "installed"}`
- **Error Response:** `503 Service Unavailable` if database check fails.

### 3.3 `POST /api/v1/chat`
- **Purpose:** Conversational chat and artifact generation pipeline.
- **Request Body:**
  ```json
  {
    "question": "What is Adam Fishman's advice on growth teams?",
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "provider": "ollama",
    "model": "qwen2.5:3b"
  }
  ```
- **Response Body:** `200 OK`
  ```json
  {
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "response_type": "grounded_answer",
    "answer": "According to Adam Fishman...",
    "artifact": "<!DOCTYPE html>...",
    "artifact_type": "html",
    "artifact_id": "7b12c842-1234-5678-90ab-cdef12345678",
    "artifact_title": "Growth Team Activation Plan",
    "citations": [
      {
        "source_id": "Adam Fishman on Growth",
        "speaker": "Adam Fishman",
        "quote": "Onboarding is the foundation of retention."
      }
    ]
  }
  ```

### 3.4 `GET /api/v1/sessions/{session_id}/artifacts`
- **Purpose:** Lists all artifacts generated within the specified session.
- **Response:** `200 OK` $\rightarrow$ `List[ArtifactSummary]` (`id`, `session_id`, `title`, `artifact_type`, `created_at`).

### 3.5 `GET /api/v1/artifacts/{artifact_id}`
- **Purpose:** Retrieves full artifact content.
- **Query Parameter:** `session_id` (optional, for session boundary validation).
- **Security Check:** If `session_id` is provided and does not match the artifact's owner, returns HTTP `403 Forbidden`.

### 3.6 `GET /api/v1/artifacts/{artifact_id}/download`
- **Purpose:** Directly downloads raw artifact with `Content-Disposition` attachment headers.
- **Headers:**
  - Markdown: `Content-Type: text/markdown; charset=utf-8`, `Content-Disposition: attachment; filename="title.md"`
  - HTML: `Content-Type: text/html; charset=utf-8`, `Content-Disposition: attachment; filename="title.html"`

---

## 4. Ingestion & Retrieval Pipeline (RAG)

### 4.1 Ingestion Flow (`scripts/ingest.py`)
1. **Document Loading:** Reads markdown transcripts from `data/transcripts/`.
2. **Semantic Chunking:** Text is split into overlapping chunks (~400–600 tokens) while preserving speaker identifiers.
3. **Embedding Generation:** Chunks are sent to local Ollama via `POST http://localhost:11434/api/embeddings` using `nomic-embed-text` (generating 768-dimensional dense vectors).
4. **Vector Storage:** Chunks and embeddings are inserted into the `transcript_chunks` table in PostgreSQL.
5. **Corpus Scope:** The current database snapshot used during development contains 3 podcast episodes (~178 chunks).

### 4.2 Retrieval Flow (`app/retrieval.py`)
1. The user query is embedded on-the-fly via `nomic-embed-text`.
2. Similarity search runs in PostgreSQL using the pgvector cosine distance operator (`<->`):
   ```sql
   SELECT id, episode_title, speaker, content, (embedding <-> :q_vec) AS distance
   FROM transcript_chunks
   WHERE (embedding <-> :q_vec) < 0.45
   ORDER BY distance ASC
   LIMIT 3;
   ```
3. Chunks with cosine distance $< 0.45$ (equivalent to cosine similarity $> 0.55$) are assembled into prompt context blocks.

---

## 5. Agent Subprocess RPC Integration

Instead of binding to heavyweight, provider-specific SDKs, the agent integrates with **Pi Coding Agent** in **stateless RPC mode**.

### 5.1 Portable CLI Discovery
To ensure portability across developer workstations:
```python
pi_path = settings.pi_cmd_path or shutil.which("pi") or "pi"
```
The application checks the `.env` variable `PI_CMD_PATH` first, falling back to system `PATH` discovery.

### 5.2 Process Execution & Tool Exclusion
The agent process is launched as a subprocess:
```python
process = subprocess.Popen(
    [
        pi_cmd_path,
        "--mode", "rpc",
        "--no-session",
        "--provider", provider,
        "--model", model,
        "--exclude-tools", "*"
    ],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
```

#### Why `--exclude-tools *` Was Added:
By default, the Pi Coding Agent exposes built-in file-manipulation tools (`write`, `edit`, `bash`) in the LLM tool schema. When prompts included action verbs like *"Write me an essay..."* or *"Create an HTML file..."*, the model attempted to call tools rather than outputting text. By passing `--exclude-tools *`, the agent is stripped of filesystem tool schemas and operates strictly as a conversational completion engine.

---

## 6. Evidence Gate & Citation Verification

To check factual citations without relying on secondary LLM calls, `app/main.py` implements an **Evidence Gate**:

1. **Structured Agent Prompt:** The system instructs the agent to return a JSON payload with fields: `evidence_state`, `source_id`, `quote`, and `answer`.
2. **Evidence Evaluation:**
   - If `evidence_state == "insufficient"`, the assistant returns a refusal acknowledging that the podcast transcripts do not contain the requested information.
   - If `evidence_state == "sufficient"`, the backend extracts `quote` and matches it against retrieved transcript chunks.
3. **Substring Verification:**
   ```python
   # Verifies exact quote presence in chunk text
   quote_found = any(quote.lower() in chunk.content.lower() for chunk in retrieved_chunks)
   ```
4. **Important Boundary & Limitation:**
   - **What it guarantees:** If `quote_found` is true, the quoted text physically exists within the retrieved transcript chunk.
   - **What it does not guarantee:** Verifying a quote does **not** prove that every statement, interpretation, or surrounding claim in the generated answer is semantically grounded. Models can still misinterpret verified quotes or generate unsupported inferences.

---

## 7. Security Controls & Sandbox Architecture

### 7.1 HTML Rendering Sandbox
When rendering user- or model-generated HTML/CSS:
1. **Iframe Isolation:** The browser creates an `<iframe>` configured with:
   ```html
   <iframe sandbox="allow-scripts" id="artifact-iframe"></iframe>
   ```
2. **Omission of `allow-same-origin`:** `allow-same-origin` is intentionally omitted. This isolates the iframe from the parent window's origin. Scripts inside the artifact cannot access:
   - `window.parent` or parent DOM nodes.
   - Parent cookies, `localStorage`, or `sessionStorage`.
   - Authenticated parent application API calls.
3. **Content Security Policy (CSP):** The iframe content is loaded via a dynamic Blob URL containing a CSP meta tag:
   ```html
   <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data: https:; font-src data: https:;">
   ```
4. **Sandbox Limitations:**
   - `allow-scripts` permits JavaScript execution inside the iframe. While parent data is isolated, security relies on standard browser sandbox enforcement.
   - Complex external assets or remote scripts are restricted by the CSP, but client-side DOM manipulation inside the iframe is permitted.

### 7.2 Session Isolation
The Artifact Library enforces session boundaries:
- Each artifact record is foreign-keyed to `sessions.id`.
- Retrieval (`/api/v1/artifacts/{id}`) and download (`/api/v1/artifacts/{id}/download`) verify that `artifact.session_id == request.session_id`.
- Mismatched session access attempts return HTTP `403 Forbidden`.
