---
name: feasibility-gate
description: Run before substantial implementation to verify transcript data, local model availability, embedding feasibility, and Pi agent integration within a strict time box.
---

# Feasibility Gate

## Goal
Resolve the few risks that could force architectural changes before building the application. Time-box to 30–45 minutes. Do not scaffold the full product during this skill.

## Steps
1. Inspect the current workspace and preserve existing user work.
2. Inspect the transcript source repository and several representative files. Record file format, metadata fields, speaker labels, timestamps, approximate corpus size, source URLs and attribution/license notes. Do not assume a fixed format.
3. Check which relevant tools are already installed: Python, Node, Docker, Ollama. Do not install software or pull large models without the human's approval.
4. If Ollama is available, list installed models. Test a small generation request with an installed model.
5. If `nomic-embed-text` is installed, test one embedding request and inspect the vector length. If not installed, report that it must be pulled and ask before doing so.
6. Investigate the smallest documented Pi Coding Agent integration path for this project. If tools and credentials are available, run one minimal tool/model call against Ollama. Do not expose secrets. If impossible, record the exact blocker.
7. Record results in `docs/feasibility_report.md` and append a decision to `docs/decision_log.md`.
8. Recommend one implementation baseline and a fallback. Explain the integration cost and impact.
9. Stop and ask the human to approve the baseline before full implementation.

## Report format
- Environment facts observed
- Transcript format and metadata observed
- Ollama model availability and test outcome
- Embedding availability and dimension observed
- Pi integration outcome
- Blockers and assumptions
- Recommended baseline
- Decision requiring human approval

## Rules
- No fabricated success.
- No large downloads without permission.
- No broad refactor or full-app generation.
