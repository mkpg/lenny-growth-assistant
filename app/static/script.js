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
    
    // Artifact Viewer Elements
    const artifactPanel = document.getElementById("artifact-panel");
    const closeArtifactBtn = document.getElementById("close-artifact-btn");
    const artifactContent = document.getElementById("artifact-content");
    const artifactIframe = document.getElementById("artifact-iframe");
    const artifactMarkdown = document.getElementById("artifact-markdown");
    
    // State
    let currentSessionId = null;
    let isProcessing = false;

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
            const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 min timeout

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
            indicator.remove();
            appendAssistantMessage(data.answer, data.citations, data.artifact);

        } catch (error) {
            indicator.remove();
            if (error.name === "AbortError") {
                showError("Request timed out after 120 seconds.");
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

    function appendAssistantMessage(text, citations, explicitArtifact) {
        if (!text) {
            text = "*(Empty response received)*";
        }
        
        const msgDiv = document.createElement("div");
        msgDiv.className = "message assistant-message";
        
        // Convert Markdown to HTML
        let rawHtml = marked.parse(text);
        
        let hasArtifact = false;
        let artifactHtml = "";
        
        let buttonHtml = "";
        
        // Use explicit artifact if provided
        if (explicitArtifact) {
            hasArtifact = true;
            artifactHtml = explicitArtifact;
            const buttonId = `view-artifact-${Date.now()}`;
            buttonHtml = `<p><button class="artifact-trigger" data-html="true" id="${buttonId}">Preview HTML Artifact</button></p>`;
        } else {
            // Fallback: Detect HTML artifacts from markdown code block
            const htmlBlockRegex = /<pre><code class="language-html">([\s\S]*?)<\/code><\/pre>/i;
            const htmlMatch = rawHtml.match(htmlBlockRegex);
            
            if (htmlMatch) {
                hasArtifact = true;
                // Decode the escaped HTML from the code block
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = htmlMatch[1];
                artifactHtml = tempDiv.textContent;
                
                // Add a button to view the artifact
                const buttonId = `view-artifact-${Date.now()}`;
                buttonHtml = `<p><button class="artifact-trigger" data-html="true" id="${buttonId}">Preview HTML Artifact</button></p>`;
                
                // Remove the code block from the raw HTML to prevent displaying both
                rawHtml = rawHtml.replace(htmlBlockRegex, "");
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
                    renderHtmlArtifact(artifactHtml);
                });
            }
        }
    }

    function showTypingIndicator() {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message assistant-message indicator-msg";
        msgDiv.innerHTML = `
            <div class="message-content typing-indicator">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        `;
        chatHistory.appendChild(msgDiv);
        return msgDiv;
    }

    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
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
        
        // Use Blob URL for reliable cross-browser iframe rendering inside sandboxes
        const blob = new Blob([htmlString], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        if (artifactIframe.dataset.blobUrl) {
            URL.revokeObjectURL(artifactIframe.dataset.blobUrl);
        }
        
        artifactIframe.dataset.blobUrl = url;
        artifactIframe.src = url;
    }

    function hideArtifactViewer() {
        artifactPanel.classList.add("collapsed");
        if (artifactIframe.dataset.blobUrl) {
            URL.revokeObjectURL(artifactIframe.dataset.blobUrl);
            artifactIframe.dataset.blobUrl = "";
        }
        artifactIframe.src = "about:blank"; 
    }
});
