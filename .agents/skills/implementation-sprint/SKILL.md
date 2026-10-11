---
name: implementation-sprint
description: Implement one approved vertical slice of The Lenny Growth Assistant, including tests, documentation, and an agent-session log.
---

# Implementation Sprint

## Before editing
1. Read `AGENTS.md`, `PROJECT.md`, the relevant docs, and the current decision log.
2. State the sprint goal and acceptance criteria.
3. List the files expected to change and the major trade-off.
4. Check the human has approved the relevant architecture decision.

## While editing
1. Implement only the agreed slice.
2. Keep modules small and responsibilities clear.
3. Do not stub a mandatory feature and describe it as complete.
4. Add tests alongside the feature.
5. Handle expected failures with useful, non-sensitive errors.
6. Update docs if implementation differs from the plan.

## After editing
1. Run the relevant test/check commands.
2. Report exact command and observed result.
3. Identify untested behavior and known limitations.
4. Append meaningful decisions to `docs/decision_log.md`.
5. Save a sanitized summary/transcript to `agent-transcripts/`.
6. Provide a concise handoff: files changed, how to run, how to test, risks, next smallest task.

## Stop conditions
Pause for human input if a change affects the selected stack, required agent framework, data model, model provider behavior, security boundary, deadline, or deliberate exclusions.
