# Decision Log

Update this file when a meaningful decision is made. Record date, context, options, decision, rationale, validation, and consequences.

## D-001 — Product scope
- **Decision:** source-grounded transcript research, follow-ups, essay generation and artifact viewing form the core user journey.
- **Rationale:** these capabilities connect the assignment's requirements into one coherent workflow.
- **Status:** initial decision; validate in implementation.

## D-002 — Primary user
- **Decision:** use product managers, founders and growth practitioners as the initial persona.
- **Rationale:** the assignment is centered on product and growth questions.
- **Caveat:** hypothesis, not validated customer demand.

## D-003 — Frontend
- **Decision:** start with vanilla HTML/CSS/JavaScript.
- **Rationale:** reduce setup and integration cost under the deadline.
- **Revisit only if:** a real requirement makes vanilla implementation materially slower.

## D-004 — Data Store

- **Decision:** Use Neon PostgreSQL as the primary managed database. Evaluate and enable the `pgvector` extension for semantic retrieval, alongside PostgreSQL full-text search where useful.
- **Rationale:** Neon provides managed PostgreSQL for persistent application data. A single database can store chat sessions, messages, transcript metadata, transcript chunks, and embeddings without introducing a separate vector database.
- **Validation required:** Verify Neon connectivity, `pgvector` extension availability, embedding dimensions, vector similarity query behavior, full-text search behavior, and reproducible schema initialization.
- **Implementation constraint:** Do not provision a separate local PostgreSQL container. Configure Neon through environment variables and keep credentials out of source control.
- **Status:** Decision selected; implementation and validation pending.

## D-005 — Retrieval
- **Decision:** use source-preserving chunking and start with a simple retrieval baseline; add hybrid ranking only if feasible and testable.
- **Rationale:** evidence traceability is mandatory; complexity should be justified by evaluation.

## D-006 — Agent framework
- **Decision:** prefer Pi Coding Agent subject to a time-boxed integration smoke test.
- **Fallback:** assignment-permitted Anthropic Claude Agent SDK for cloud mode plus explicit Ollama adapter for local mode.
- **Validation required:** demonstrate an actual agent layer, tool/workflow invocation, and selected provider behavior.

## D-007 — Deliberate exclusions
- **Decision:** no authentication, transcript auto-refresh, advanced reranking or streaming polish.
- **Rationale:** scope discipline and deadline.
- **Caveat:** these exclusions do not permit dropping other mandatory assignment requirements.

## D-008 — Artifact security
- **Decision:** Markdown sanitization and isolated sandboxed iframe for HTML; no `allow-same-origin`; restrictive CSP.
- **Validation required:** inspect actual DOM/iframe implementation and test hostile markup.

## D-009 — Feasibility Gate Blockers
- **Decision:** Halt further implementation until transcript repository and local/cloud LLM keys/binaries are provided.
- **Rationale:** Ollama is not installed locally and no transcript data is present in the workspace, making it impossible to pass the feasibility gate for testing RAG and local inference.
- **Status:** Awaiting human approval/data.
