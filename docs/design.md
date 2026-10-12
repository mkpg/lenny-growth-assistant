# Product Design Document (design.md)
## The Lenny Growth Assistant

**Project:** Forward Deployed Engineer Take-Home Assignment | Oogway Labs  
**Repository:** [https://github.com/mkpg/lenny-growth-assistant](https://github.com/mkpg/lenny-growth-assistant)  
**Status:** Implemented in Frontend Architecture  

---

## 1. Design Overview & Core Principles

The user interface of **The Lenny Growth Assistant** is designed to provide a focused, research-oriented workspace for exploring growth and product management insights. The visual design uses modern styling principles: dark theme, subtle glassmorphism, responsive typography, and clear visual state indicators.

### Core Design Principles:
1. **Evidence-First Hierarchy:** Citations and source references are prominent. Users can expand citation cards to view the speaker, episode, and exact quote behind a response.
2. **Cognitive Ease:** Primary workflows remain central: asking questions, inspecting citations, toggling models, and generating artifacts.
3. **Claude-Style In-App Artifact Experience:** Generated Markdown documents and HTML/CSS snippets open natively inside an in-app viewer modal, keeping the user in the conversation flow without redirecting to external tabs.
4. **Visual State Clarity:** The interface clearly distinguishes user messages, assistant responses, citation cards, and artifact action triggers.

---

## 2. Information Architecture & Layout Breakdown

The interface (`app/static/index.html`, `style.css`, `script.js`) is organized into three primary visual areas: **Top Navigation Header**, **Main Chat Canvas**, and the **In-App Artifact Viewer Modal**.

```
+----------------------------------------------------------------------------------------------------+
|                                      TOP NAVIGATION HEADER                                         |
|  [Logo & Title]             [Provider Dropdown]  [Model Dropdown]  [Artifacts (N)]  [+ New Chat]  |
+----------------------------------------------------------------------------------------------------+
|                      |                                                                             |
|                      |                                MAIN CHAT CANVAS                             |
|                      |                                                                             |
|   HISTORY SIDEBAR    |  [Assistant Welcome Card]                                                   |
|                      |  "Ask me anything about product, growth, or leadership..."                 |
|   - Conversations    |                                                                             |
|     * Session 1      |  [User Message Bubble]                                                      |
|     * Session 2      |  "What is Adam Fishman's framework for growth teams?"                       |
|                      |                                                                             |
|   - Saved Artifacts  |  [Assistant Message Card]                                                   |
|     * Activation Plan|  - Growth team structure overview...                                        |
|     * Retention Essay|  [Citations Block: Adam Fishman Ep. 42 (Click to expand quote)]             |
|                      |  [Preview Markdown Artifact]  [Preview HTML Artifact]                       |
|                      |                                                                             |
|                      +-----------------------------------------------------------------------------+
|                      | [Message Input Field: "Ask a growth question..."]               [Send Button]|
+----------------------+-----------------------------------------------------------------------------+
|                                                                                                    |
|                                IN-APP ARTIFACT VIEWER MODAL                                         |
|  +-----------------------------------------------------------------------------------------------+ |
|  | Header: [Artifact Title]  [Badge: HTML / MARKDOWN]   [Actions: Copy | Download]  [Close (X)] | |
|  +-----------------------------------------------------------------------------------------------+ |
|  | Content Viewport:                                                                             | |
|  |   - IFRAME SANDBOX (#artifact-iframe, sandbox="allow-scripts", Blob URL CSP)                   | |
|  |   - MARKDOWN CONTAINER (#markdown-viewer, rendered via marked.js)                              | |
|  +-----------------------------------------------------------------------------------------------+ |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. DOM Component Breakdown

The DOM components implemented in `app/static/index.html` include:

### 3.1 Top Navigation Header (`#app-header`)
- **Brand Title:** Logo and application title: *"The Lenny Growth Assistant"*.
- **Provider Selector (`#provider-select`):** Dropdown allowing users to choose between **Ollama (Local)** and **Gemini (Cloud)**.
- **Model Selector (`#model-select`):** Dynamically populates models matching the selected provider (`qwen2.5:3b`, `qwen3:4b`, `gemini-2.5-flash`).
- **Header Artifacts Button (`#header-artifacts-btn`):**
  - Displays dynamic count: `"Artifacts (0)"` $\rightarrow$ `"Artifacts (N)"`.
  - Serves as a persistent header toggle to open the Artifact Library sidebar.
- **New Chat Button (`#new-chat-btn`):** Initializes a fresh conversation session, resetting the chat view and session context.

### 3.2 Chat Canvas & Message Elements
- **Message List (`#chat-messages`):** Vertically scrollable chat timeline with auto-scroll on new turns.
- **User Message (`.message.user`):** Right-aligned bubble with primary accent background.
- **Assistant Message (`.message.assistant`):** Left-aligned card with formatted Markdown text, headings, and code blocks.
- **Citation Card (`.citations-container`):**
  - Displays speaker name and episode title.
  - Accordion interaction: Clicking expands the card to reveal the exact transcript quote.
- **Inline Artifact Buttons:**
  - `.btn-preview-html`: Opens the Artifact Viewer displaying the HTML artifact.
  - `.btn-preview-md`: Opens the Artifact Viewer displaying the rendered Markdown document.

### 3.3 History Sidebar (`#history-sidebar`)
- **Sessions Tab:** Lists prior conversations with timestamps.
- **Artifacts Tab (`#artifacts-list`):** Lists all saved artifacts for the active session, showing title, format badge (`HTML` or `MARKDOWN`), and timestamp.
- **Reopen Action:** Clicking any saved artifact row opens it in the viewer directly from database storage without a new model call.

### 3.4 Dual-Format Artifact Viewer Modal (`#artifact-modal`)
- **Modal Header (`.modal-header`):**
  - Title element (`#artifact-modal-title`).
  - Format badge (`#artifact-type-badge`).
- **Action Toolbar (`.modal-actions`):**
  - **Copy Button (`#copy-artifact-btn`):** Copies raw artifact source to the clipboard with status feedback.
  - **Download Button (`#download-artifact-btn`):** Initiates a browser download for the artifact file (`.html` or `.md`).
  - **Close Button (`#close-modal-btn`):** Closes the modal.
- **Dual Viewports:**
  - **HTML Viewport (`#artifact-iframe`):** An `<iframe>` configured with `sandbox="allow-scripts"` and loaded via a Blob URL containing a CSP meta tag.
  - **Markdown Viewport (`#markdown-viewer`):** Formatted container rendering parsed HTML via `marked.js`.

---

## 4. Key User Interaction Flows

### Flow 1: Submitting a Question and Reviewing Citations
1. User enters a query into `#chat-input` and clicks **Send** or presses **Enter**.
2. Input field is temporarily disabled; a loading typing indicator appears (`.typing-indicator`).
3. Backend processes the query, retrieves chunks, and invokes the model.
4. Response text renders in the assistant card.
5. If source chunks were retrieved, citation badges appear below the answer.
6. User clicks a citation pill to inspect the speaker and quoted text.

### Flow 2: Generating and Viewing an HTML Artifact
1. User requests: *"Create an HTML activation funnel dashboard."*
2. Assistant generates introductory text and a complete HTML snippet.
3. Message displays a **Preview HTML Artifact** button, and the header button increments to **Artifacts (1)**.
4. Clicking **Preview HTML Artifact** opens the modal.
5. The HTML renders inside the sandboxed iframe viewport, allowing internal script interaction while isolating parent window storage.

### Flow 3: Generating and Downloading a Markdown Essay (Ship 30 for 30)
1. User requests: *"Write a Ship 30 for 30 essay on user onboarding."*
2. Assistant applies the dedicated skill to generate an essay of approximately 1,250 words.
3. Message displays **Preview Markdown Artifact**.
4. Clicking opens the modal with `#markdown-viewer` displaying formatted headings and bullet points.
5. User clicks **Download Markdown** to save `user_onboarding_essay.md` to disk.

---

## 5. UI State Matrix

| UI State | Visual Representation | User Feedback / Trigger |
|---|---|---|
| **Empty / Initial** | Welcome card with prompt suggestions. | Prompts user to start conversation. |
| **Request Pending** | Input disabled; animated pulsing dots (`.typing-indicator`). | Indicates model inference in progress. |
| **Grounded Answer** | Formatted text with expandable citation pills. | Informs user that citations are available for inspection. |
| **Evidence Refusal** | Neutral card acknowledging lack of transcript evidence. | Transparently explains corpus limits. |
| **Artifact Generated** | Action buttons in message + incremented Header Artifacts counter. | Alerts user to view or download the generated artifact. |
| **Artifact Modal Active** | Backdrop overlay; centered modal; keyboard `Esc` listener. | Focuses attention on the artifact content. |
| **Provider Error** | Toast notification with error details. | Informs user of connection or model failure. |

---

## 6. Accessibility & Usability (Design Targets)

*Note: Accessibility attributes represent engineering design targets rather than certified WCAG 2.1 AA audit compliance.*

- **Visual Contrast:** Dark palette designed with high-contrast text ratios for readability.
- **Keyboard Navigation:** Tab-order traversal supported across inputs, provider dropdowns, citation toggles, and modal controls. `Esc` key closes the artifact modal.
- **Semantic Structure:** Semantic HTML5 tags (`<header>`, `<main>`, `<aside>`, `<nav>`) used throughout the layout.
- **Focus Indicators:** Visible outline indicators on active buttons and input fields.
- **Limitations:** Formal automated screen-reader audits and comprehensive focus-trapping certifications have not been executed.

---

## 7. Responsive Behavior

- **Desktop ($\ge 1200\text{px}$):** Persistent history sidebar on the left, central chat stream, modal width scaled to 85% of viewport.
- **Tablet ($768\text{px} – 1199\text{px}$):** Collapsible history drawer; modal scales to 92% of viewport width.
- **Mobile ($< 768\text{px}$):** Slide-out drawer for history; navigation controls collapse; modal expands to a full-screen overlay with sticky header controls.
