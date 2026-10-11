# Requirements Traceability Checklist

This document tracks the authoritative requirements from the original assignment document (`Forward_Deployed_Engineer_Take_Home_Assignment_12_Oct_2026.docx`) against our implementation decisions and verification status.

## Backend and Agent
| ID | Requirement Summary | Source | Planned Implementation | Verification Method | Status | Evidence/Blocker |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-B1** | Backend API: FastAPI | Assignment | Build API with FastAPI. | Run endpoints locally; verify `/health`. | VERIFIED | `app/main.py` created and tested (`tests/test_main.py`). |
| **REQ-B2** | Agent framework: Pi Coding Agent or Anthropic Claude SDK | Assignment | Integrate Anthropic Claude Agent SDK for Python native integration. | Execute an agent task successfully. | NOT STARTED | Pending API key and schema setup. |
| **REQ-B3** | Session handling: independent chat context | Assignment | SQLAlchemy `Session` model; `session_id` passed via headers or payload. | Start two distinct sessions; verify context isolation. | NOT STARTED | Schema not yet defined. |
| **REQ-B4** | Persistence: PostgreSQL (convos, session IDs, timestamps, metadata) | Assignment | Neon PostgreSQL integration using SQLAlchemy. | Write to and read from the Neon database. | IN PROGRESS | Setup in `app/database.py`, but blocked on `.env` configuration. |
| **REQ-B5** | API quality: validated contracts, structured errors, health endpoints | Assignment | Pydantic models for I/O; FastAPI exception handlers; `/health` and `/ready` endpoints. | Hit `/health` and trigger validation errors in tests. | IN PROGRESS | Liveness checks passed; Pydantic inputs to be added. |

## Language-Model Configuration
| ID | Requirement Summary | Source | Planned Implementation | Verification Method | Status | Evidence/Blocker |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-L1** | Cloud LLM integration (Anthropic Claude or OpenAI) | Assignment | Anthropic Claude via Claude Agent SDK. | Test cloud generation end-to-end. | NOT STARTED | Pending `ANTHROPIC_API_KEY`. |
| **REQ-L2** | Local inference (Ollama + compatible model) for demo | Assignment | Ollama installed locally; expose config flag to toggle local/cloud. | Run offline and generate a valid response via Ollama. | BLOCKED | `ollama` CLI not installed on host. |
| **REQ-L3** | Visible provider in UI/config, fallback behavior documented | Assignment | Expose UI toggle; if cloud fails/unreachable, fallback to local Ollama if configured. | Disconnect internet/remove key and verify fallback in UI. | NOT STARTED | Frontend not yet built. |
| **REQ-L4** | Handle missing credentials, unavailable Ollama, model timeouts | Assignment | Try-except blocks handling `httpx.TimeoutException`, API errors, and Ollama connection refused. | Unit test error paths and verify structured error responses. | NOT STARTED | Waiting on agent integration. |

## Knowledge Base and Grounding
| ID | Requirement Summary | Source | Planned Implementation | Verification Method | Status | Evidence/Blocker |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-K1** | Use Lenny's Podcast / Newsletter transcript content | Assignment | Ingest `lennys-podcast-transcripts` (Markdown + YAML frontmatter). | Count transcripts in DB matches repository. | IN PROGRESS | Repo cloned to `scratch/`; Newsletter sourcing pending. |
| **REQ-K2** | Explain chunking, indexing, refreshing, and traceability | Assignment | Architecture doc details semantic chunking, `pgvector` indexing, and UUID mapping. | Review design documentation. | NOT STARTED | Need to write ingestion script first. |
| **REQ-K3** | Implement RAG / Ground answers in retrieved source material | Assignment | Use `pgvector` to retrieve chunks; inject into Claude Agent prompt. | Ask specific podcast question and verify factual answer. | NOT STARTED | Needs embedding model and database populated. |
| **REQ-K4** | Identify supporting transcripts/sources | Assignment | Return source URLs and timestamps in API response. | Check API response JSON for `sources` array. | NOT STARTED | - |
| **REQ-K5** | Acknowledge when evidence does not support an answer | Assignment | System prompt instruction + fallback tool behavior. | Ask out-of-domain question; verify graceful denial. | NOT STARTED | - |

## Ship 30 for 30 Essay Skill
| ID | Requirement Summary | Source | Planned Implementation | Verification Method | Status | Evidence/Blocker |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-S1** | Dedicated skill/tool informed by writing guide | Assignment | Create specific Claude Tool for essay generation. | Invoke tool via Agent SDK. | NOT STARTED | - |
| **REQ-S2** | ~1,250 words, hook, narrative, headings, bold emphasis | Assignment | Enforce format and length constraints in the tool's system prompt. | Generate essay and verify word count and markdown formatting. | NOT STARTED | - |
| **REQ-S3** | Specific, useful takeaway and claims grounded in KB | Assignment | Combine retrieval step with the essay generation step. | Review essay content against source facts. | NOT STARTED | - |

## Artifact Generation and Viewer
| ID | Requirement Summary | Source | Planned Implementation | Verification Method | Status | Evidence/Blocker |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-A1** | Generate Markdown and HTML/CSS artifacts from conversation | Assignment | Agent returns structured `Artifact` payloads. | API returns artifact blocks. | NOT STARTED | - |
| **REQ-A2** | Render artifacts natively in in-app Artifact Viewer | Assignment | Frontend React/Vanilla JS split pane design. | View artifact in browser. | NOT STARTED | - |
| **REQ-A3** | Treat HTML as untrusted (isolation/sanitization) | Assignment | Use `iframe` with `sandbox` attributes for isolation; DOMPurify if inline. | Attempt XSS script execution; verify it is blocked. | NOT STARTED | - |

## Deployment, Reliability, and Handoff
| ID | Requirement Summary | Source | Planned Implementation | Verification Method | Status | Evidence/Blocker |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-D1** | One-command startup (Docker Compose or equivalent) | Assignment | Create `docker-compose.yml` for UI and API (if applicable). | Run `docker-compose up` on a fresh system. | NOT STARTED | - |
| **REQ-D2** | Include safe `.env.example`, no committed secrets | Assignment | Provide template; add `.env` to `.gitignore`. | Review repo files and git history. | VERIFIED | Completed in Sprint 1. |
| **REQ-D3** | Structured logging and diagnostics for failures | Assignment | Use Python `logging` with JSON formatter or explicit contextual logging. | Inspect console logs during errors. | NOT STARTED | - |
| **REQ-D4** | Provide 8 specific submission deliverables (README, PRD, docs, tests, demo) | Assignment | Incrementally build docs folder and record demo video at the end. | Checklist review before handoff. | IN PROGRESS | PRD and Architecture being drafted. |
