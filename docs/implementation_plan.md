# Implementation Plan — Time-Boxed Vertical Slices

**Project:** The Lenny Growth Assistant — Oogway Labs Forward-Deployed Engineer Take-Home  
**Official deadline:** 12 October 2026 EOD  
**Internal target:** 10 October 2026  
**11 October:** Unavailable to the user

## Operating principles

- Optimize for a coherent, working, demonstrated system—not a checklist of unfinished components.
- Treat the original assignment document as the authority for mandatory requirements.
- Preserve existing implementation and documentation; inspect before changing.
- Do not follow the schedule mechanically when a blocker appears. Report the blocker and propose the smallest viable adjustment.
- Use **Neon PostgreSQL** as the selected database. Do not create a separate local PostgreSQL container.
- Treat local Ollama inference and at least one cloud LLM provider as required capabilities.
- Integrate either Pi Coding Agent or Anthropic Claude Agent SDK as the actual agent framework.
- Never mark work as verified merely because code or documentation exists.
- Record actual commands, observed results, failed attempts, and unresolved limitations.
- Do not install software, download large models, apply destructive migrations, or incur unexpected costs without appropriate approval.

## Gate 0 — Feasibility and requirements verification

**Time box:** 30–45 minutes. Do not build additional application features during this gate.

### Tasks

1. Read the original assignment document and existing project instructions.
2. Inspect `docs/requirements_traceability.md`, `docs/architecture.md`, `docs/decision_log.md`, `docs/feasibility_report.md`, and the previous agent transcript.
3. Inspect the real transcript repository structure, metadata, source attribution, and available podcast/newsletter coverage.
4. Check installed tools, available Ollama models, hardware constraints, and embedding-model availability.
5. Smoke-test embeddings if a suitable model is already available.
6. Investigate Pi and its local-model integration path. Compare it with the permitted Anthropic Claude Agent SDK if needed.
7. Verify the approved database decision: Neon PostgreSQL + pgvector, with PostgreSQL full-text search considered as a complementary retrieval mechanism.
8. Identify the minimum viable architecture for satisfying both the local Ollama demo and cloud-model requirement.
9. Record findings and distinguish verified facts from assumptions and blockers.

### Exit criteria

- Requirements traceability checklist reflects the original assignment.
- Final proposed stack and architecture are documented.
- Material unresolved choices are identified.
- Human approval is obtained for material architecture changes before broad implementation.

Do not block reversible skeleton work on missing external credentials, but do not claim live integrations work without testing them.

## Verification Gate — Existing implementation audit

Before connecting Neon or ingesting the full corpus, inspect any implementation already created by the coding agent.

### Required checks

- FastAPI application imports and starts.
- SQLAlchemy models import successfully.
- Alembic discovers the expected models and can produce a migration.
- Migration contents include the expected tables, vector column configuration, and necessary extension handling.
- Database configuration distinguishes pooled application connections from direct migration connections where required.
- The ingestion script parses representative real transcript files and preserves actual source metadata.
- Chunking, duplicate handling, and reruns have defined behavior.
- `.env` is ignored by Git and secrets do not appear in logs or transcripts.
- Requirements traceability statuses are supported by tests or observed demonstrations.

### Exit criteria

Every check is recorded as `PASS`, `FAIL`, `NOT TESTED`, or `BLOCKED`, with its command and observed result.

Do not apply migrations to Neon or ingest the full corpus until the configuration, migration, and representative parsing checks have passed. Missing credentials must be reported as a blocker to live verification, not as proof that the implementation is broken or working.

## Slice 1 — Runnable application skeleton

### Tasks

- Preserve and complete the existing project structure.
- Provide `.gitignore`, `.env.example`, setup instructions, and an agent transcript template.
- Create Docker Compose for the FastAPI backend and frontend if appropriate for the selected frontend.
- Do not include a PostgreSQL container; the database is Neon.
- Configure the Neon connection through environment variables.
- Implement the FastAPI application with `/health`, dependency readiness, request validation, structured errors, and basic logging.
- Create a basic frontend shell with an identifiable application layout.
- Implement database connection/session management and an initial reproducible schema or migration process.
- Keep local and cloud model configuration independent of database startup.
- Document required and optional environment variables without exposing secrets.

### Verification

- Start the application using the documented local workflow.
- Verify `/health` reports application liveness.
- Verify readiness checks actual database connectivity when credentials are available.
- Run the schema/migration process against a configured Neon project.
- If Neon credentials are unavailable, test configuration failure behavior and document the exact action needed for live verification.

### Exit criteria

The backend and basic frontend run using documented instructions. Database readiness reflects the actual dependency state. No live Neon integration is marked verified without a successful connection test.

## Slice 2 — One real RAG path

### Tasks

- Select a bounded subset of real podcast transcripts.
- Verify their metadata and source links before ingestion.
- Parse the content without inventing missing fields.
- Split transcripts into manageable chunks while retaining source attribution.
- Select and test an embedding model compatible with the intended local hardware.
- Generate and store embeddings in Neon using pgvector if the embedding test succeeds and the extension is available.
- If embeddings are blocked, do not fabricate vectors. Implement or evaluate a transparent retrieval baseline using PostgreSQL full-text search and record the limitation.
- Implement retrieval and a citation data structure that preserves episode title, guest, source URL, and available timestamps.
- Create a small manually checked retrieval dataset.
- Test one known-answer question and one question unsupported by the available evidence.

