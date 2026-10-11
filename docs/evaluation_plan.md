# Evaluation Plan

## Purpose
Evaluate whether the assistant retrieves relevant evidence, cites it correctly, handles missing evidence honestly, preserves sessions, routes requests correctly, and renders artifacts safely.

## Small evaluation set
Create a JSON/CSV fixture with manually checked questions and expected source IDs. Cover:
1. Known-answer question whose answer appears directly in one transcript.
2. Conceptual question where wording differs from the transcript.
3. Question asking for a named guest/company/product.
4. Comparison question requiring at least two sources.
5. Follow-up that depends on the previous turn.
6. Unsupported question with no sufficient evidence in the indexed subset.
7. Essay request based on retrieved passages.
8. Markdown artifact request.
9. HTML artifact request containing hostile markup for security testing.
10. Session isolation test using two different sessions.

## Metrics
- Recall@5: fraction of questions for which a labelled relevant chunk is among top five results.
- Citation support rate: fraction of sampled factual claims supported by the cited passage.
- Unsupported-question handling: fraction of no-evidence cases where the assistant clearly abstains or explains the evidence gap.
- Session isolation: all cross-session isolation tests pass.
- Request routing accuracy: fraction of cases routed to the expected workflow.

Targets in `PROJECT.md` are initial engineering goals, not industry standards or achieved results.

## Required automated checks
- `GET /health`.
- Session creation and message persistence.
- Cross-session history isolation.
- Retrieval returns source metadata.
- Citation IDs correspond to retrieved chunks.
- Unsupported question does not fabricate a source.
- Provider selection and missing-credential handling.
- Essay workflow is invoked and preserves evidence.
- Artifact type validation and session association.
- HTML sandbox configuration and malicious markup behavior.
- Database unavailable / model timeout errors where practical.

## Manual test plan
- Start the app from documented instructions.
- Ask a known-answer question and open its citation.
- Ask a follow-up.
- Create a new session and verify prior context is absent.
- Switch provider and verify the selected provider is shown.
- Stop Ollama and verify a clear error.
- Ask an unsupported question.
- Generate a Ship 30 essay and check length, structure, evidence and takeaway.
- Generate Markdown and HTML artifacts.
- Attempt a hostile HTML artifact and verify it remains isolated.
- Review logs for useful diagnostics and confirm secrets are not logged.
- Follow README in a fresh clone.

## Reporting
Record actual pass/fail results, test commands, environment details and known limitations. Never write that a metric was achieved unless the test was run and the result recorded.
