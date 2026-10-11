# The Lenny Growth Assistant

A full-stack RAG (Retrieval-Augmented Generation) application designed to assist users with product, growth, and management questions using insights from *Lenny's Podcast*.

This project was built as an assignment for the Oogway Labs Forward-Deployed Engineer role.

## Features
- **Retrieval-Augmented Generation (RAG)**: Uses local vector embeddings (`nomic-embed-text`) stored in Neon PostgreSQL via `pgvector` to ground agent responses in actual podcast transcripts.
- **Strict Evidence Grounding**: The assistant verifies claims directly against retrieved chunks via a `source_id` mapping, strictly dropping unrelated citations to prevent hallucination and citation laundering.
- **Adversarial Resistance**: System instructions are hardened against prompt injections and instruction overrides, ensuring reliable conversational flow.
- **Robust Artifact Rendering**: Dynamically generates full HTML documents securely injected into a sandboxed UI iframe for safe viewing, driven by strict JSON schema types.
- **Pi Coding Agent RPC**: Leverages the local Pi Coding Agent installation in headless RPC mode for inference.
- **Provider Flexibility**: Supports both local LLMs via Ollama (e.g. `qwen2.5:3b`) and cloud APIs (e.g. Google Gemini) through the Pi Agent.
- **Isolated Sessions**: Conversation histories are persisted in PostgreSQL and properly scoped per session.
- **Deduplicated Citations**: The frontend displays transparent UI citations linking directly to YouTube episodes.
- **Asynchronous Robustness**: Agent communication is handled via non-blocking, asynchronous thread queues to prevent deadlocks and enforce timeouts.

## Limitations & Current Sample Corpus
*   **Sample Corpus Only**: The current database contains **3 transcript episodes** (approx. 178 chunked segments). It does not contain the entirety of Lenny's Podcast or Newsletter.
*   **Static Ingestion**: Transcripts were ingested via a static test script. Automatic periodic ingestion/refresh is not currently implemented.

---

## Getting Started (Fresh Clone)

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) (If using local inference)
- Neon PostgreSQL database with `pgvector` enabled

### 1. Repository Setup
Clone the repository and install dependencies:
```bash
git clone https://github.com/mkpg/lenny-growth-assistant.git
cd lenny-growth-assistant
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate # Mac/Linux
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy the `.env.example` file to create your own `.env` file:
```bash
cp .env.example .env
```
Inside `.env`, provide your actual Neon PostgreSQL connection string:
```env
DATABASE_URL=postgresql://user:password@ep-example.region.aws.neon.tech/dbname?sslmode=require
```

### 3. Database Migration
Ensure your Neon database has the `vector` extension enabled. Then, run Alembic to create the schema:
```bash
alembic upgrade head
```

### 4. Ollama Installation & Setup (Local LLM)
If you wish to run the app using local models to save on cloud API costs:
1. Install [Ollama](https://ollama.com/).
2. Pull the required models:
```bash
ollama run qwen2.5:3b
ollama pull nomic-embed-text
```

*(Note: The embedding model `nomic-embed-text` is strictly required for the RAG chunk ingestion).*

### 5. Running the Application
Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```
The frontend will be available at `http://127.0.0.1:8000`.

---

## Troubleshooting

- **Agent Timeout / Unresponsive**: Ensure the Pi CLI is properly installed and accessible. If you see `Pi process exited prematurely`, check the terminal for backend exceptions.
- **Database Connection Error**: Verify your Neon `DATABASE_URL` is correct and that your IP is whitelisted (or use a compute endpoint).
- **No Citations / Empty Answers**: Ensure you have ingested the sample transcripts into the database. Run `python scripts/ingest_test.py` (if available) to populate the initial corpus.
