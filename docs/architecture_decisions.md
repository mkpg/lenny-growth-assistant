# Architecture Decisions

| Component | Selected Option | Reason | Verification Status | Remaining Risks |
| --- | --- | --- | --- | --- |
| **Database** | Neon PostgreSQL + pgvector | Managed PostgreSQL simplifies persistence and semantic search without needing a separate vector DB or local Docker DB container. | BLOCKED: No credentials provided yet. | If `pgvector` isn't enabled on the specific Neon project, retrieval will fail. |
| **Backend** | FastAPI (Python) | High performance, excellent typing/Pydantic support, and aligns with Python ecosystem for AI/Agent tasks. | PASSED: Skeleton runs and passes health check. | Need to structure project correctly to avoid circular dependencies as routes grow. |
| **Local LLM** | Ollama | Mandatory requirement for local demo execution. | BLOCKED: Ollama CLI not found on host. | Local hardware constraints (4 GB VRAM) may limit model choice and speed. |
| **Cloud LLM** | Anthropic Claude | Allowed by the assignment; good alternative while Ollama is absent. | NOT TESTED: No API key provided yet. | API costs and latency. |
| **Agent Framework** | Anthropic Claude Agent SDK | Avoids TypeScript/Python integration overhead present in Pi Coding Agent. | NOT TESTED: Pending API key and schema implementation. | Tool calling constraints and error handling. |
| **Ingestion Corpus** | Github `lennys-podcast-transcripts` | Accessible, well-structured repository containing 269 podcast transcripts with rich metadata. | PASSED: Repo cloned and inspected successfully. | Does not contain newsletter content (needs separate sourcing). |
