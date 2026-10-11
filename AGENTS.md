# Oogway Labs — Lenny Growth Assistant: Agent Instructions

## Mission
Build the smallest complete, reliable, testable implementation of the Oogway Labs Forward-Deployed Engineer take-home assignment: **The Lenny Growth Assistant**. The official deadline is 12 October 2026 EOD. The working target is to finish by 10 October; 11 October is unavailable to the user.

## How to work with the human
- The human is learning and must understand important decisions before they are implemented. Do not silently make major product or architecture decisions.
- Work in small, reviewable steps. Explain the goal, files to change, and trade-offs before a meaningful implementation step; then implement and report exact results.
- Do not scaffold the entire application in one giant operation.
- When a choice materially affects architecture, cost, security, deadline, or required deliverables, pause and present the options with a recommendation.
- Prefer working vertical slices over disconnected scaffolding.
- Do not claim a feature, test, integration, metric, or security property works unless you ran a relevant check and observed the result.
- Keep a concise decision log. Record assumptions, decisions, rejected options, and why.
- Capture coding-agent sessions, failures, and corrections in `agent-transcripts/`. Never include secrets or personal tokens.
- The human uses Windows 11. Prefer Windows-friendly commands and clearly label PowerShell commands. Docker Desktop and host-running Ollama may be used if installed.

## Assignment requirements that must not be lost
- FastAPI backend.
- Agent layer using **Anthropic Claude Agent SDK or Pi Coding Agent**.
- Persistent PostgreSQL storage for sessions, messages, timestamps, and user metadata.
- Local Ollama model must work for the demo.
- At least one cloud LLM option; provider selection must be visible and configurable.
- Transcript knowledge base with traceable sources.
- Grounded Q&A, follow-up questions, independent sessions, and explicit abstention when evidence is insufficient.
- Dedicated Ship 30 for 30 writing skill; approximately 1,250 words, hook, narrative progression, scannable headings/bullets, useful takeaway, transcript-grounded claims.
- Markdown and complete HTML/CSS artifact generation with an in-app viewer.
- Safe artifact rendering; generated HTML is untrusted.
- Reproducible startup, `.env.example`, structured logs, graceful failure behavior, tests, and handoff docs.
- Eight deliverables: public repository, README, PRD, `design.md`, `architecture.md`, agent transcripts, tests/manual test plan, 2–3 minute camera-on YouTube demo.

## Architecture direction — decisions are provisional until validated
- Frontend: vanilla HTML, CSS, and JavaScript to minimize integration overhead.
- Backend: FastAPI.
- Database: PostgreSQL with pgvector; use PostgreSQL full-text search plus vector search only if a small baseline proves the added work is feasible.
- Local inference: Ollama; verify installed models and hardware fit before selecting a model. Do not assume a model is already installed.
- Embeddings: test `nomic-embed-text` through Ollama, subject to availability and successful smoke test.
- Agent: Pi Coding Agent is the preferred candidate, conditional on a short integration smoke test. It is TypeScript-based, so validate the FastAPI boundary immediately. If it consumes too much time, use the assignment-permitted Anthropic Claude Agent SDK for the cloud agent and a clear, explicit Ollama adapter for local mode. Document the trade-off and verify the result.
- Use a bounded agent/workflow design, not unrestricted autonomy or unnecessary multi-agent orchestration.
- Docker Compose should start PostgreSQL, backend, and frontend. Ollama may run on the host and must be documented.
- Do not silently fall back between providers. Show the selected provider and make failures clear.

## Engineering rules
- Inspect the existing repository and files before editing. Preserve useful work.
- Never overwrite or delete user work without explaining the impact and obtaining approval.
- Keep secrets out of source control. `.env` is ignored; `.env.example` contains placeholders only.
- Validate request/response schemas. Use clear HTTP errors and a health endpoint.
- Keep modules small and responsibilities separated.
- Add migrations/schema initialization reproducibly; avoid relying on undocumented manual database steps.
- Add timeouts and controlled error handling for database/model calls.
- Store source metadata with every transcript chunk and preserve it through retrieval and citations.
- Do not fabricate transcript quotes, episode names, guests, timestamps, or citations.
- Never treat previous model output as source evidence.
- Use parameterized SQL/ORM queries.
- Treat transcript content and model-generated content as untrusted input.
- HTML artifacts must be isolated in a sandboxed iframe without `allow-same-origin`; use a restrictive CSP and sanitize where appropriate. Markdown must be rendered safely; use DOMPurify if rendering HTML in the browser.
- Do not expose application secrets, privileged functions, or trusted UI context to artifacts.
- Avoid adding authentication, reranking, auto-refresh, streaming polish, or other scope expansions unless required to fix a real blocker.
- Do not install extra frameworks or dependencies without explaining why they are needed.
- Prefer meaningful tests for critical paths over a large superficial test suite.

## Definition of done for every task
1. State what changed and why.
2. Run relevant tests or checks.
3. Report exact commands and outcomes; identify anything not tested.
4. Update the applicable docs and decision log.
5. Record the agent session in `agent-transcripts/`.
6. Leave the repository in a runnable, coherent state.

## First action
Do not start by generating the entire app. Read `PROJECT.md`, `docs/PRD.md`, `docs/architecture.md`, and `docs/implementation_plan.md`. Then perform the **short feasibility gate** in `.agents/skills/feasibility-gate/SKILL.md`: inspect the transcript source and run bounded smoke tests for Ollama/embeddings and the Pi integration. Time-box it, report findings, and ask the human to approve the implementation baseline before large changes.