### Verification

Inspect the retrieved passages, metadata, and resulting answer. Confirm that citations correspond to actual source records and that unsupported questions are handled honestly.

### Exit criteria

One question retrieves relevant real evidence and returns correct source metadata. An unsupported-query test exists. The retrieval baseline and any limitations are documented.

## Slice 3 — Persistence and independent sessions

### Tasks

- Implement session and message tables and endpoints.
- Persist user and assistant messages with timestamps.
- Associate messages with their session.
- Keep conversation history isolated by session.
- Implement starting a new chat and retrieving prior sessions.
- Avoid logging sensitive message contents unnecessarily.

### Verification

Test creation, persistence, retrieval, follow-up context, and session isolation across at least two separate sessions.

### Exit criteria

New chats, follow-ups, and session isolation work against Neon when configured. Persistence behavior is covered by tests.

## Slice 4 — Agent framework and model selection

### Tasks

- Integrate the approved assignment-permitted agent framework: Pi Coding Agent or Anthropic Claude Agent SDK.
- Verify the framework participates in the actual workflow rather than existing only as a dependency or wrapper.
- Add controlled workflows/tools for transcript retrieval and the later essay/artifact capabilities.
- Implement local Ollama inference.
- Integrate at least one cloud provider, such as Anthropic Claude or OpenAI.
- Make provider selection visible in the UI or configuration.
- Define explicit behavior when the selected provider is unavailable.
- Do not silently switch providers.
- Keep local inference independent of cloud API credentials.

### Verification

Test:

- A real Ollama generation request.
- A cloud generation request if credentials are available.
- The selected agent-framework invocation.
- Missing cloud key.
- Ollama unavailable.
- Model timeout.
- Explicit provider selection and failure reporting.

### Exit criteria

The required agent framework is demonstrably integrated, and both local and cloud model modes are documented. Ollama is mandatory for the final demo; a cloud-only fallback does not satisfy this criterion.

## Slice 5 — Required content workflows

### Ship 30 for 30 skill

- Read the linked writing guide.
- Encode its relevant writing principles in a dedicated skill/tool.
- Generate approximately 1,250 words.
- Include a strong hook, narrative progression, skimmable formatting, and a specific takeaway.
- Ground substantive claims in retrieved transcript evidence.
- Preserve relevant source references.

### Artifact generation and viewer

- Generate Markdown documents and complete HTML/CSS artifacts from the current conversation.
- Render them beside the chat in an in-app Artifact Viewer.
- Do not display only raw code or redirect to an external editor.
- Treat generated HTML as untrusted.
- Implement an appropriate isolation or sanitization strategy.
- Document permitted and blocked behavior.

### Verification

Test essay structure, approximate length, source preservation, artifact rendering, unsafe HTML handling, and the viewer's isolation boundary.

### Exit criteria

The essay workflow and artifact viewer are usable through the product UI, and their key behavior is tested.

## Slice 6 — Hardening and handoff

### Tasks

- Add meaningful tests for health/readiness, sessions, retrieval, citations, agent routing, provider selection, persistence, and artifact safety.
- Add structured logs and controlled failure behavior.
- Ensure missing credentials and unavailable dependencies produce understandable errors.
- Complete README, PRD, `design.md`, `architecture.md`, `requirements_traceability.md`, implementation plan, and decision log.
- Record coding-agent transcripts, including failed attempts and corrections, with secrets removed.
- Complete the manual UI test plan.
- Record a 2–3 minute YouTube demo with the camera enabled. Show the product, demonstrate local Ollama, and explain one important technical trade-off.
- Ensure the repository is public and contains no secrets.
- Perform a fresh-clone test using only the README instructions.
- Check all eight assignment deliverables against actual evidence.

### Exit criteria

The product is reproducible from a fresh clone, mandatory requirements are demonstrated or explicitly disclosed as incomplete, and all eight deliverables have a documented status.

## Scope cuts if time is short

Cut in this order:

1. Cosmetic UI polish.
2. Full-corpus ingestion; use a clearly disclosed, representative bounded corpus.
3. Advanced hybrid-ranking tuning; retain a reliable baseline and document limitations.
4. Optional convenience features.

Do not silently drop FastAPI, the permitted agent framework, Ollama local inference, a cloud LLM provider, persistent sessions, grounded source citations, the Ship 30 for 30 skill, secure artifact rendering, tests, or the required demo.

If a mandatory requirement cannot be completed, disclose it clearly and explain its impact on evaluation.

## Daily execution and reporting

At the end of each slice, report:

- What changed.
- Files affected.
- Commands actually run.
- Observed test results.
- Verified features.
- Failed, untested, and blocked items.
- Decisions requiring approval.
- The next smallest useful implementation step.

Keep `docs/requirements_traceability.md`, `docs/decision_log.md`, `docs/feasibility_report.md`, and the coding-agent transcript consistent with the actual implementation state.

Prioritize one verified vertical slice at a time. Do not equate code generation with completion.
