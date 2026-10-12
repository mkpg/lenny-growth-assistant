document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const chatHistory = document.getElementById("chat-history");
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const sendBtn = document.getElementById("send-btn");
    const newChatBtn = document.getElementById("new-chat-btn");
    const providerSelect = document.getElementById("provider-select");
    const modelSelect = document.getElementById("model-select");
    const sessionStatus = document.getElementById("session-status");
    const errorBanner = document.getElementById("error-banner");
    
    // Artifact Viewer & Library Elements
    const artifactPanel = document.getElementById("artifact-panel");
    const closeArtifactBtn = document.getElementById("close-artifact-btn");
    const artifactContent = document.getElementById("artifact-content");
    const artifactIframe = document.getElementById("artifact-iframe");
    const artifactMarkdown = document.getElementById("artifact-markdown");
    const artifactHeaderTitle = document.getElementById("artifact-header-title");
    const artifactTypeBadge = document.getElementById("artifact-type-badge");
    const toggleHistoryBtn = document.getElementById("toggle-history-btn");
    const historyCount = document.getElementById("history-count");
    const downloadArtifactBtn = document.getElementById("download-artifact-btn");
    const artifactHistoryView = document.getElementById("artifact-history-view");
    const artifactHistoryList = document.getElementById("artifact-history-list");
    const headerArtifactsBtn = document.getElementById("header-artifacts-btn");
    const headerArtifactCount = document.getElementById("header-artifact-count");
    
    // State
    let currentSessionId = null;
    let isProcessing = false;
    let activeArtifact = null; // { id, title, artifact_type, content }
    let sessionArtifacts = [];

    // Configure marked for safe Markdown rendering
    marked.setOptions({
        breaks: true,
        gfm: true
    });

    // Event Listeners
    chatForm.onsubmit = handleChatSubmit;
    userInput.onkeydown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!isProcessing) {
                chatForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
            }
        }
    };
    
    newChatBtn.onclick = startNewSession;
    closeArtifactBtn.onclick = hideArtifactViewer;
    toggleHistoryBtn.onclick = toggleHistoryView;
    downloadArtifactBtn.onclick = downloadActiveArtifact;
    if (headerArtifactsBtn) {
        headerArtifactsBtn.onclick = () => {
            if (artifactPanel.classList.contains("collapsed")) {
                artifactPanel.classList.remove("collapsed");
            }
            if (artifactHistoryView.classList.contains("hidden")) {
                artifactHistoryView.classList.remove("hidden");
                loadSessionArtifacts();
            } else {
                artifactHistoryView.classList.add("hidden");
            }
        };
    }
    
    // Provider change handler to update available models
    providerSelect.addEventListener("change", () => {
        const provider = providerSelect.value;
        if (provider === "google") {
            modelSelect.innerHTML = `
                <option value="gemini-3.8-flash" selected>gemini-3.8-flash</option>
            `;
        } else {
            modelSelect.innerHTML = `
                <option value="qwen2.5:3b" selected>qwen2.5:3b</option>
                <option value="qwen3:4b">Qwen3 4B</option>
            `;
        }
    });

    // Initial state: hide artifact panel on load
    hideArtifactViewer();

    // Functions
    function startNewSession() {
        if (isProcessing) return;
        currentSessionId = null;
        chatHistory.innerHTML = `
            <div class="message assistant-message">
                <div class="message-content">
                    Started a new session! I am The Lenny Growth Assistant. How can I help you?
                </div>
            </div>
        `;
        sessionStatus.textContent = "New Session";
        activeArtifact = null;
        sessionArtifacts = [];
        historyCount.textContent = "0";
        if (headerArtifactsBtn) {
            headerArtifactsBtn.classList.add("hidden");
            headerArtifactCount.textContent = "0";
        }
        artifactHistoryView.classList.add("hidden");
        artifactHistoryList.innerHTML = `<div class="history-empty">No artifacts generated in this session yet.</div>`;
        hideArtifactViewer();
        hideError();
        userInput.value = "";
        userInput.focus();
    }

    function showError(msg) {
        errorBanner.textContent = msg;
        errorBanner.classList.remove("hidden");
    }

    function hideError() {
        errorBanner.classList.add("hidden");
        errorBanner.textContent = "";
    }

    async function handleChatSubmit(e) {
        e.preventDefault();
        if (isProcessing) return;
        
        const question = userInput.value.trim();
        if (!question) return;

        // UI Updates for sending
        hideError();
        appendUserMessage(question);
        userInput.value = "";
        isProcessing = true;
        sendBtn.disabled = true;
        userInput.disabled = true;
        
        const indicator = showTypingIndicator();
        scrollToBottom();

        // API Request payload
        const payload = {
            question: question,
            provider: providerSelect.value,
            model: modelSelect.value
        };
        
        if (currentSessionId) {
            payload.session_id = currentSessionId;
        }

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 600000); // 5 min timeout

            const response = await fetch("/api/v1/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                let errText = await response.text();
                try {
                    const errJson = JSON.parse(errText);
                    errText = errJson.detail || errText;
                } catch (e) {}
                throw new Error(`Server Error (${response.status}): ${errText}`);
            }

            const data = await response.json();
            
            // Save session ID for follow-ups
            if (data.session_id) {
                currentSessionId = data.session_id;
                sessionStatus.textContent = `Session: ${currentSessionId.substring(0, 8)}...`;
            }

            // Display Answer
            indicator.cleanup();
            indicator.remove();
            appendAssistantMessage(data.answer, data.citations, data.artifact, data.artifact_id, data.artifact_title, data.artifact_type);

            // Automatically refresh session artifact history
            if (currentSessionId) {
                loadSessionArtifacts();
            }

            // Auto-display artifact if returned
            if (data.artifact) {
                displayArtifact({
                    id: data.artifact_id,
                    title: data.artifact_title || (data.artifact_type === "markdown" ? "Markdown Document" : "Generated Artifact"),
                    artifact_type: data.artifact_type || "html",
                    content: data.artifact
                });
            }

        } catch (error) {
            indicator.cleanup();
            indicator.remove();
            if (error.name === "AbortError") {
                showError("Request timed out after 600 seconds.");
            } else {
                showError(error.message || "A network error occurred.");
            }
        } finally {
            isProcessing = false;
            sendBtn.disabled = false;
            userInput.disabled = false;
            userInput.focus();
            scrollToBottom();
        }
    }

    function appendUserMessage(text) {
        // Safe escaping for text
        const safeText = DOMPurify.sanitize(text, { ALLOWED_TAGS: [] });
        
        const msgDiv = document.createElement("div");
        msgDiv.className = "message user-message";
        msgDiv.innerHTML = `<div class="message-content">${safeText}</div>`;
        
        chatHistory.appendChild(msgDiv);
    }

    function appendAssistantMessage(text, citations, explicitArtifact, artifactId, artifactTitle, artifactType) {
        if (!text) {
            text = "*(Empty response received)*";
        }

        // Defense-in-depth: if raw JSON string reaches frontend, extract answer or show fallback
        const trimmed = text.trim();
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
            try {
                const parsed = JSON.parse(trimmed);
                if (parsed && typeof parsed.answer === "string" && parsed.answer.trim()) {
                    text = parsed.answer.trim();
                }
            } catch (e) {
                if (trimmed.includes('"answer"') || trimmed.includes('"evidence_state"')) {
                    text = "I was unable to format a reliable answer from the podcast transcripts. Please try rephrasing your question.";
                }
            }
        }
        
        const msgDiv = document.createElement("div");
        msgDiv.className = "message assistant-message";
        
        // Convert Markdown to HTML
        let rawHtml = marked.parse(text);
        
        let hasArtifact = false;
        let artifactContent = "";
        let effectiveType = (artifactType || "html").toLowerCase();
        let buttonHtml = "";
        
        // Use explicit artifact if provided
        if (explicitArtifact) {
            hasArtifact = true;
            artifactContent = explicitArtifact;
            const buttonId = `view-artifact-${Date.now()}`;
            const btnLabel = effectiveType === "markdown" ? "Preview Markdown Artifact" : "Preview HTML Artifact";
            buttonHtml = `<p><button class="artifact-trigger" data-type="${effectiveType}" id="${buttonId}">${btnLabel}</button></p>`;
        } else {
            // Fallback: Detect HTML or Markdown code blocks
            const htmlBlockRegex = /<pre><code class="language-html">([\s\S]*?)<\/code><\/pre>/i;
            const htmlMatch = rawHtml.match(htmlBlockRegex);
            
            const mdBlockRegex = /<pre><code class="language-(?:markdown|md)">([\s\S]*?)<\/code><\/pre>/i;
            const mdMatch = rawHtml.match(mdBlockRegex);

            if (htmlMatch) {
                hasArtifact = true;
                effectiveType = "html";
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = htmlMatch[1];
                artifactContent = tempDiv.textContent;
                const buttonId = `view-artifact-${Date.now()}`;
                buttonHtml = `<p><button class="artifact-trigger" data-type="html" id="${buttonId}">Preview HTML Artifact</button></p>`;
                rawHtml = rawHtml.replace(htmlBlockRegex, "");
            } else if (mdMatch) {
                hasArtifact = true;
                effectiveType = "markdown";
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = mdMatch[1];
                artifactContent = tempDiv.textContent;
                const buttonId = `view-artifact-${Date.now()}`;
                buttonHtml = `<p><button class="artifact-trigger" data-type="markdown" id="${buttonId}">Preview Markdown Artifact</button></p>`;
                rawHtml = rawHtml.replace(mdBlockRegex, "");
            }
        }
        
        // Sanitize the HTML for the chat view (no scripts, safe links)
        const safeHtml = DOMPurify.sanitize(rawHtml);
        
        // Append the button HTML after sanitization to ensure classes/ids are preserved
        let contentHtml = `<div class="message-content">${safeHtml}${buttonHtml}</div>`;
        
        // Append citations if they exist
        if (citations && citations.length > 0) {
            contentHtml += `<div class="citations">
                <div class="citations-title">Sources:</div>
            `;
            
            citations.forEach((cit, idx) => {
                const title = DOMPurify.sanitize(cit.episode_title || cit.source_id || "Unknown Source", { ALLOWED_TAGS: [] });
                let url = cit.source_url ? DOMPurify.sanitize(cit.source_url, { ALLOWED_TAGS: [] }) : "";
                if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
                    contentHtml += `<div class="citation-item">[${idx + 1}] <a href="${url}" target="_blank" rel="noopener noreferrer">${title}</a></div>`;
                } else {
                    contentHtml += `<div class="citation-item">[${idx + 1}] ${title}</div>`;
                }
            });
            contentHtml += `</div>`;
        }
        
        msgDiv.innerHTML = contentHtml;
        chatHistory.appendChild(msgDiv);
        
        // Bind artifact button if present
        if (hasArtifact) {
            const btn = msgDiv.querySelector('.artifact-trigger');
            if (btn) {
                btn.addEventListener('click', () => {
                    displayArtifact({
                        id: artifactId,
                        title: artifactTitle || (effectiveType === "markdown" ? "Markdown Document" : "Generated Artifact"),
                        artifact_type: effectiveType,
                        content: artifactContent
                    });
                });
            }
        }
    }

    function showTypingIndicator() {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message assistant-message indicator-msg";
        msgDiv.innerHTML = `
            <div class="message-content typing-indicator">
                <div class="dots-wrap">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
                <span class="thinking-label">Thinking... <span class="timer-val">0s</span></span>
            </div>
        `;
        chatHistory.appendChild(msgDiv);

        const startTime = Date.now();
        const timerEl = msgDiv.querySelector('.timer-val');

        const intervalId = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            if (elapsed < 60) {
                timerEl.textContent = `${elapsed}s`;
            } else {
                const mins = Math.floor(elapsed / 60);
                const secs = elapsed % 60;
                timerEl.textContent = `${mins}m ${String(secs).padStart(2, '0')}s`;
            }
        }, 1000);

        msgDiv.cleanup = () => clearInterval(intervalId);

        return msgDiv;
    }

    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function displayArtifact(art) {
        if (!art) return;
        activeArtifact = art;

        // Update header
        artifactHeaderTitle.textContent = art.title || "Artifact Viewer";
        const type = (art.artifact_type || "html").toLowerCase();
        artifactTypeBadge.textContent = type.toUpperCase();
        artifactTypeBadge.className = "badge " + (type === "markdown" ? "md-badge" : "html-badge");
        artifactTypeBadge.classList.remove("hidden");
        downloadArtifactBtn.classList.remove("hidden");
        if (headerArtifactsBtn) {
            headerArtifactsBtn.classList.remove("hidden");
        }

        if (type === "markdown") {
            renderMarkdownArtifact(art.content);
        } else {
            renderHtmlArtifact(art.content);
        }

        updateHistoryActiveState(art.id);
    }

    function renderMarkdownArtifact(mdString) {
        if (!mdString || !mdString.trim()) return;

        artifactPanel.classList.remove("collapsed");
        artifactContent.classList.remove("empty");

        // Hide iframe, show markdown
        artifactIframe.classList.add("hidden");
        artifactMarkdown.classList.remove("hidden");

        const emptyState = document.querySelector(".empty-state");
        if (emptyState) emptyState.classList.add("hidden");

        // Render Markdown safely
        const html = marked.parse(mdString);
        artifactMarkdown.innerHTML = DOMPurify.sanitize(html);
    }

    function renderHtmlArtifact(htmlString) {
        if (!htmlString || !htmlString.trim()) {
            return;
        }
        
        artifactPanel.classList.remove("collapsed");
        artifactContent.classList.remove("empty");
        
        // Hide markdown, show iframe
        artifactMarkdown.classList.add("hidden");
        artifactIframe.classList.remove("hidden");
        
        // Also hide empty state if it's present!
        const emptyState = document.querySelector('.empty-state');
        if (emptyState) {
            emptyState.classList.add('hidden');
        }
        
        // Ensure Content Security Policy (CSP) is present to isolate untrusted HTML
        let securedHtml = htmlString;
        const cspMeta = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; img-src data: https:; font-src data: https:;">';
        if (!securedHtml.includes('Content-Security-Policy')) {
            if (securedHtml.includes('<head>')) {
                securedHtml = securedHtml.replace('<head>', `<head>\n    ${cspMeta}`);
            } else if (securedHtml.includes('<html>')) {
                securedHtml = securedHtml.replace('<html>', `<html>\n<head>\n    ${cspMeta}\n</head>`);
            } else {
                securedHtml = `<head>${cspMeta}</head>\n` + securedHtml;
            }
        }

        // Use Blob URL for reliable cross-browser iframe rendering inside sandboxes
        const blob = new Blob([securedHtml], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        if (artifactIframe.dataset.blobUrl) {
            URL.revokeObjectURL(artifactIframe.dataset.blobUrl);
        }
        
        artifactIframe.dataset.blobUrl = url;
        artifactIframe.src = url;
    }

    function downloadActiveArtifact() {
        if (!activeArtifact) return;

        if (activeArtifact.id) {
            const sessionParam = currentSessionId ? `?session_id=${currentSessionId}` : "";
            const downloadUrl = `/api/v1/artifacts/${activeArtifact.id}/download${sessionParam}`;
            const link = document.createElement("a");
            link.href = downloadUrl;
            link.download = "";
            document.body.appendChild(link);
            link.click();
            link.remove();
        } else {
            // Fallback for unpersisted preview
            const type = (activeArtifact.artifact_type || "html").toLowerCase();
            const ext = type === "markdown" ? ".md" : ".html";
            const mime = type === "markdown" ? "text/markdown;charset=utf-8" : "text/html;charset=utf-8";
            const blob = new Blob([activeArtifact.content], { type: mime });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `artifact${ext}`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        }
    }

    async function loadSessionArtifacts() {
        if (!currentSessionId) return;

        try {
            const res = await fetch(`/api/v1/sessions/${currentSessionId}/artifacts`);
            if (!res.ok) return;
            sessionArtifacts = await res.json();
            historyCount.textContent = sessionArtifacts.length;
            if (headerArtifactsBtn) {
                if (sessionArtifacts.length > 0) {
                    headerArtifactsBtn.classList.remove("hidden");
                    headerArtifactCount.textContent = sessionArtifacts.length;
                } else {
                    headerArtifactsBtn.classList.add("hidden");
                    headerArtifactCount.textContent = "0";
                }
            }
            renderHistoryList();
        } catch (e) {
            artifactHistoryList.innerHTML = `<div class="history-error">Failed to load artifact library.</div>`;
        }
    }

    function renderHistoryList() {
        if (!sessionArtifacts || sessionArtifacts.length === 0) {
            artifactHistoryList.innerHTML = `<div class="history-empty">No artifacts generated in this session yet.</div>`;
            return;
        }

        artifactHistoryList.innerHTML = "";
        sessionArtifacts.forEach((art) => {
            const item = document.createElement("div");
            const isActive = activeArtifact && activeArtifact.id === art.id;
            item.className = `history-item ${isActive ? "active" : ""}`;
            item.dataset.id = art.id;

            const timeStr = art.created_at ? new Date(art.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "";
            const safeTitle = DOMPurify.sanitize(art.title || "Untitled Artifact", { ALLOWED_TAGS: [] });
            const typeUpper = (art.artifact_type || "html").toUpperCase();

            item.innerHTML = `
                <div class="history-item-info" title="Click to view">
                    <span class="history-item-title">${safeTitle}</span>
                    <span class="history-item-meta">${typeUpper} &bull; ${timeStr}</span>
                </div>
                <div class="history-item-actions">
                    <button class="history-action-btn open-btn" type="button">Open</button>
                    <a href="/api/v1/artifacts/${art.id}/download?session_id=${currentSessionId}" class="history-action-btn download-btn" download>Save</a>
                </div>
            `;

            // Open on title or Open button click
            const infoEl = item.querySelector(".history-item-info");
            const openBtn = item.querySelector(".open-btn");
            const handleOpen = () => openArtifactById(art.id);
            infoEl.addEventListener("click", handleOpen);
            openBtn.addEventListener("click", handleOpen);

            artifactHistoryList.appendChild(item);
        });
    }

    function updateHistoryActiveState(activeId) {
        const items = artifactHistoryList.querySelectorAll(".history-item");
        items.forEach((it) => {
            if (it.dataset.id === activeId) {
                it.classList.add("active");
            } else {
                it.classList.remove("active");
            }
        });
    }

    async function openArtifactById(artifactId) {
        try {
            const sessionParam = currentSessionId ? `?session_id=${currentSessionId}` : "";
            const res = await fetch(`/api/v1/artifacts/${artifactId}${sessionParam}`);
            if (!res.ok) {
                showError(`Failed to fetch artifact (${res.status})`);
                return;
            }
            const art = await res.json();
            displayArtifact(art);
        } catch (e) {
            showError("Network error while loading artifact.");
        }
    }

    function toggleHistoryView() {
        const isHidden = artifactHistoryView.classList.toggle("hidden");
        if (!isHidden && currentSessionId) {
            loadSessionArtifacts();
        }
    }

    function hideArtifactViewer() {
        artifactPanel.classList.add("collapsed");
        downloadArtifactBtn.classList.add("hidden");
        artifactTypeBadge.classList.add("hidden");
        if (artifactIframe.dataset.blobUrl) {
            URL.revokeObjectURL(artifactIframe.dataset.blobUrl);
            artifactIframe.dataset.blobUrl = "";
        }
        artifactIframe.src = "about:blank"; 
    }
});
