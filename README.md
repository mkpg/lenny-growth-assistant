# The Lenny Growth Assistant

**Forward Deployed Engineer Take-Home Assignment | Oogway Labs**  
**Repository:** [https://github.com/mkpg/lenny-growth-assistant](https://github.com/mkpg/lenny-growth-assistant)  

 
---

## 1. Executive Summary & Engagement Scenario

The **Lenny Growth Assistant** is a full-stack, conversational AI web application built to address a common pain point for product managers, growth teams, and startup founders: extracting verifiable, actionable insights from [Lenny's Podcast transcripts](https://github.com/ChatPRD/lennys-podcast-transcripts) without having to manually read hundreds of transcript files or rely on ungrounded general-purpose chatbots that invent quotations and metrics.

Built as a Forward Deployed Engineer (FDE) engagement, the system combines:
1. **Source-Grounded Question Answering:** Semantic vector retrieval across podcast transcripts backed by an Evidence Gate that validates quotation substrings against retrieved transcript text.
2. **Configurable Model Routing:** Toggle between local inference via **Ollama (Local)** (mandatory for the offline evaluation demo) and configured cloud providers (Gemini / Anthropic) through the Pi Coding Agent RPC subprocess integration.
3. **Dedicated Content Skill (Ship 30 for 30):** Built-in skill generating structured ~1,250-word essays with narrative hooks, skimmable headings, and grounded takeaways.
4. **Dual-Format In-App Artifact Viewer:** Native in-app viewer (modeled on Claude Artifacts) that renders formatted Markdown documents and interactive HTML/CSS components with iframe sandboxing.
5. **Persistent Artifact Library:** Database-backed artifact storage scoped to user sessions with deduplication, session boundary enforcement, and direct `.md` / `.html` downloads.

---

## 2. High-Level Architecture

```
+-----------------------------------------------------------------------------------+
|                                Browser Frontend                                   |
|   - Vanilla JS / CSS (Responsive Layout, Modern Typography)                       |
|   - Real-time Chat Stream & Expandable Source Citation Cards                      |
|   - Header Provider/Model Selectors & Artifacts Counter Button                    |
|   - In-App Artifact Viewer Modal (Sandboxed HTML Iframe & Markdown marked.js)     |
|   - History Drawer (Conversations & Saved Artifacts)                              |
+----------------------------------------+------------------------------------------+
                                         | HTTP REST API
                                         v
+-----------------------------------------------------------------------------------+
|                                FastAPI Backend                                    |
|   - Health & Readiness Probes (/health, /ready)                                   |
|   - Chat Endpoint (/api/v1/chat) with Session & History Management                |
|   - Evidence Gate (Source ID & Quote substring verification)                      |
|   - Artifact Library Endpoints (List, Retrieve, Raw Attachment Download)           |
+--------------------+-------------------------------------+------------------------+
                     |                                     |
                     v                                     v
+--------------------------------------+  +-----------------------------------------+
|   PostgreSQL + pgvector (Neon)       |  |     Pi Coding Agent RPC Engine          |
|  - sessions & messages tables        |  |  - Portable Discovery (PI_CMD_PATH)     |
|  - transcript_chunks table           |  |  - Subprocess with --exclude-tools *    |
|    (768-dim embeddings, HNSW index)  |  |  - Providers:                           |
|  - artifacts table                   |  |    * Ollama Local (qwen2.5:3b/qwen3:4b) |
|    (HTML & Markdown persistence)     |  |    * Cloud (gemini-2.5-flash / Claude)  |
+--------------------------------------+  +-----------------------------------------+
                     ^
                     | Vector Embeddings
+--------------------+-----------------+
|            Ollama Local Service      |
|  - nomic-embed-text (Embeddings)     |
|  - qwen2.5:3b (Chat & Synthesis)     |
+--------------------------------------+
```

---

## 3. Assignment Deliverables Status

Status of the eight required deliverables specified in Section 6 of the assignment brief:

| # | Deliverable | Location in Submission | Status | Description |
|---|---|---|---|---|
| **1** | **Public GitHub Repository** | `https://github.com/mkpg/lenny-growth-assistant` | Ready for Push | Complete source code, modular structure, `.env.example` provided, zero committed secrets. |
| **2** | **README.md** | [`./README.md`](./README.md) | Completed | Setup, architecture, configuration, endpoints, test commands, and troubleshooting. |
| **3** | **PRD.md** | [`./PRD.md`](./PRD.md) | Completed | Discovery brief, user personas, success metrics, assumptions, scope choices, and risks. |
| **4** | **design.md** | [`./design.md`](./design.md) | Completed | UI/UX hierarchy, DOM structure, dual-format viewer, state matrix, and accessibility targets. |
| **5** | **architecture.md** | [`./architecture.md`](./architecture.md) | Completed | DB schema, API contracts, Pi RPC mechanics, Evidence Gate, and sandbox boundaries. |
| **6** | **Agent Transcripts** | [`agent-transcripts/`](./agent-transcripts/) | Completed | Dedicated folder containing genuine session logs and bug diagnoses (e.g., Pi CLI tool exclusion). |
| **7** | **Automated Tests & UI Test Plan** | [`tests/`](./tests/) | Completed | 116 passing tests (`pytest`) + manual UI verification checklist. |
| **8** | **Camera-On Demo Video** | YouTube | Completed | [Watch on YouTube](https://youtu.be/Z4ag47-Lv54) — Covers problem framing, local Ollama demo, artifact viewer, and technical trade-offs. |

---

## 4. Prerequisites

- **Python:** Version 3.10, 3.11, or 3.12.
- **Node.js & Pi CLI:** Node.js 18+ with Pi Coding Agent installed (`npm install -g @withcontext/pi`) or configured via `PI_CMD_PATH`.
- **Database:** PostgreSQL 15+ with the `vector` (pgvector) extension enabled (tested on Neon PostgreSQL).
- **Ollama (for local model evaluation):**
  - Chat Model: `ollama pull qwen2.5:3b`
  - Embedding Model: `ollama pull nomic-embed-text`
- **Cloud API Keys (Optional):** `GEMINI_API_KEY` or `ANTHROPIC_API_KEY` if exercising cloud providers.

---

## 5. Setup & Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/mkpg/lenny-growth-assistant.git
cd lenny-growth-assistant
```

### Step 2: Create and Activate Virtual Environment
**Windows PowerShell:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate `.env` with your settings based on the repository's `.env.example`:
```env
# Database Connections (Neon PostgreSQL with pgvector)
DATABASE_URL=postgresql://user:password@ep-cool-db-123456.us-east-2.aws.neon.tech/dbname?sslmode=require
DATABASE_URL_DIRECT=postgresql://user:password@ep-cool-db-123456.us-east-2.aws.neon.tech/dbname?sslmode=require

# Application Environment & Logging
APP_ENV=development
LOG_LEVEL=INFO

# Optional: Cloud Provider Keys (If exercising cloud LLM)
ANTHROPIC_API_KEY=your_anthropic_key_here
GEMINI_API_KEY=your_gemini_key_here

# Optional: Custom Pi CLI Path (Auto-discovered via PATH if omitted)
# PI_CMD_PATH=C:\Users\Admin\AppData\Local\Author Software\nvm\installs\v22.20.0\pi.cmd
```

### Step 4: Run Database Migrations
Apply Alembic migrations to create tables (`sessions`, `messages`, `transcript_chunks`, `artifacts`):
```bash
alembic upgrade head
```

### Step 5: Pull Ollama Models & Start Ollama
Ensure the Ollama service is running:
```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

### Step 6: Ingest Transcript Knowledge Base (If using a fresh database)
If you are configuring a fresh local database rather than connecting to the pre-seeded development instance, ingest the benchmark podcast episodes (~178 semantic chunks) by running:
```bash
python scripts/ingest_sample.py
```
This script parses the markdown transcripts, chunks the text while preserving speaker metadata, generates 768-dimensional vector embeddings using Ollama's `nomic-embed-text`, and indexes them in PostgreSQL with pgvector.

### Step 7: Start the Application
Launch the FastAPI server:
```bash
python -m uvicorn app.main:app --reload
```
Access points:
- **Web Interface:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Liveness Probe:** `http://127.0.0.1:8000/health`
- **Readiness Probe (DB + pgvector):** `http://127.0.0.1:8000/ready`

---

## 6. REST API Reference

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/health` | Liveness check returning application status and environment. | `200` |
| `GET` | `/ready` | Readiness check verifying PostgreSQL connection and `vector` extension. | `200`, `503` |
| `POST` | `/api/v1/chat` | Main conversational RAG endpoint; accepts question, session ID, provider, and model. | `200`, `400`, `404`, `500` |
| `GET` | `/api/v1/sessions/{id}/artifacts` | Lists saved artifacts for the specified session. | `200`, `404` |
| `GET` | `/api/v1/artifacts/{id}` | Retrieves full artifact content; supports `?session_id=` ownership check. | `200`, `403`, `404` |
| `GET` | `/api/v1/artifacts/{id}/download` | Direct file download with `Content-Disposition` header (`.html` or `.md`). | `200`, `403`, `404` |

---

## 7. Automated Test Suite & Results

The test suite covers API routes, model routing, pgvector retrieval, Evidence Gate quotation matching, Ship 30 for 30 skill formatting, and the Artifact Library persistence layer.

### Command
```bash
python -m pytest -q
```

### Verified Test Run Result
```text
........................................................................ [ 62%]
............................................                             [100%]
116 passed, 1 warning in 73.72s (0:01:13)
```
- **Verified on:** 12 October 2026.
- **Scope:** 116 tests across 11 test modules (`test_api_endpoints.py`, `test_artifact_library.py`, `test_code_requirement_fixes.py`, `test_real_db_chat.py`, `test_security.py`, etc.).
- **Note on Scope:** Automated tests verify API contracts, database persistence, and logic checks. They do not guarantee that every generated answer in live interactive usage will be free of hallucinations.

---

## 8. Manual UI Verification Checklist

- [ ] **Local Startup:** App starts with `uvicorn app.main:app --reload` without errors.
- [ ] **Readiness Check:** `http://127.0.0.1:8000/ready` returns `{"status":"ready","database":"connected","pgvector":"installed"}`.
- [ ] **Local Ollama Execution:** Select **Ollama (Local)** -> `qwen2.5:3b`. Submit a growth question. Answer returns with source references.
- [ ] **Evidence Refusal:** Submit an unsupported question (e.g., an unmentioned financial metric). The assistant acknowledges the evidence gap rather than inventing numbers.
- [ ] **Ship 30 for 30 Essay Skill:** Ask for a Ship 30 for 30 essay. The assistant generates a structured essay with hook, headings, bold emphasis, and transcript citations.
- [ ] **HTML Artifact Workflow:** Ask for an HTML component. A **Preview HTML Artifact** button appears. Clicking it opens the viewer rendering inside the sandbox.
- [ ] **Markdown Artifact Workflow:** Ask for a Markdown checklist. A **Preview Markdown Artifact** button appears and renders formatted Markdown.
- [ ] **Artifact History:** The top header button updates to **Artifacts (N)**. Clicking it or opening the sidebar displays saved items.
- [ ] **Reopening & Downloads:** Reopening an artifact displays saved content without a new LLM call. Clicking **Download** downloads the `.html` or `.md` file.
- [ ] **Session Isolation:** Starting a "New Conversation" creates a new session. Attempting to access another session's artifact via the API returns `403 Forbidden`.

---

## 9. Security & Operational Boundaries

1. **HTML Rendering Sandbox:**
   - Generated HTML is rendered in an `<iframe>` configured with `sandbox="allow-scripts"`.
   - `allow-same-origin` is omitted to isolate the iframe from parent window cookies, localStorage, and DOM.
   - Served via Blob URLs with a Content Security Policy meta header:
     `default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data: https:; font-src data: https:;`
   - *Boundary Note:* `allow-scripts` permits client-side script execution within the iframe context. While parent storage and DOM are isolated, sandbox security relies on browser policy compliance and strict CSP enforcement.
2. **Subprocess Isolation:**
   - Pi CLI is invoked with `--exclude-tools *` to prevent the LLM from attempting filesystem writes or terminal execution.
3. **Session Data Boundaries:**
   - Artifact endpoints enforce session ownership checks, returning `403 Forbidden` if cross-session access is attempted.

---

## 10. Troubleshooting Guide

| Issue | Root Cause | Resolution |
|---|---|---|
| **Pi CLI hangs on prompts** | Built-in tool calling schema triggered by prompt keywords like "write" or "edit". | Ensure `app/agent.py` passes `--exclude-tools *` to `subprocess.Popen`. Verify `PI_CMD_PATH` if Pi is not in system PATH. |
| **Ollama connection refused** | Local Ollama daemon is stopped. | Run `ollama serve` or start Ollama desktop. Confirm `qwen2.5:3b` and `nomic-embed-text` are installed via `ollama list`. |
| **Database connection fails** | Missing SSL configuration or invalid credentials. | Ensure `?sslmode=require` is appended to Neon PostgreSQL URLs. |
| **Readiness check returns 503** | `vector` extension not enabled. | Execute `CREATE EXTENSION IF NOT EXISTS vector;` in your PostgreSQL database, then re-run migrations. |
| **Unsupported claims in output** | Model synthesis hallucinating details outside retrieved chunks. | Known generative limitation. Check citation cards to verify exact quoted text against the episode. |

---

## 11. Camera-On Demo Video (Recorded Walkthrough)

**Status:** Completed & Live  
**Video URL:** [https://youtu.be/Z4ag47-Lv54](https://youtu.be/Z4ag47-Lv54)  
**Format:** Camera-on split screen (Presenter + Live Web Application)

### Walkthrough Topics Covered:
- **Problem & Engagement Context:** Forward Deployed Engineer scenario for product teams needing grounded transcript research.
- **Local Ollama Demo:** Live demonstration of 100% offline local inference using Ollama (`qwen2.5:3b`) and `nomic-embed-text`, showing citation expansion and exact quote verification.
- **Ship 30 for 30 Skill & In-App Artifact Viewer:** Demonstrating a generated essay and an HTML dashboard inside the sandboxed viewer; showing header artifact count and file downloads.
- **Technical Trade-Off Discussion:** Architectural trade-off between **stateless CLI RPC subprocessing vs. native SDKs**, and why **deterministic quote substring validation** was chosen over secondary LLM-as-a-judge calls.
