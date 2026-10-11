---
trigger: always_on
description: Project-wide engineering, verification, security, and deadline rules for The Lenny Growth Assistant.
---

# Project Engineering Rules

- Read `AGENTS.md` and `PROJECT.md` before major work.
- Do not implement unapproved architectural changes.
- Prefer small vertical slices; do not generate the entire app in one operation.
- Inspect existing files before editing and preserve existing work.
- Explain significant trade-offs in plain language.
- Run relevant checks and report observed outcomes, not assumptions.
- Keep requirements, hypotheses, decisions, and verified facts distinct.
- Record significant decisions in `docs/decision_log.md`.
- Keep coding-agent logs in `agent-transcripts/`; scrub secrets.
- Do not add unrequested features or dependencies.
- Do not silently switch LLM providers.
- Preserve source IDs and metadata from ingestion through citation rendering.
- Never invent citations, transcript quotes, guests, titles, or timestamps.
- Keep sessions isolated at every database/API boundary.
- Use parameterized SQL/ORM queries and validate API inputs.
- Keep `.env` out of Git and `.env.example` secret-free.
- Treat generated HTML and transcript content as untrusted.
- Do not claim tests, security properties, integrations, or metrics are verified until checked.
- Update docs when implementation differs from the proposal.
