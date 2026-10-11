# Start Here — Antigravity Implementation Brief

Read `AGENTS.md` and `PROJECT.md` first, then read:
- `docs/PRD.md`
- `docs/architecture.md`
- `docs/design.md`
- `docs/implementation_plan.md`
- `docs/evaluation_plan.md`

## How to work
Do not build everything in one prompt. Work through the implementation plan in order and stop at each gate. Explain the intended changes before each substantial stage. Run checks and report observed results.

## First task only
Invoke the `feasibility-gate` skill:
1. Inspect the actual transcript repository structure and licensing/attribution details.
2. Check whether Docker, Ollama, Python, and Node are available in the current environment; do not install or change system-wide software without asking.
3. Check whether an Ollama model is already installed; do not pull large models without asking.
4. Smoke-test `nomic-embed-text` only if Ollama and the model are available. Otherwise report the exact blocker and required next step.
5. Test a minimal Pi Coding Agent integration path with a local Ollama model if feasible. Time-box this to 30–45 minutes. Do not build the whole app during this test.
6. Report findings, the simplest viable integration design, and any trade-offs.
7. Ask the human to approve the baseline before starting the full implementation.

## Initial user-facing product flow
A user opens a chat, chooses the model provider, asks a question, sees a grounded answer with episode/guest/source citations, asks a follow-up, then requests either a Ship 30 essay or an artifact rendered beside the chat.

## Keep the scope disciplined
Do not add authentication, reranking, transcript auto-refresh, or streaming polish. Prioritize a complete vertical slice, then required secondary features, then tests/docs/demo.
