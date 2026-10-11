# Project Charter — The Lenny Growth Assistant

## Purpose
Build a full-stack AI application that helps product managers, founders, and growth practitioners discover, verify, and reuse advice from Lenny's Podcast/Newsletter transcripts.

This is a take-home engagement, not a production-scale platform. The goal is a small, complete, defensible product that an evaluator can clone, run, test, understand, and extend.

## User/problem hypothesis
**Primary-user hypothesis:** a product manager, aspiring founder, or startup operator remembers useful advice but cannot easily recall the episode, guest, or passage, or wants to research a current product/growth problem across multiple interviews.

**Job to be done:** “When I need advice about a product or growth challenge, help me find relevant original discussions, understand the evidence in context, and turn the insight into useful written work without manually searching hours of transcripts.”

This is an evidence-informed hypothesis, not validated customer research. Do not present it as proven demand.

## Core product loop
1. Ask a product/growth question.
2. Retrieve relevant transcript passages.
3. Answer from retrieved evidence and show traceable source citations.
4. Ask a follow-up in the same session.
5. Turn grounded research into a Ship 30 for 30-style essay or a Markdown/HTML artifact.
6. Review the artifact inside the application.

## Required capabilities
- Grounded transcript Q&A with citations to guest/episode and source URL; timestamp when available.
- Follow-up questions with session-specific context.
- New independent sessions and PostgreSQL persistence.
- Local Ollama demo path and at least one cloud provider, with explicit selection visible in the UI/config.
- Agent layer using Pi Coding Agent or Anthropic Claude Agent SDK.
- Dedicated `ship30` skill.
- Dedicated `artifact` workflow/skill and in-app artifact viewer.
- FastAPI, health endpoint, validation, structured errors and logs.
- Reproducible setup, `.env.example`, tests, documentation and short demo video.

## Non-goals / deliberate cuts
- Authentication and multi-user access control.
- General-purpose web research or arbitrary browsing.
- Automatic transcript refresh/synchronization.
- Advanced reranking.
- Streaming polish.
- Unrestricted autonomous agents or elaborate multi-agent orchestration.
- Publishing platform, analytics dashboard, or production-scale infrastructure.

## Success measures (targets to test, not claimed results)
- Retrieval Recall@5 >= 80% on a small manually labelled test set.
- Citation support rate >= 90% in a manually reviewed sample of factual claims.
- Unsupported-question handling >= 80% on a test set with intentionally unanswerable questions.
- Session isolation: 100% of session-isolation tests pass.
- Request routing accuracy >= 90% across Q&A, follow-up, essay, and artifact requests.
- Record local latency on the actual machine; do not promise a latency target until measured.

## Required deliverables
1. Public GitHub repository with no committed secrets.
2. `README.md`.
3. PRD.
4. `design.md`.
5. `architecture.md`.
6. `agent-transcripts/` with successful and failed attempts/corrections, secrets removed.
7. Automated tests and manual UI test plan.
8. 2–3 minute YouTube demo with camera enabled.

## Deadline
Official: 12 October 2026 EOD. Internal working target: 10 October 2026. The user has stated 11 October is unavailable, so do not schedule required work on that day.

## Product principles
- Evidence over confidence.
- Show source provenance and uncertainty.
- A bounded workflow is preferable to unrestricted autonomy.
- Never silently change the selected model provider.
- Do not claim untested behavior.
- Simplicity and reproducibility beat unnecessary sophistication.
