# Design Specification — The Lenny Growth Assistant

**Status:** Initial UX direction. Revise after the first working slice.

## 1. Design principles
- Research-first, not a generic chatbot clone.
- Evidence is visible and easy to inspect.
- Keep the main flow simple: ask, verify, follow up, create.
- Show loading, empty, error and unsupported-evidence states clearly.
- Avoid UI polish that delays required functionality.
- Keyboard accessible, responsive, and readable.

## 2. Information architecture
- Main application shell.
- Left sidebar: new chat and session history.
- Main pane: messages, composer, provider/model selection, citations.
- Artifact pane: opens when an artifact is generated; can collapse on small screens.
- Clear status area for selected provider and connection errors.

## 3. Primary journey
1. User opens the app and sees an empty-state explanation and example questions.
2. User selects Ollama or the configured cloud provider.
3. User submits a product/growth question.
4. UI shows a loading state.
5. Assistant answers with citations. Each citation displays episode title, guest, and a source link; timestamp appears only when available.
6. User follows up in the same session.
7. User requests an essay or artifact.
8. Artifact opens beside the chat and can be copied or inspected.
9. User starts a new chat; prior session context must not leak into it.

## 4. Key states
- Initial empty state.
- Sending/loading.
- Answer with citations.
- Answer with partial evidence/uncertainty.
- No supporting evidence.
- Ollama unavailable.
- Cloud key missing.
- Database unavailable.
- Artifact generating.
- Artifact rendered.
- Artifact blocked/invalid.
- Empty session history.
- Narrow-screen layout.

## 5. Accessibility and responsive behavior
- Use semantic buttons, labels, headings and form controls.
- Keyboard focus must remain visible.
- Provide accessible names for icon-only controls.
- Do not rely on color alone to communicate provider/error state.
- Respect reduced-motion preferences if animations are added.
- On small screens, stack the artifact viewer below the chat rather than squeezing both panes.
- Keep citation text selectable and source links keyboard accessible.

## 6. Artifact viewer
- Show the artifact title and type.
- Keep artifact content separate from trusted chat UI.
- Markdown should be safely rendered.
- HTML must render only inside a sandboxed iframe without `allow-same-origin`, with a restrictive CSP and no arbitrary script execution.
- Provide a source/code view or copy action if feasible.
- Display a clear error if rendering is blocked.

## 7. Visual direction
Use a clean editorial/research interface inspired by reading and note-taking tools, not a replica of another product. Prioritize legible typography, restrained color, clear hierarchy, and generous spacing. Use plain CSS unless a dependency materially speeds up delivery.

## 8. UX acceptance checklist
- User can create a new session and return to a previous session.
- Provider selection is visible.
- Citations are clearly associated with the answer.
- Unsupported questions are not presented as confidently answered.
- Loading and errors are understandable.
- Artifact can be opened and does not execute untrusted content in the trusted app context.
- Layout remains usable on desktop and mobile widths.
