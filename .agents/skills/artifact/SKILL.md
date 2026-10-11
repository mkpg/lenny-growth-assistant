---
name: artifact
description: Generate a Markdown document or self-contained HTML/CSS artifact from the current grounded conversation and show it in the in-app Artifact Viewer safely.
---

# Artifact Generation Skill

## Purpose
Turn the current conversation and transcript-grounded findings into a useful rendered artifact, not just a code block.

## Supported outputs
- Markdown document: structured notes, plan, comparison, checklist, or brief.
- HTML/CSS artifact: a self-contained mini-page, report, table, or lightweight interactive view. Prefer no JavaScript unless a specific interaction requires it and the security model explicitly permits it.

## Workflow
1. Clarify the artifact's purpose from the user's request. If output type is ambiguous and materially changes the result, ask one concise question.
2. Extract only relevant, supported information from the current conversation and retrieved sources.
3. Choose Markdown for text-first content; HTML/CSS for a visual or layout-driven artifact.
4. Generate a title and clear hierarchy.
5. Preserve citations and source metadata for factual claims based on transcripts.
6. Validate the artifact type and output schema before saving.
7. Persist the artifact with the correct session ID and return its artifact ID/type to the frontend.
8. Render it in the Artifact Viewer, not in the trusted application DOM.
9. Report rendering failures clearly; do not silently show an empty pane.

## Security rules
- Treat all generated HTML, CSS, Markdown, and embedded links as untrusted.
- Never interpolate generated HTML directly into the trusted application DOM.
- HTML must render inside an iframe with `sandbox` and **without `allow-same-origin`**. Do not enable arbitrary script execution.
- Use a restrictive Content Security Policy. Deny network connections where feasible and limit images/fonts/styles to safe sources or inline content as appropriate.
- Sanitize Markdown/HTML-capable output with a maintained sanitizer such as DOMPurify when browser-side HTML rendering is used.
- Validate links and reject dangerous schemes such as `javascript:`.
- Do not expose API keys, application state, privileged APIs, or session secrets to artifact content.
- Add tests for script tags, event-handler attributes, dangerous URLs, and iframe sandbox configuration.
- Explain what the implemented viewer permits and blocks in `docs/architecture.md`.

## Output contract
Return structured data containing:
- `artifact_type`: `markdown` or `html`
- `title`
- `content`
- `sources`: optional list of source references
- `session_id` or enough trusted server-side context to associate it with the active session

Do not trust a model-provided session ID; the backend must bind artifacts to the authenticated/request session context it already validated.
