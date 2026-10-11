# Product Requirements Document — The Lenny Growth Assistant

**Status:** Draft for implementation; assumptions and targets must be validated during development.  
**Assignment:** Oogway Labs Forward-Deployed Engineer take-home.  
**Deadline:** 12 October 2026 EOD; internal target 10 October 2026.

## 1. Discovery brief

### User and problem
Primary-user hypothesis: product managers, founders, and growth practitioners who need to find advice across Lenny's Podcast/Newsletter transcripts and reuse it in practical work.

The archive contains useful expertise, but users may not remember the episode, guest, exact wording, or location. Finding evidence is only part of the job: users also need to compare advice, understand context, verify claims, and turn research into content.

This persona and pain point are hypotheses. No customer interviews or quantitative demand evidence have been supplied.

### Product promise
A source-grounded research assistant that connects transcript discovery, contextual follow-up questions, essay writing, and native artifact viewing in one interface.

### Success metrics
These are proposed targets, not achieved results or industry benchmarks:
- Retrieval Recall@5 >= 80% on a small labelled test set.
- Citation support rate >= 90% on a manually reviewed sample.
- Unsupported-question handling >= 80% on deliberately unanswerable questions.
- 100% pass rate for session-isolation tests.
- Request-routing accuracy >= 90% across Q&A, follow-up, essay, and artifact requests.
- Record local response latency and disclose the observed result.

### Assumptions
- Existing public transcripts are the initial knowledge source; real-time audio transcription is not required by the brief.
- A single primary persona is sufficient for the take-home.
- A small, curated or bounded transcript corpus is acceptable if its scope is clearly disclosed.
- Local Ollama inference may be slower or lower quality than cloud inference.
- The frontend can use vanilla HTML/CSS/JavaScript to reduce implementation overhead.
- Generated artifacts are untrusted and must be isolated from the main application.
- One developer with AI coding assistance is implementing under a severe deadline.

## 2. Scope

### In scope
- Grounded Q&A across ingested transcripts.
- Episode/guest/source citations and timestamps when available.
- Follow-up questions within the same session.
- New independent sessions; persist sessions and messages in PostgreSQL.
- Local Ollama and at least one cloud LLM option, explicitly selected and visible.
- Agent layer using Pi Coding Agent or Anthropic Claude Agent SDK.
- Dedicated Ship 30 for 30 essay skill.
- Markdown and HTML/CSS artifact generation and an in-app viewer.
- Safe artifact rendering, logs, health checks, controlled errors, tests and handoff documentation.

### Out of scope
- Authentication and multi-user authorization.
- General-purpose web search.
- Automatic transcript refresh.
- Advanced reranking unless baseline testing proves it necessary.
- Streaming polish.
- Multiple autonomous agents.
- Production-scale monitoring or deployment infrastructure beyond the assignment.

## 3. User stories and acceptance criteria

### Story A — Ask a grounded question
As a product/growth user, I want an answer based on relevant transcript passages so that I can trust and verify it.
- Relevant passages are retrieved from the indexed corpus.
- Each substantive answer includes source citations linked to retrieved chunks.
- Citation metadata includes episode title, guest, source URL, and timestamp when available.
- If evidence is insufficient, the assistant says so rather than inventing details.
- The test suite checks retrieval and citation behavior.

### Story B — Ask a follow-up
As a user, I want the assistant to understand follow-up questions in the current conversation.
- Messages are stored against the correct session.
- Follow-up requests include only that session's history.
- A new session has independent context.
- Cross-session access is rejected or impossible through the API.

### Story C — Choose a model
As an evaluator, I want to select local Ollama or a cloud provider.
- Selected provider/model is visible in the UI.
- Configuration is documented in `.env.example` and README.
- Missing cloud credentials and unavailable Ollama produce clear errors.
- Provider switching is explicit; no silent fallback.

### Story D — Generate a Ship 30 for 30 essay
As a user, I want grounded research transformed into a useful essay.
- A dedicated skill encodes writing principles.
- Output targets approximately 1,250 words.
- It includes a strong hook, coherent narrative progression, headings, selective emphasis, and a specific takeaway.
- Claims are grounded in transcript evidence and citations are retained where appropriate.
- If evidence is insufficient, the workflow does not fabricate supporting claims.

### Story E — Generate and view an artifact
As a user, I want a Markdown or HTML/CSS artifact rendered beside the chat.
- Artifact content is stored and associated with the correct session.
- Markdown is rendered safely.
- HTML is rendered in an isolated sandboxed iframe without `allow-same-origin`.
- A restrictive CSP is used; unsafe scripts and privileged application access are not allowed.
- The UI identifies artifact type and offers a way to inspect/copy the source where feasible.

### Story F — Run and hand off the application
As an evaluator, I want to clone and run the application using documented steps.
- Docker Compose starts the database, backend and frontend.
- Ollama host setup is documented separately.
- `.env.example` contains safe placeholders, not secrets.
- Health endpoint, automated tests and troubleshooting guidance exist.
- Documentation reflects observed implementation and test results.

## 4. Quality and failure behavior
- Validate all API inputs and use structured errors.
- Log request/session IDs, provider, retrieval count, latency and error category; never log keys.
- Handle missing cloud keys, Ollama unavailable, model timeout, empty retrieval, malformed output and database outage.
- Preserve source metadata end-to-end.
- Treat transcript text and generated output as untrusted input.
- Do not silently switch providers or claim a test passed without running it.

## 5. Risks and trade-offs
- **Hallucination:** mitigate with retrieved evidence, citations, abstention, and manual claim checks.
- **Local model quality/latency:** use a model that fits the machine; measure rather than promise.
- **Agent SDK integration:** Pi is TypeScript-based while the API is Python; test early and time-box.
- **Retrieval complexity:** hybrid search can improve exact-term and conceptual recall but adds ranking complexity; compare against a simpler baseline.
- **Artifact injection:** isolate generated HTML and sanitize content.
- **Deadline:** focus on vertical slices; avoid non-required scope.
- **Transcript coverage/metadata:** inspect source files and disclose the indexed subset.

## 6. Definition of done
The repository starts from documented instructions, the core Q&A path returns source-grounded answers, session persistence/isolation is tested, local Ollama works in the demo, the required agent layer is present, essay and artifact flows work, critical tests run, and all eight deliverables are complete or clearly disclose any limitation.
